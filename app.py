"""
app.py — SentinelRAG Streamlit Web Interface

A production-grade UI for the SentinelRAG pipeline.
Shows the full pipeline execution, metrics, traces, and evaluation.

Usage:
    streamlit run app.py

Make sure Ollama is running and ingest.py has been executed first.
"""

import time
import json
import re
import sys
import os
from typing import TypedDict, List, Literal
from datetime import datetime

import streamlit as st

# ─── Page config MUST be first Streamlit call ─────────────────────────────────
st.set_page_config(
    page_title="SentinelRAG",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;600;700;800&display=swap');

/* Base */
html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}

/* Dark background */
.stApp {
    background: #0a0e1a;
    color: #e2e8f0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f1729 !important;
    border-right: 1px solid #1e2d4a;
}

section[data-testid="stSidebar"] * {
    color: #94a3b8 !important;
}

/* Header */
.sentinel-header {
    background: linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0f1729 100%);
    border: 1px solid #1e3a5f;
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}

.sentinel-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(56, 189, 248, 0.06) 0%, transparent 70%);
    pointer-events: none;
}

.sentinel-header h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2.4rem;
    color: #f8fafc;
    margin: 0 0 6px 0;
    letter-spacing: -0.5px;
}

.sentinel-header p {
    color: #64748b;
    font-size: 0.95rem;
    margin: 0;
    font-family: 'JetBrains Mono', monospace;
}

.sentinel-badge {
    display: inline-block;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: #38bdf8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    margin-right: 8px;
    margin-bottom: 16px;
    letter-spacing: 0.5px;
}

/* Pipeline steps */
.pipeline-container {
    display: flex;
    align-items: center;
    gap: 0;
    margin: 20px 0;
    overflow-x: auto;
    padding: 4px 0;
}

.pipeline-step {
    display: flex;
    align-items: center;
    gap: 0;
    flex-shrink: 0;
}

.pipeline-node {
    background: #131d35;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 10px 16px;
    text-align: center;
    min-width: 110px;
    transition: all 0.3s ease;
}

.pipeline-node.active {
    background: rgba(56, 189, 248, 0.1);
    border-color: #38bdf8;
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.15);
}

.pipeline-node.done {
    background: rgba(34, 197, 94, 0.08);
    border-color: #22c55e;
}

.pipeline-node.web {
    background: rgba(251, 146, 60, 0.08);
    border-color: #fb923c;
}

.pipeline-node .node-icon {
    font-size: 1.3rem;
    display: block;
    margin-bottom: 4px;
}

