# 🛡️ SentinelRAG — Production-Grade RAG Observability Pipeline

> **B.Tech Year Project** | Department of Computer Science & Engineering (AI)

[![CI Gate](https://img.shields.io/badge/CI%20Gate-RAGAS%20%E2%89%A5%200.75-brightgreen)](https://github.com/Akshu24Tech/Sentinel-RAG)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.28-blue)](https://github.com/langchain-ai/langgraph)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5.5-orange)](https://www.trychroma.com/)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.2-purple)](https://ollama.com/)
[![Phoenix](https://img.shields.io/badge/Arize%20Phoenix-4.29.0-red)](https://phoenix.arize.com/)

---

## What is SentinelRAG?

SentinelRAG is a **Retrieval-Augmented Generation (RAG)** system engineered for **reliability and observability**. It solves the "black-box" problem in AI pipelines by making every step visible, measurable, and automatically quality-gated.

**Core idea:** `Retrieve → Validate → Generate → Measure`

The system features a **premium web dashboard** for real-time interaction and metric visualization, and a **GitHub Actions CI pipeline** that automatically blocks deployments if the AI pipeline quality degrades.

---

## 🏗️ Architecture

```
User Query
    │
    ▼
┌─────────────┐
│   RETRIEVE  │  ChromaDB cosine similarity search (k=3)
└──────┬──────┘
       │
    ▼
┌─────────────────┐
│ GRADE RELEVANCE │  Cosine Similarity Threshold (>= 0.20)
└──────┬──────────┘
       │
  ┌────┴────┐
  │         │
  ▼         ▼
[yes]      [no]
  │         │
  │    ┌────────────┐
  │    │ WEB SEARCH │  DuckDuckGo + Scrapling fallback
  │    └─────┬──────┘
  │          │
  └────┬─────┘
       │
    ▼
┌──────────┐
│ GENERATE │  ChatOllama (llama3.2, temp=0)
└──────────┘
       │
    Metrics: TTFT, tokens, cost → Phoenix traces
```

---

## 🛡️ Three Guardrails

| Guardrail | What it does | Tool |
|-----------|-------------|------|
| **A — Observability** | Traces every node (retrieve/grade/generate) with timing and token counts | Arize Phoenix + OpenTelemetry |
| **B — Self-Correction** | Blocks irrelevant context; routes to web fallback automatically | LangGraph conditional edges |
| **C — QA Gate** | Blocks CI/CD if metrics fall below threshold; prevents hallucinating models from shipping | RAGAS (faithfulness & answer relevancy) + eval_gate.py |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) installed and running
- `llama3.2` model pulled

```bash
# 1. Pull the model
ollama pull llama3.2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Ingest documents into ChromaDB
python ingest.py

# 4. Run the Streamlit Web Application
streamlit run app.py
# → App: http://localhost:8501

# Optional: Start Phoenix observability dashboard
python launch_phoenix.py
# → Dashboard: http://localhost:6006

# Optional: Run the RAGAS evaluation gate
python eval_gate.py
```

---

## 📊 Metrics Tracked

| Metric | Description |
|--------|-------------|
| **TTFT** | Time-To-First-Token (user-perceived latency) |
| **Input tokens** | Estimated prompt token count |
| **Output tokens** | Estimated response token count |
| **Simulated cost** | Estimated API cost equivalent |
| **Faithfulness** | RAGAS score — hallucination measure (threshold 0.75) |
| **Answer Relevancy**| RAGAS score — off-topic measure (threshold 0.70) |
| **Relevance grade** | Pass/fail based on similarity cutoff |

---

## 🗂️ Project Structure

```
RAG-Ops-Sentinel/
├── docs/
│   └── *.pdf                    # Knowledge corpus (e.g., University Syllabus)
├── data/
│   └── golden_dataset.json      # 25 golden Q&A pairs for evaluation
├── app.py                       # Premium Streamlit web dashboard
├── ingest.py                    # Step 1 — Chunk & embed docs into ChromaDB
├── rag_system.py                # Step 2 — Full LangGraph RAG pipeline
├── launch_phoenix.py            # Step 4 — Arize Phoenix OTEL dashboard
├── eval_gate.py                 # Step 5 — RAGAS faithfulness CI gate
├── requirements.txt
└── .github/workflows/rag_ci.yml
```

---

## 🖥️ Web Dashboard

The included web dashboard (`app.py`) is built with Streamlit and provides:

- **Live system health** — Ollama, ChromaDB, and Phoenix status
- **Interactive query panel** — Ask questions and see grounded answers
- **Pipeline visualizer** — See which nodes activated (retrieve → grade → generate/web)
- **Metric cards** — TTFT, token counts, cost, route decision
- **RAGAS evaluation runner** — Trigger the CI gate from the browser
- **Execution log** — Step-by-step node output trace

---

## 🔧 Troubleshooting

| Problem | Fix |
|---------|-----|
| `ChromaDB not found` | Run `python ingest.py` first |
| `Ollama connection refused` | Run `ollama serve` in a terminal |
| `Phoenix not receiving traces` | Run `python launch_phoenix.py` before `api_server.py` |
| `RAGAS score = 0` | Ollama LLM judge needs `llama3.2` pulled |
| `eval_gate.py exits with 1` | Metric < threshold — check your docs or golden dataset |
| `CORS error in browser` | Make sure `api_server.py` is running on port 8000 |

---

## 🛠️ Tech Stack

| Category | Tool |
|----------|------|
| Core Runtime | Python 3.10+, LangGraph 0.2.28, LangChain 0.2.16 |
| LLM | Ollama · llama3.2 (local, no API key) |
| Vector Store | ChromaDB 0.5.5 (persistent, local) |
| Web Fallback | DuckDuckGo-Search + Scrapling (StealthyFetcher) |
| Observability | Arize Phoenix 4.29.0, OpenTelemetry, OpenInference |
| Evaluation | RAGAS 0.1.21 (faithfulness & answer relevancy) |
| API Layer | FastAPI 0.111.0 + Uvicorn |
| Frontend | Streamlit |
| CI/CD | GitHub Actions |

---

## 🔮 Future Scope

- Containerized Docker deployment with GitHub Actions integration
- Multi-user authentication for the web dashboard
- Advanced chunking strategies for nested tables
- p50/p95 latency dashboards with alerts

---

*LLMOps · MLOps · Retrieval-Augmented Generation · Gurugram University 2026*
*Built with ❤️ by Akshu Grewal · Ishantnu · Anish Singh Rawat*
