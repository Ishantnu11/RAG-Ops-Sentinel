"""
basic_rag.py — Simple RAG with NO guardrails.
Used ONLY for comparison against SentinelRAG.

This is what a standard RAG tutorial looks like:
- No relevance grading
- No web fallback
- No observability
- No evaluation gate
- No metrics

Usage:
    python basic_rag.py
"""

import time
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ─── CONFIG ──────────────────────────────────────────────────
CHROMA_DIR  = "./chroma_db"
EMBED_MODEL = "llama3.2"
CHAT_MODEL  = "llama3.2"
RETRIEVAL_K = 3

# ─── SETUP ───────────────────────────────────────────────────
embeddings  = OllamaEmbeddings(model=EMBED_MODEL)
vectorstore = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings,
)
llm = ChatOllama(model=CHAT_MODEL, temperature=0)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Answer the question using the provided context."),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])
chain = PROMPT | llm | StrOutputParser()

def ask(question: str) -> dict:
    """Basic RAG: retrieve → generate. No validation whatsoever."""

    # Step 1: Retrieve (blind — no grading)
    t0   = time.time()
    docs = vectorstore.similarity_search(question, k=RETRIEVAL_K)
    t_retrieve = round(time.time() - t0, 3)

    # Step 2: Generate directly (no grader, no fallback)
    context = "\n\n".join([d.page_content for d in docs])
    t1      = time.time()
    answer  = chain.invoke({"context": context, "question": question})
    t_gen   = round(time.time() - t1, 3)

    return {
        "question":    question,
        "answer":      answer,
        "t_retrieve":  t_retrieve,
        "t_generate":  t_gen,
        "total_time":  round(t_retrieve + t_gen, 3),
        "route":       "Local Only (no fallback)",
        "graded":      "No grading",
        "observability": "None",
        "eval_gate":   "None",
    }

def print_result(r: dict):
    print("\n" + "=" * 55)
    print("  BASIC RAG — RESULT (No Guardrails)")
    print("=" * 55)
    print(f"❓ Question : {r['question']}")
    print(f"💬 Answer   :\n{r['answer']}")
    print(f"\n📊 Metrics")
    print(f"   Retrieve time : {r['t_retrieve']}s")
    print(f"   Generate time : {r['t_generate']}s")
    print(f"   Total time    : {r['total_time']}s")
    print(f"   Route         : {r['route']}")
    print(f"   Grading       : {r['graded']}")
    print(f"   Observability : {r['observability']}")
    print(f"   Eval Gate     : {r['eval_gate']}")
    print("=" * 55)

if __name__ == "__main__":
    print("=" * 55)
    print("  Basic RAG — No Guardrails")
    print("  (Comparison baseline for SentinelRAG)")
    print("=" * 55)
    print("\nType 'quit' to exit.\n")

    while True:
        question = input("🔍 Ask: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue
        result = ask(question)
        print_result(result)
