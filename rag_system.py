"""
rag_system.py - SentinelRAG: Full LangGraph pipeline with observability.

Pipeline:
    retrieve -> grade_relevance -> [generate | web_search] -> generate -> END

SentinelRAG | Gurugram University B.Tech Project
Authors: Akshu Grewal, Ishantnu, Anish Singh Rawat

Usage:
    python rag_system.py
"""

import time
import json
import re
from typing import TypedDict, List, Literal

# --- LangChain / LangGraph ----------------------------------------------------
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END

# --- Web Fallback -------------------------------------------------------------
from duckduckgo_search import DDGS
try:
    from scrapling import StealthyFetcher
    _SCRAPLING_AVAILABLE = True
except ImportError:
    _SCRAPLING_AVAILABLE = False
    print("[sentinel] WARNING: scrapling not installed -- web fallback will use DDG snippets only")

# --- Observability ------------------------------------------------------------
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.langchain import LangChainInstrumentor

# ─── CONFIG ──────────────────────────────────────────────────────────────────
CHROMA_DIR   = "./chroma_db"
EMBED_MODEL  = "llama3.2"
CHAT_MODEL   = "llama3.2"
RETRIEVAL_K      = 8
SIMILARITY_CUTOFF = 0.20   # accept any chunk with cosine similarity > this
PHOENIX_OTLP = os.getenv("PHOENIX_OTLP", "http://localhost:6006/v1/traces")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# ------------------------------------------------------------------------------
#  OBSERVABILITY SETUP
# ------------------------------------------------------------------------------

def setup_observability():
    """Wire OpenTelemetry → Arize Phoenix with SentinelRAG service name."""
    resource = Resource(attributes={
        "service.name":    "SentinelRAG",
        "service.version": "1.0.0",
        "project.name":    "Sentinel RAG",
    })
    tracer_provider = trace_sdk.TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=PHOENIX_OTLP)
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    print("[sentinel] OK: Observability wired -> Phoenix at", PHOENIX_OTLP)
    print("[sentinel]     Service name: SentinelRAG")
    return tracer_provider


# ------------------------------------------------------------------------------
#  GRAPH STATE
# ------------------------------------------------------------------------------

class RAGState(TypedDict):
    question:        str
    documents:       List[Document]
    grade:           str              # "yes" | "no"
    web_context:     str
    answer:          str
    ttft:            float
    input_tokens:    int
    output_tokens:   int
    simulated_cost:  float
    route:           str              # "generate" | "web_search"
    node_log:        List[dict]       # Per-node execution log for UI


# ------------------------------------------------------------------------------
#  COMPONENTS
# ------------------------------------------------------------------------------

def get_vectorstore():
    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL
    )
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
    )


def get_llm():
    return ChatOllama(
        model=CHAT_MODEL, 
        temperature=0,
        base_url=OLLAMA_BASE_URL
    )


# ------------------------------------------------------------------------------
#  NODE 1 - RETRIEVE
# ------------------------------------------------------------------------------

def retrieve(state: RAGState) -> RAGState:
    """Retrieve top-k document chunks from ChromaDB using similarity scores."""
    print(f"\n[NODE 1 — RETRIEVE] Query: {state['question']}")
    t0 = time.time()
    vectorstore = get_vectorstore()

    # Use similarity_search_with_relevance_scores to filter weak matches
    results = vectorstore.similarity_search_with_relevance_scores(
        state["question"], k=RETRIEVAL_K
    )
    # Accept ALL returned docs — filter only truly irrelevant (very low score)
    docs = [doc for doc, score in results if score >= SIMILARITY_CUTOFF]
    if not docs and results:
        # Safety net: if all below cutoff, still keep the best match
        docs = [results[0][0]]

    elapsed = time.time() - t0
    scores_str = ", ".join([f"{s:.3f}" for _, s in results])
    print(f"[retrieve] Retrieved {len(docs)}/{len(results)} chunk(s) in {elapsed:.2f}s | scores: [{scores_str}]")

    log_entry = {
        "node":    "retrieve",
        "status":  "done",
        "message": f"Retrieved {len(docs)} chunks from ChromaDB (similarity >= {SIMILARITY_CUTOFF})",
        "time_ms": round(elapsed * 1000),
        "chunks":  [d.page_content[:120].strip() for d in docs],
    }
    return {**state, "documents": docs, "node_log": state.get("node_log", []) + [log_entry]}


# ------------------------------------------------------------------------------
#  NODE 2 - GRADE RELEVANCE
# ------------------------------------------------------------------------------

# ─── GRADER PROMPT ─────────────────────────────────────────────────────────────
GRADER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a grader assessing relevance of a retrieved document to a user question. "
     "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. "
     "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."),
    ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
])