.pipeline-node .node-label {
    font-size: 0.7rem;
    font-family: 'JetBrains Mono', monospace;
    color: #64748b;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.pipeline-node.active .node-label { color: #38bdf8; }
.pipeline-node.done .node-label  { color: #22c55e; }
.pipeline-node.web .node-label   { color: #fb923c; }

.pipeline-arrow {
    color: #1e3a5f;
    font-size: 1.2rem;
    padding: 0 4px;
    flex-shrink: 0;
}

/* Metric cards */
.metric-card {
    background: #0f1729;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    height: 100%;
}

.metric-card .metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    font-weight: 700;
    color: #38bdf8;
    display: block;
    margin-bottom: 4px;
}

.metric-card .metric-label {
    font-size: 0.75rem;
    color: #475569;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

.metric-card.green .metric-value { color: #22c55e; }
.metric-card.orange .metric-value { color: #fb923c; }
.metric-card.purple .metric-value { color: #a78bfa; }

/* Answer box */
.answer-box {
    background: #0f1729;
    border: 1px solid #1e3a5f;
    border-left: 3px solid #38bdf8;
    border-radius: 0 12px 12px 0;
    padding: 24px 28px;
    font-size: 0.95rem;
    line-height: 1.7;
    color: #cbd5e1;
    margin: 16px 0;
}

/* Route badge */
.route-local {
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
    color: #22c55e;
    padding: 4px 14px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
}

.route-web {
    background: rgba(251, 146, 60, 0.1);
    border: 1px solid rgba(251, 146, 60, 0.3);
    color: #fb923c;
    padding: 4px 14px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
}

/* Chunk cards */
.chunk-card {
    background: #0a0e1a;
    border: 1px solid #1e2d4a;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #64748b;
    line-height: 1.6;
    position: relative;
}

.chunk-card.relevant {
    border-color: rgba(34, 197, 94, 0.3);
    color: #94a3b8;
}

.chunk-card .chunk-badge {
    position: absolute;
    top: 10px;
    right: 12px;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
}

.chunk-card.relevant .chunk-badge {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
}

.chunk-card.irrelevant .chunk-badge {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border-color: rgba(239, 68, 68, 0.2);
}

/* Log terminal */
.log-terminal {
    background: #050810;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    line-height: 1.8;
    max-height: 280px;
    overflow-y: auto;
    color: #475569;
}

.log-terminal .log-time   { color: #1e3a5f; }
.log-terminal .log-node   { color: #38bdf8; font-weight: 600; }
.log-terminal .log-ok     { color: #22c55e; }
.log-terminal .log-warn   { color: #fb923c; }
.log-terminal .log-metric { color: #a78bfa; }

/* Section title */
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.8rem;
    font-weight: 700;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 12px;
    margin-top: 24px;
}

/* History item */
.history-item {
    background: #0f1729;
    border: 1px solid #1e2d4a;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
    cursor: pointer;
    transition: border-color 0.2s;
}

.history-item:hover {
    border-color: #38bdf8;
}

.history-item .hi-question {
    font-size: 0.85rem;
    color: #94a3b8;
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.history-item .hi-meta {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #334155;
}

/* Eval result */
.eval-pass {
    background: rgba(34, 197, 94, 0.08);
    border: 1px solid rgba(34, 197, 94, 0.25);
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
}

.eval-fail {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
}

/* Input override */
.stTextInput input, .stTextArea textarea {
    background: #0f1729 !important;
    border: 1px solid #1e3a5f !important;
    color: #e2e8f0 !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.1) !important;
}

/* Button override */
.stButton button {
    background: linear-gradient(135deg, #0ea5e9, #0284c7) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    padding: 10px 28px !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.3px !important;
    transition: all 0.2s !important;
}

.stButton button:hover {
    background: linear-gradient(135deg, #38bdf8, #0ea5e9) !important;
    transform: translateY(-1px) !important;
}

/* Divider */
hr {
    border-color: #1e2d4a !important;
    margin: 24px 0 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════

if "history" not in st.session_state:
    st.session_state.history = []

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "pipeline_logs" not in st.session_state:
    st.session_state.pipeline_logs = []


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE IMPORT (lazy, with error handling)
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def load_pipeline():
    """Load the RAG pipeline once and cache it."""
    try:
        from langchain_ollama import ChatOllama, OllamaEmbeddings
        from langchain_chroma import Chroma
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.documents import Document
        from langgraph.graph import StateGraph, END
        from duckduckgo_search import DDGS

        CHROMA_DIR  = "./chroma_db"
        EMBED_MODEL = "llama3.2"
        CHAT_MODEL  = "llama3.2"
        RETRIEVAL_K = 3

        embeddings  = OllamaEmbeddings(model=EMBED_MODEL)
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
        )
        llm = ChatOllama(model=CHAT_MODEL, temperature=0)

        return {
            "vectorstore": vectorstore,
            "llm":         llm,
            "k":           RETRIEVAL_K,
            "status":      "ok",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
#  CORE PIPELINE LOGIC (simplified for Streamlit — no LangGraph needed)
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(question: str, pipeline: dict) -> dict:
    """Execute full RAG pipeline and return detailed result dict."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from duckduckgo_search import DDGS

    logs   = []
    result = {}

    def log(tag: str, msg: str, level: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        logs.append({"ts": ts, "tag": tag, "msg": msg, "level": level})

    vectorstore = pipeline["vectorstore"]
    llm         = pipeline["llm"]
    k           = pipeline["k"]

    # ── NODE 1: RETRIEVE ──────────────────────────────────────────────────────
    log("RETRIEVE", f"Similarity search k={k}", "info")
    t_retrieve = time.time()
    retriever  = vectorstore.as_retriever(search_kwargs={"k": k})
    docs       = retriever.invoke(question)
    t_retrieve = round(time.time() - t_retrieve, 3)
    log("RETRIEVE", f"Found {len(docs)} chunk(s) in {t_retrieve}s", "ok")

    result["retrieve_time"] = t_retrieve
    result["raw_docs"]      = docs

    # ── NODE 2: GRADE RELEVANCE ───────────────────────────────────────────────
    log("GRADER", "Evaluating chunk relevance...", "info")
    t_grade = time.time()

    GRADE_PROMPT = ChatPromptTemplate.from_messages([
        ("system",
         "You are a relevance grader. Answer ONLY 'yes' if the document chunk "
         "is useful to answer the question, or 'no' if it is not. "
         "Output only: yes or no."),
        ("human", "Question: {question}\n\nDocument chunk:\n{document}"),
    ])
    grade_chain = GRADE_PROMPT | llm | StrOutputParser()

    graded_docs = []
    grade_results = []
    for doc in docs:
        g = grade_chain.invoke({
            "question": question,
            "document": doc.page_content,
        }).strip().lower()
        is_relevant = "yes" in g
        grade_results.append({"doc": doc, "relevant": is_relevant})
        if is_relevant:
            graded_docs.append(doc)
        log("GRADER",
            f"{'✓ relevant' if is_relevant else '✗ irrelevant'}: "
            f"{doc.page_content[:60].strip()}...",
            "ok" if is_relevant else "warn")

    t_grade = round(time.time() - t_grade, 3)
    grade   = "yes" if graded_docs else "no"
    log("GRADER", f"Grade: {grade.upper()} — {len(graded_docs)}/{len(docs)} relevant ({t_grade}s)",
        "ok" if grade == "yes" else "warn")

    result["grade"]        = grade
    result["grade_time"]   = t_grade
    result["grade_results"]= grade_results
    result["graded_docs"]  = graded_docs

    # ── NODE 3: WEB FALLBACK (if needed) ─────────────────────────────────────
    web_context = ""
    web_sources = []
    t_web       = 0

    if grade == "no":
        log("WEB", "Routing to web fallback (DuckDuckGo + Scrapling StealthyFetcher)", "warn")
        t_web = time.time()
        try:
            from scrapling import StealthyFetcher
        except ImportError:
            StealthyFetcher = None
            log("WEB", "scrapling not installed — falling back to DDG snippets only", "warn")

        try:
            with DDGS() as ddgs:
                web_results = list(ddgs.text(question, max_results=3))
            for r in web_results:
                url     = r.get("href", "")
                snippet = r.get("body", "")

                # ── Scrapling: fetch full page content ───────────────────────
                page_text = snippet   # default to DDG snippet
                if url and StealthyFetcher is not None:
                    try:
                        log("WEB", f"Scrapling: {url[:60]}...", "info")
                        fetcher   = StealthyFetcher()
                        page      = fetcher.fetch(url, headless=True, network_idle=True)
                        raw_text  = page.get_content()
                        import re as _re
                        page_text = _re.sub(r'\s+', ' ', raw_text).strip()[:1500]
                        log("WEB", f"Scrapled {len(page_text)} chars from {url[:50]}...", "ok")
                    except Exception as scrape_err:
                        log("WEB", f"Scrapling failed ({scrape_err}), using snippet", "warn")
                        page_text = snippet

                web_sources.append({"url": url, "snippet": page_text})
                web_context += f"\n[Source: {url}]\n{page_text}\n"
        except Exception as e:
            log("WEB", f"DuckDuckGo error: {e}", "warn")
            web_context = "Web search unavailable."

        t_web = round(time.time() - t_web, 3)
        log("WEB", f"Web fallback complete ({t_web}s)", "ok")

    result["web_context"] = web_context
    result["web_sources"] = web_sources
    result["web_time"]    = t_web
    result["route"]       = "web" if grade == "no" else "local"

    # ── NODE 4: GENERATE ──────────────────────────────────────────────────────
    log("GENERATE", "Generating answer...", "info")
    context = (
        web_context if grade == "no"
        else "\n\n".join([d.page_content for d in graded_docs])
    )

    GEN_PROMPT = ChatPromptTemplate.from_messages([
        ("system",
         "You are a helpful assistant. Answer the question using ONLY the "
         "provided context. Be clear and concise. If context is insufficient, say so."),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ])
    gen_chain = GEN_PROMPT | llm | StrOutputParser()

    t_gen  = time.time()
    answer = gen_chain.invoke({"context": context, "question": question})
    t_gen  = round(time.time() - t_gen, 3)

    # Metrics
    input_tokens  = (len(context) + len(question)) // 4
    output_tokens = len(answer) // 4
    sim_cost      = round((input_tokens + output_tokens) / 1000 * 0.001, 6)
    ttft          = t_gen  # single-shot approximation

    log("GENERATE", f"Answer generated in {t_gen}s", "ok")
    log("METRIC",   f"TTFT: {ttft}s | Tokens in: ~{input_tokens} | out: ~{output_tokens}", "metric")
    log("METRIC",   f"Simulated cost: ${sim_cost}", "metric")

    result.update({
        "question":      question,
        "answer":        answer,
        "ttft":          ttft,
        "gen_time":      t_gen,
        "input_tokens":  input_tokens,
        "output_tokens": output_tokens,
        "sim_cost":      sim_cost,
        "total_time":    round(t_retrieve + t_grade + t_web + t_gen, 3),
        "logs":          logs,
        "timestamp":     datetime.now().strftime("%H:%M:%S"),
    })

    return result


# ══════════════════════════════════════════════════════════════════════════════
#  UI — HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="sentinel-header">
    <span class="sentinel-badge">🛡️ SENTINELRAG</span>
    <span class="sentinel-badge">LLMOPS</span>
    <span class="sentinel-badge">GURUGRAM UNIVERSITY</span>
    <h1>SentinelRAG</h1>
    <p>Retrieve → Validate → Generate → Measure &nbsp;|&nbsp; Production-Grade RAG Observability Pipeline</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🛡️ SentinelRAG")
    st.markdown("---")

    # Pipeline status
    st.markdown("**PIPELINE STATUS**")
    pipeline = load_pipeline()

    if pipeline["status"] == "ok":
        st.success("Pipeline Ready")
        st.markdown(f"""
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #475569; line-height: 2;">
        Model &nbsp;&nbsp;&nbsp;: llama3.2<br>
        VectorDB : ChromaDB (local)<br>
        Observ.  : Arize Phoenix<br>
        Eval     : RAGAS ≥ 0.85<br>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error("Pipeline Error")
        st.caption(pipeline.get("error", "Unknown error"))
        st.markdown("""
        **Fix:**
        ```bash
        ollama serve
        python ingest.py
        ```
        """)

    st.markdown("---")

    # Stats
    if st.session_state.history:
        st.markdown("**SESSION STATS**")
        total_q   = len(st.session_state.history)
        web_count = sum(1 for h in st.session_state.history if h.get("route") == "web")
        avg_ttft  = round(
            sum(h.get("ttft", 0) for h in st.session_state.history) / total_q, 3
        )
        st.markdown(f"""
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #475569; line-height: 2.2;">
        Queries asked &nbsp;: {total_q}<br>
        Web fallbacks &nbsp;: {web_count}<br>
        Avg TTFT &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {avg_ttft}s<br>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**QUERY HISTORY**")
        for i, h in enumerate(reversed(st.session_state.history[-8:])):
            route_icon = "🌐" if h.get("route") == "web" else "📄"
            st.markdown(f"""
            <div class="history-item">
                <div class="hi-question">{route_icon} {h['question'][:45]}{'...' if len(h['question']) > 45 else ''}</div>
                <div class="hi-meta">TTFT: {h.get('ttft', 0)}s &nbsp;|&nbsp; {h.get('timestamp', '')}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size: 0.7rem; color: #1e3a5f; line-height: 1.8; font-family: 'JetBrains Mono', monospace;">
    Akshu Grewal<br>
    Ishantnu<br>
    Anish Singh Rawat<br>
    B.Tech CSE (AI) · 2026
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Ask & Answer",
    "📊 Pipeline Trace",
    "🧪 Evaluation Gate",
    "📖 About",
])


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 1 — ASK & ANSWER
# ─────────────────────────────────────────────────────────────────────────────

with tab1:
    col_q, col_btn = st.columns([5, 1])

    with col_q:
        question = st.text_input(
            "",
            placeholder="Ask anything about your documents... (e.g. What is RAG? What is TTFT?)",
            label_visibility="collapsed",
        )

    with col_btn:
        ask_btn = st.button("Ask →", use_container_width=True)

    # Sample questions
    st.markdown('<p class="section-title">Try these</p>', unsafe_allow_html=True)
    sample_cols = st.columns(3)
    samples = [
        "What is Retrieval-Augmented Generation?",
        "What is TTFT and why does it matter?",
        "How does ChromaDB work in a RAG pipeline?",
        "What is the faithfulness threshold in RAGAS?",
        "What makes LangGraph useful for RAG?",
        "What is observability in LLM systems?",
    ]
    selected_sample = None
    for i, col in enumerate(sample_cols):
        with col:
            if st.button(samples[i], key=f"s{i}", use_container_width=True):
                selected_sample = samples[i]
            if st.button(samples[i + 3], key=f"s{i+3}", use_container_width=True):
                selected_sample = samples[i + 3]

    # Resolve question
    final_question = selected_sample or (question if ask_btn and question else None)

    if final_question:
        if pipeline["status"] != "ok":
            st.error("Pipeline not ready. Start Ollama and run `python ingest.py` first.")
        else:
            # Pipeline execution with progress
            st.markdown("---")
            st.markdown('<p class="section-title">Pipeline Execution</p>', unsafe_allow_html=True)

            # Animated pipeline visualization
            pipeline_placeholder = st.empty()

            def show_pipeline(active_node: str, done_nodes: list, web_active: bool = False):
                nodes = [
                    ("retrieve",  "🔍", "Retrieve"),
                    ("grade",     "⚖️",  "Grade"),
                    ("web",       "🌐", "Web"),
                    ("generate",  "✨", "Generate"),
                    ("measure",   "📊", "Measure"),
                ]
                html = '<div class="pipeline-container">'
                for i, (nid, icon, label) in enumerate(nodes):
                    if nid == "web":
                        cls = "web" if web_active else ("done" if "web" in done_nodes else "pipeline-node")
                    elif nid == active_node:
                        cls = "active"
                    elif nid in done_nodes:
                        cls = "done"
                    else:
                        cls = ""
                    html += f'<div class="pipeline-step">'
                    html += f'<div class="pipeline-node {cls}"><span class="node-icon">{icon}</span><span class="node-label">{label}</span></div>'
                    if i < len(nodes) - 1:
                        html += '<span class="pipeline-arrow">→</span>'
                    html += '</div>'
                html += '</div>'
                pipeline_placeholder.markdown(html, unsafe_allow_html=True)

            # Run with step-by-step visualization
            show_pipeline("retrieve", [])
            time.sleep(0.3)

            with st.spinner("Running SentinelRAG pipeline..."):
                result = run_pipeline(final_question, pipeline)

            show_pipeline("measure", ["retrieve", "grade", "web", "generate", "measure"],
                          web_active=(result["route"] == "web"))

            # Store in history
            st.session_state.last_result = result
            st.session_state.history.append(result)

            # ── METRICS ROW ───────────────────────────────────────────────────
            st.markdown("---")
            st.markdown('<p class="section-title">Metrics</p>', unsafe_allow_html=True)

            m1, m2, m3, m4, m5 = st.columns(5)
            metrics = [
                (m1, f"{result['ttft']}s",           "TTFT",          "blue"),
                (m2, f"~{result['input_tokens']}",   "Input Tokens",  "purple"),
                (m3, f"~{result['output_tokens']}",  "Output Tokens", "purple"),
                (m4, f"${result['sim_cost']}",       "Est. Cost",     "green"),
                (m5, f"{result['total_time']}s",     "Total Time",    "orange"),
            ]
            color_map = {
                "blue": "", "purple": "purple", "green": "green", "orange": "orange"
            }
            for col, val, label, color in metrics:
                with col:
                    st.markdown(f"""
                    <div class="metric-card {color_map[color]}">
                        <span class="metric-value">{val}</span>
                        <span class="metric-label">{label}</span>
                    </div>
                    """, unsafe_allow_html=True)

            # ── ROUTE BADGE ───────────────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            route_html = (
                '<span class="route-local">📄 LOCAL DOCS</span>'
                if result["route"] == "local"
                else '<span class="route-web">🌐 WEB FALLBACK</span>'
            )
            grade_color = "#22c55e" if result["grade"] == "yes" else "#ef4444"
            st.markdown(
                f'Route: {route_html} &nbsp;&nbsp; '
                f'<span style="font-family: JetBrains Mono; font-size: 0.78rem; color: {grade_color};">'
                f'Grade: {result["grade"].upper()}</span>',
                unsafe_allow_html=True
            )

            # ── ANSWER ────────────────────────────────────────────────────────
            st.markdown('<p class="section-title">Answer</p>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="answer-box">
                {result['answer'].replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)

            # ── RETRIEVED CHUNKS ──────────────────────────────────────────────
            st.markdown('<p class="section-title">Retrieved & Graded Chunks</p>', unsafe_allow_html=True)
            for i, gr in enumerate(result.get("grade_results", [])):
                cls  = "relevant" if gr["relevant"] else "irrelevant"
                badge = "RELEVANT ✓" if gr["relevant"] else "IRRELEVANT ✗"
                st.markdown(f"""
                <div class="chunk-card {cls}">
                    <span class="chunk-badge">{badge}</span>
                    <strong style="color:#475569; font-size:0.68rem;">CHUNK {i+1}</strong><br>
                    {gr['doc'].page_content[:300].strip()}...
                </div>
                """, unsafe_allow_html=True)

            # ── WEB SOURCES ───────────────────────────────────────────────────
            if result["route"] == "web" and result.get("web_sources"):
                st.markdown('<p class="section-title">Web Sources Used</p>', unsafe_allow_html=True)
                for src in result["web_sources"]:
                    if src.get("url"):
                        st.markdown(f"""
                        <div class="chunk-card relevant">
                            <strong style="color:#fb923c; font-size:0.68rem;">🌐 WEB SOURCE</strong><br>
                            <a href="{src['url']}" style="color:#38bdf8; font-size:0.75rem;">{src['url']}</a><br>
                            <span style="color:#64748b;">{src.get('snippet', '')[:200]}</span>
                        </div>
                        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 2 — PIPELINE TRACE
# ─────────────────────────────────────────────────────────────────────────────

with tab2:
    st.markdown('<p class="section-title">Execution Trace Log</p>', unsafe_allow_html=True)

    if not st.session_state.last_result:
        st.markdown("""
        <div style="text-align:center; padding: 60px 20px; color: #1e3a5f;">
            <div style="font-size: 3rem; margin-bottom: 16px;">📡</div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
                No trace yet — ask a question in the Ask & Answer tab
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        result = st.session_state.last_result
        logs   = result.get("logs", [])

        # Trace terminal
        log_html = '<div class="log-terminal">'
        for entry in logs:
            level_class = {
                "ok":     "log-ok",
                "warn":   "log-warn",
                "metric": "log-metric",
                "info":   "log-node",
            }.get(entry["level"], "")
            log_html += (
                f'<div>'
                f'<span class="log-time">[{entry["ts"]}]</span> '
                f'<span class="log-node">[{entry["tag"]}]</span> '
                f'<span class="{level_class}">{entry["msg"]}</span>'
                f'</div>'
            )
        log_html += '</div>'
        st.markdown(log_html, unsafe_allow_html=True)

        # Node timing breakdown
        st.markdown('<p class="section-title">Node Timing Breakdown</p>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        timings = [
            (c1, "🔍 Retrieve",  result.get("retrieve_time", 0), "#38bdf8"),
            (c2, "⚖️ Grade",     result.get("grade_time",   0), "#a78bfa"),
            (c3, "🌐 Web",       result.get("web_time",     0), "#fb923c"),
            (c4, "✨ Generate",  result.get("gen_time",     0), "#22c55e"),
        ]
        for col, label, t, color in timings:
            with col:
                st.markdown(f"""
                <div class="metric-card" style="border-color: {color}22;">
                    <span class="metric-value" style="color:{color}; font-size:1.4rem;">{t}s</span>
                    <span class="metric-label">{label}</span>
                </div>
                """, unsafe_allow_html=True)

        # Phoenix note
        st.markdown("---")
        st.info(
            "🔭 **Full OpenTelemetry traces** are also available in Arize Phoenix "
            "at **http://localhost:6006** — run `python launch_phoenix.py` to start the dashboard."
        )


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 3 — EVALUATION GATE
# ─────────────────────────────────────────────────────────────────────────────

with tab3:
    st.markdown('<p class="section-title">RAGAS Faithfulness CI Gate</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="chunk-card" style="border-color: #1e3a5f; margin-bottom: 20px;">
        This gate evaluates the pipeline against a golden dataset of question-answer pairs.
        If the <strong style="color:#38bdf8;">faithfulness score &lt; 0.85</strong>, deployment is blocked (exit code 1).
        This is the same pattern used in production MLOps CI/CD pipelines.
    </div>
    """, unsafe_allow_html=True)

    # Load golden dataset preview
    try:
        with open("./data/golden_dataset.json", "r") as f:
            golden = json.load(f)

        st.markdown(f'<p class="section-title">Golden Dataset ({len(golden)} pairs)</p>',
                    unsafe_allow_html=True)
        for i, item in enumerate(golden):
            with st.expander(f"Q{i+1}: {item['question'][:70]}..."):
                st.markdown(f"**Question:** {item['question']}")
                st.markdown(f"**Ground Truth:** {item['ground_truth']}")
                st.markdown("**Reference Context:**")
                for ctx in item.get("reference_contexts", []):
                    st.caption(ctx[:300] + "...")
    except FileNotFoundError:
        st.warning("golden_dataset.json not found. Make sure `data/golden_dataset.json` exists.")

    st.markdown("---")

    if st.button("▶ Run Evaluation Gate", use_container_width=False):
        if pipeline["status"] != "ok":
            st.error("Pipeline not ready.")
        else:
            with st.spinner("Running RAGAS faithfulness evaluation... (this takes 1-2 minutes)"):
                try:
                    import subprocess
                    proc = subprocess.run(
                        [sys.executable, "eval_gate.py"],
                        capture_output=True, text=True, timeout=300
                    )
                    output   = proc.stdout + proc.stderr
                    passed   = proc.returncode == 0

                    # Parse score from output
                    score = None
                    for line in output.split("\n"):
                        if "Faithfulness Score" in line:
                            try:
                                score = float(line.split(":")[-1].strip())
                            except:
                                pass

                    if passed:
                        st.markdown(f"""
                        <div class="eval-pass">
                            <div style="font-size:2.5rem; margin-bottom:8px;">✅</div>
                            <div style="font-family:'Syne',sans-serif; font-size:1.2rem; font-weight:700; color:#22c55e;">
                                CI GATE: PASS
                            </div>
                            <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#64748b; margin-top:8px;">
                                Faithfulness Score: {score if score else 'see log below'} ≥ 0.85
                            </div>
                            <div style="font-size:0.8rem; color:#475569; margin-top:6px;">
                                Pipeline is faithful. Safe to deploy.
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="eval-fail">
                            <div style="font-size:2.5rem; margin-bottom:8px;">❌</div>
                            <div style="font-family:'Syne',sans-serif; font-size:1.2rem; font-weight:700; color:#ef4444;">
                                CI GATE: BLOCKED
                            </div>
                            <div style="font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#64748b; margin-top:8px;">
                                Faithfulness Score: {score if score else 'see log below'} &lt; 0.85
                            </div>
                            <div style="font-size:0.8rem; color:#475569; margin-top:6px;">
                                Hallucination risk detected. Deployment blocked.
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown('<p class="section-title">Evaluation Log</p>', unsafe_allow_html=True)
                    st.code(output, language="bash")

                except subprocess.TimeoutExpired:
                    st.error("Evaluation timed out (>5 min). Ollama may be slow on this hardware.")
                except Exception as e:
                    st.error(f"Error running eval_gate.py: {e}")
                    st.markdown("Run manually: `python eval_gate.py`")


# ─────────────────────────────────────────────────────────────────────────────
#  TAB 4 — ABOUT
# ─────────────────────────────────────────────────────────────────────────────

with tab4:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("""
        ### 🛡️ What is SentinelRAG?

        SentinelRAG is a **production-grade RAG observability pipeline** that
        focuses on engineering reliability — not just chat quality.

        It solves the black-box problem in AI deployments by making every
        step observable, measurable, and automatically tested.

        **Core idea:** `Retrieve → Validate → Generate → Measure`

        ---

        ### 3 Guardrails

        **A — Observability**
        Phoenix traces each node (retrieval / grading / generation) via OpenTelemetry.

        **B — Self-Correction**
        A Grader node blocks irrelevant context and routes to web fallback
        instead of hallucinating.

        **C — QA Gate**
        RAGAS faithfulness gate stops deployment when score < 0.85.

        ---

        ### Tech Stack

        | Layer | Tool |
        |-------|------|
        | LLM | Ollama · llama3.2 (local) |
        | Pipeline | LangGraph |
        | Vector DB | ChromaDB |
        | Web Fallback | DuckDuckGo + Scrapling |
        | Observability | Arize Phoenix + OTLP |
        | Evaluation | RAGAS |
        | UI | Streamlit |
        """)

    with col_b:
        st.markdown("""
        ### Pipeline Flow

        ```
        User Query
             │
             ▼
        ┌─────────────┐
        │   RETRIEVE  │  ChromaDB, k=3
        └──────┬──────┘
               │
               ▼
        ┌─────────────────┐
        │ GRADE RELEVANCE │  LLM → yes/no
        └──────┬──────────┘
               │
          ┌────┴────┐
         yes        no
          │         │
          │    ┌────────────┐
          │    │ WEB SEARCH │  DuckDuckGo
          │    └─────┬──────┘
          └────┬─────┘
               │
               ▼
        ┌──────────┐
        │ GENERATE │  ChatOllama
        └────┬─────┘
             │
             ▼
        TTFT + Tokens + Cost → Phoenix
        ```

        ---

        ### Team

        | Member | Role |
        |--------|------|
        | Akshu Grewal | Pipeline & Routing |
        | Ishantnu | Observability & Metrics |
        | Anish Singh Rawat | Evaluation & CI Gate |

        **Department of Engineering & Technology**
        Gurugram University · B.Tech CSE (AI) · 2026

        ---

        ### Quick Start

        ```bash
        ollama serve
        ollama pull llama3.2
        pip install -r requirements.txt
        python ingest.py
        streamlit run app.py
        ```
        """)
