# 🛡️ SentinelRAG: Production-Grade Observability Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20(Llama%203.2)-orange.svg)](https://ollama.com/)
[![Arize Phoenix](https://img.shields.io/badge/Observability-Arize%20Phoenix-green.svg)](https://phoenix.arize.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

SentinelRAG is a high-performance RAG (Retrieval-Augmented Generation) system built with **LangGraph** and **ChromaDB**, focused on extreme observability. It provides real-time metrics, node-level tracing, and automated CI/CD gating—all running **100% locally and for free** using Ollama.

## 🚀 Key Features

-   **Agentic Self-Correction**: LLM-based grader ensures document relevance before generation.
-   **Zero-Cost Web Fallback**: Uses **DuckDuckGo Search** and **Scrapling** to autonomously find and extract real-time internet context when local knowledge is insufficient. No API keys required!
-   **Full Observability**: Integrated with Arize Phoenix for deep tracing of every retrieval and generation step.
-   **Automated Evaluation**: Built-in CI/CD gating using **RAGAS** to ensure answer faithfulness and reliability.
-   **Local-First Architecture**: 100% privacy-focused. Your data never leaves your environment.

## 🛠️ Tech Stack

-   **Orchestration**: LangGraph
-   **Vector Database**: ChromaDB
-   **Embedding & LLM**: Ollama (Llama 3.2)
-   **Web Extraction**: Scrapling (StealthyFetcher)
-   **Search**: DuckDuckGo
-   **Observability**: Arize Phoenix / OpenTelemetry
-   **Evaluation**: RAGAS

## 📂 Project Structure

```text
SentinelRAG/
├── chroma_db/          # Persistent vector store
├── eval_gate.py        # CI/CD evaluation script
├── golden_dataset.json # Ground truth for evaluation
├── launch_phoenix.py   # Background observability launcher
├── observability.py    # OTLP tracing configuration
├── rag_system.py       # Main LangGraph pipeline
└── requirements.txt    # Project dependencies
```

## 📥 Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/Akshu24Tech/RAG-Ops-Sentinel.git
    cd RAG-Ops-Sentinel
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Ollama**:
    Ensure [Ollama](https://ollama.com/) is running and the model is pulled:
    ```bash
    ollama pull llama3.2
    ```

## 🚦 Usage

### 1. Launch the Observability Dashboard
Run the dedicated launcher in a separate terminal to keep the dashboard alive:
```bash
python launch_phoenix.py
```
Access the dashboard at: [http://localhost:6006](http://localhost:6006)

### 2. Run the RAG System
Execute the main RAG pipeline:
```bash
python rag_system.py
```

### 3. Run CI/CD Evaluation Gate
Test the system against the `golden_dataset.json`:
```bash
python eval_gate.py
```
*Note: The script exits with status 1 if the Faithfulness score is < 0.85.*

## 📊 Metrics Explained

-   **TTFT (Time To First Token)**: Measures UI responsiveness.
-   **Cost Analysis**: Simulated local cost estimates based on token usage.
-   **Faithfulness (RAGAS)**: High-precision metric to ensure answers are grounded in context.

## 🔒 Privacy & Cost
Everything runs locally. No data leaves your machine, and **zero API keys** are needed.

---
Built with ❤️ for High-Performance RAG Engineering.