def grade_relevance(state: RAGState) -> RAGState:
    """LLM-based grader: checks if the retrieved documents actually answer the question.
    
    If no documents are found OR the LLM grades them as irrelevant,
    the system will fall back to web search.
    """
    print("\n[NODE 2 — GRADE RELEVANCE]")
    docs = state["documents"]
    
    if not docs:
        print("[grade] No documents retrieved. Falling back to web.")
        return {**state, "grade": "no", "node_log": state.get("node_log", []) + [{
            "node": "grade_relevance", "status": "done", "message": "No docs found", "grade": "no", "time_ms": 0
        }]}

    llm = get_llm()
    # Simple strategy: check if ANY of the top-3 documents are relevant
    # (Checking all 8 might be too slow/expensive for a local model)
    relevant_found = False
    t0 = time.time()
    
    # We'll just check the combined context of the top chunks for speed
    combined_context = "\n\n".join([d.page_content for d in docs[:3]])
    
    chain = GRADER_PROMPT | llm | StrOutputParser()
    res = chain.invoke({"question": state["question"], "document": combined_context})
    
    # Normalize response
    grade = "yes" if "yes" in res.lower() else "no"
    elapsed = time.time() - t0
    
    status = f"LLM Grade: {grade.upper()} ({elapsed:.2f}s) — {'using local docs' if grade == 'yes' else 'falling back to web'}"
    print(f"[grade] {status}")

    log_entry = {
        "node":    "grade_relevance",
        "status":  "done",
        "message": status,
        "grade":   grade,
        "time_ms": round(elapsed * 1000),
    }
    return {
        **state,
        "grade":    grade,
        "node_log": state.get("node_log", []) + [log_entry],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER — conditional edge
# ══════════════════════════════════════════════════════════════════════════════

def route_after_grading(state: RAGState) -> Literal["generate", "web_search"]:
    """Conditional router:
       grade=yes (docs found in PDF) -> generate from local context
       grade=no  (nothing in DB)     -> web_search fallback
    """
    route = "generate" if state["grade"] == "yes" else "web_search"
    print(f"[route] -> {route.upper()}")
    return route


# ------------------------------------------------------------------------------
#  NODE 3 - WEB FALLBACK
# ------------------------------------------------------------------------------

def web_search(state: RAGState) -> RAGState:
    """DuckDuckGo search + Scrapling StealthyFetcher for web context.

    Blueprint spec (FILE 6, NODE 3): For each DDG result URL, use
    StealthyFetcher to scrape the full page content (up to 1500 chars).
    Falls back to the raw DDG snippet if Scrapling fails or is unavailable.
    """
    print("\n[NODE 3 - WEB FALLBACK]")
    t0    = time.time()
    query = state["question"]
    web_text = ""
    sources  = []

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        print(f"[web_search] Found {len(results)} DuckDuckGo result(s)")

        for r in results:
            url     = r.get("href", "")
            snippet = r.get("body", "")
            if not url:
                continue

            # ── Scrapling: fetch full page content ───────────────────────────
            page_text = snippet  # default: DDG snippet
            if _SCRAPLING_AVAILABLE:
                print(f"[web_search] Scraping: {url}")
                try:
                    fetcher   = StealthyFetcher()
                    page      = fetcher.fetch(url, headless=True, network_idle=True)
                    raw_text  = page.get_content()
                    clean     = re.sub(r'\s+', ' ', raw_text).strip()[:1500]
                    if clean:
                        page_text = clean
                        print(f"[web_search] Scrapled {len(page_text)} chars from {url}")
                except Exception as e:
                    print(f"[web_search] Scrape failed for {url}: {e}")
                    # page_text stays as snippet (already set above)
            else:
                print(f"[web_search] Scrapling unavailable, using snippet for {url}")

            web_text += f"\n[Source: {url}]\n{page_text}\n"
            sources.append(url)

    except Exception as e:
        print(f"[web_search] DuckDuckGo failed: {e}")
        web_text = "Web search unavailable. Answering from model knowledge."

    elapsed = time.time() - t0
    print(f"[web_search] Web context length: {len(web_text)} chars ({elapsed:.2f}s)")
    log_entry = {
        "node":    "web_search",
        "status":  "done",
        "message": f"Fetched {len(sources)} web sources via DuckDuckGo + Scrapling",
        "sources": sources,
        "time_ms": round(elapsed * 1000),
    }
    return {
        **state,
        "web_context": web_text,
        "route":       "web_search",
        "node_log":    state.get("node_log", []) + [log_entry],
    }


# ------------------------------------------------------------------------------
#  NODE 4 - GENERATE
# ------------------------------------------------------------------------------

GENERATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant for SentinelRAG, a production-grade RAG system. "
     "Answer the user's question using ONLY the provided context. "
     "If the context does not contain enough information, say so clearly. "
     "Be concise, factual, and well-structured."),
    ("human",
     "Context:\n{context}\n\nQuestion: {question}"),
])

