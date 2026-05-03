"""
eval_gate.py — RAGAS Faithfulness CI Gate.

Loads golden_dataset.json, runs faithfulness evaluation using the local
Ollama LLM as the judge, and exits with code 1 if score < 0.85.

SentinelRAG | Gurugram University B.Tech Project
Authors: Akshu Grewal · Ishantnu · Anish Singh Rawat

Usage:
    python eval_gate.py

Exit codes:
    0 → PASS (faithfulness >= 0.85)
    1 → FAIL (faithfulness < 0.85) — blocks CI/CD
"""

import sys
import json
import time
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ─── CONFIG ──────────────────────────────────────────────────────────────────
GOLDEN_DATASET_PATH    = "./data/golden_dataset.json"
FAITHFULNESS_THRESHOLD = 0.85
RELEVANCY_THRESHOLD    = 0.80
CHAT_MODEL             = "llama3.2"
EMBED_MODEL            = "llama3.2"
CHROMA_DIR             = "./chroma_db"
import os
OLLAMA_BASE_URL        = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

GENERATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Answer the question using ONLY the provided context. Be concise and factual."),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])


def retrieve_context(question: str, k: int = 3) -> str:
    """Retrieve relevant context from ChromaDB."""
    embeddings  = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL
    )
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
    )
    docs = vectorstore.similarity_search(question, k=k)
    return "\n\n".join([d.page_content for d in docs])


def generate_answer(question: str, context: str) -> str:
    """Generate answer using local Ollama LLM."""
    llm   = ChatOllama(
        model=CHAT_MODEL, 
        temperature=0,
        base_url=OLLAMA_BASE_URL
    )
    chain = GENERATE_PROMPT | llm | StrOutputParser()
    return chain.invoke({"question": question, "context": context})


def run_eval() -> dict:
    """
    Run the full RAGAS faithfulness evaluation.
    Returns a dict with score, pass/fail, and per-question results.
    """
    print("=" * 60)
    print("  SentinelRAG — RAGAS Multi-Metric Evaluation Gate")
    print(f"  Thresholds: Faithfulness >= {FAITHFULNESS_THRESHOLD}")
    print(f"              Relevancy    >= {RELEVANCY_THRESHOLD}")
    print("  Authors: Akshu Grewal · Ishantnu · Anish Singh Rawat")
    print("=" * 60)

    with open(GOLDEN_DATASET_PATH, "r") as f:
        golden = json.load(f)

    print(f"\n[eval] Loaded {len(golden)} golden Q&A pair(s)")
    print("[eval] Generating answers from RAG pipeline...\n")

    questions     = []
    answers       = []
    contexts      = []
    ground_truths = []
    per_q_results = []

    for i, item in enumerate(golden):
        q   = item["question"]
        gt  = item["ground_truth"]
        ctx = "\n\n".join(item.get("reference_contexts", []))
        if not ctx:
            ctx = retrieve_context(q)

        t0  = time.time()
        ans = generate_answer(q, ctx)
        elapsed = time.time() - t0

        print(f"  [{i+1}/{len(golden)}] Q: {q[:60]}...")
        print(f"         A: {ans[:80].strip()}...\n")

        questions.append(q)
        answers.append(ans)
        contexts.append([ctx])
        ground_truths.append(gt)
        per_q_results.append({
            "question": q,
            "answer":   ans[:200],
            "elapsed":  round(elapsed, 2),
        })

    # Build HuggingFace Dataset for RAGAS
    eval_dataset = Dataset.from_dict({
        "question":     questions,
        "answer":       answers,
        "contexts":     contexts,
        "ground_truth": ground_truths,
    })

    print("[eval] Running RAGAS multi-metric evaluation...")
    print("[eval] (This uses the local Ollama LLM as judge — may take a moment)\n")

    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper

    llm_wrapper   = LangchainLLMWrapper(llm = ChatOllama(
        model=CHAT_MODEL, 
        temperature=0,
        base_url=OLLAMA_BASE_URL
    ))
    embed_wrapper = LangchainEmbeddingsWrapper(OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL
    ))

    result = evaluate(
        dataset=eval_dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=llm_wrapper,
        embeddings=embed_wrapper,
        raise_exceptions=False,
    )

    faith_score = float(result["faithfulness"])
    rel_score   = float(result["answer_relevancy"])

    print("\n" + "=" * 60)
    print(f"  RAGAS Faithfulness Score : {faith_score:.4f} (Goal: {FAITHFULNESS_THRESHOLD})")
    print(f"  RAGAS Answer Relevancy   : {rel_score:.4f} (Goal: {RELEVANCY_THRESHOLD})")
    
    faith_passed = faith_score >= FAITHFULNESS_THRESHOLD
    rel_passed   = rel_score >= RELEVANCY_THRESHOLD
    overall_pass = faith_passed and rel_passed
    
    print("=" * 60)

    if overall_pass:
        print(f"\n✅ PASS — Both metrics meet thresholds.")
        print("   Pipeline is faithful and relevant. CI gate: OPEN.\n")
    else:
        print(f"\n❌ FAIL — One or more metrics dropped below threshold.")
        if not faith_passed: print(f"      - Faithfulness ({faith_score:.4f}) < {FAITHFULNESS_THRESHOLD}")
        if not rel_passed:   print(f"      - Relevancy ({rel_score:.4f}) < {RELEVANCY_THRESHOLD}")
        print("   Deployment BLOCKED due to quality risks.\n")

    return {
        "faithfulness_score": round(faith_score, 4),
        "relevancy_score":    round(rel_score, 4),
        "passed":             overall_pass,
        "num_questions":      len(golden),
        "per_question":       per_q_results,
    }


if __name__ == "__main__":
    result = run_eval()
    sys.exit(0 if result["passed"] else 1)