def generate(state: RAGState) -> RAGState:
    """Generate answer + collect TTFT, token counts, simulated cost."""
    print("\n[NODE 4 — GENERATE]")
    llm   = get_llm()
    chain = GENERATE_PROMPT | llm | StrOutputParser()

    # Build context from local docs or web
    if state.get("route") == "web_search":
        context = state.get("web_context", "No web context retrieved.")
        source_label = "web"
        print("[generate] Using WEB context")
    else:
        context = "\n\n".join([d.page_content for d in state["documents"]])
        source_label = "local"
        print(f"[generate] Using LOCAL context ({len(state['documents'])} chunks)")

    # Measure TTFT (first token latency approximation)
    t0     = time.time()
    answer = chain.invoke({"context": context, "question": state["question"]})
    ttft   = time.time() - t0

    # Token estimation (~4 chars per token heuristic)
    input_tokens  = (len(context) + len(state["question"])) // 4
    output_tokens = len(answer) // 4

    # Simulated cost (GPT-3.5 pricing as benchmark: $0.001/1K tokens)
    simulated_cost = (input_tokens + output_tokens) / 1000 * 0.001

    print(f"[generate] OK: TTFT: {ttft:.3f}s | in: ~{input_tokens} | out: ~{output_tokens} | est. ${simulated_cost:.5f}")

    log_entry = {
        "node":         "generate",
        "status":       "done",
        "message":      f"Generated answer using {source_label} context",
        "time_ms":      round(ttft * 1000),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    return {
        **state,
        "answer":         answer,
        "ttft":           round(ttft, 3),
        "input_tokens":   input_tokens,
        "output_tokens":  output_tokens,
        "simulated_cost": round(simulated_cost, 6),
        "node_log":       state.get("node_log", []) + [log_entry],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  BUILD GRAPH
# ══════════════════════════════════════════════════════════════════════════════

def build_graph():
    g = StateGraph(RAGState)

    g.add_node("retrieve",        retrieve)
    g.add_node("grade_relevance", grade_relevance)
    g.add_node("web_search",      web_search)
    g.add_node("generate",        generate)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "grade_relevance")

    g.add_conditional_edges(
        "grade_relevance",
        route_after_grading,
        {
            "generate":  "generate",
            "web_search": "web_search",
        },
    )

    g.add_edge("web_search", "generate")
    g.add_edge("generate",   END)

    return g.compile()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN — interactive loop
# ══════════════════════════════════════════════════════════════════════════════

def print_result(result: dict):
    print("\n" + "=" * 60)
    print("  SENTINEL RAG — RESULT")
    print("=" * 60)
    print(f"\nQUERY    : {result['question']}")
    print(f"\nANSWER   :\n{result['answer']}")
    print(f"\nMETRICS")
    print(f"   Route          : {'Local Docs' if result.get('route') != 'web_search' else 'Web Fallback'}")
    print(f"   Relevance Grade: {result.get('grade', 'N/A').upper()}")
    print(f"   TTFT           : {result.get('ttft', 0):.3f}s")
    print(f"   Input tokens   : ~{result.get('input_tokens', 0)}")
    print(f"   Output tokens  : ~{result.get('output_tokens', 0)}")
    print(f"   Simulated cost : ${result.get('simulated_cost', 0):.6f}")
    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("  SentinelRAG — Production-Grade RAG Pipeline")
    print("  Retrieve -> Validate -> Generate -> Measure")
    print("  Gurugram University B.Tech Project")
    print("=" * 60)

    try:
        setup_observability()
    except Exception as e:
        print(f"[sentinel] WARNING: Phoenix not running: {e}")
        print("[sentinel] Run 'python launch_phoenix.py' in another terminal.")

    graph = build_graph()
    print("\n[sentinel] Pipeline ready. Type 'quit' to exit.\n")

    while True:
        question = input("Ask a question: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not question:
            continue

        initial_state: RAGState = {
            "question":       question,
            "documents":      [],
            "grade":          "",
            "web_context":    "",
            "answer":         "",
            "ttft":           0.0,
            "input_tokens":   0,
            "output_tokens":  0,
            "simulated_cost": 0.0,
            "route":          "generate",
            "node_log":       [],
        }

        result = graph.invoke(initial_state, config={"run_name": "SentinelRAG_Pipeline"})
        print_result(result)
