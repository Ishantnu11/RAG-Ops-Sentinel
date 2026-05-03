"""
api_server.py — FastAPI REST bridge for the SentinelRAG Web UI.

Exposes the full RAG pipeline via HTTP so the browser frontend can talk to it.

SentinelRAG | Gurugram University B.Tech Project
Authors: Akshu Grewal · Ishantnu · Anish Singh Rawat

Endpoints:
    GET  /status         — System health check
    POST /query          — Run a RAG query, return answer + metrics
    POST /ingest         — Re-ingest documents into ChromaDB
    GET  /eval           — Run RAGAS evaluation gate
    WS   /ws/query       — WebSocket for streaming node updates

Usage:
    python api_server.py
    → API:  http://localhost:8000
    → Docs: http://localhost:8000/docs
"""

import os
import json
import time
import asyncio
import subprocess
from typing import Optional

import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── CONFIG ──────────────────────────────────────────────────────────────────
CHROMA_DIR   = "./chroma_db"
OLLAMA_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
PHOENIX_URL  = "http://localhost:6006"

app = FastAPI(
    title="SentinelRAG API",
    description="Production-grade RAG observability pipeline — Gurugram University B.Tech Project",
    version="1.0.0",
    docs_url="/docs",
)

# Allow the frontend (running on any port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
#  REQUEST / RESPONSE MODELS
# ──────────────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question:        str
    answer:          str
    grade:           str
    route:           str
    ttft:            float
    input_tokens:    int
    output_tokens:   int
    simulated_cost:  float
    node_log:        list
    elapsed_total:   float


# ──────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def check_ollama() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def check_chromadb() -> bool:
    return os.path.exists(CHROMA_DIR) and os.path.isdir(CHROMA_DIR)


def check_phoenix() -> bool:
    try:
        r = requests.get(PHOENIX_URL, timeout=2)
        return r.status_code in (200, 302)
    except Exception:
        return False


def get_rag_graph():
    """Import and build the LangGraph pipeline (lazy import for fast startup)."""
    from rag_system import build_graph, setup_observability
    try:
        setup_observability()
    except Exception:
        pass  # Phoenix might not be running — that's OK
    return build_graph()


# ──────────────────────────────────────────────────────────────────────────────
#  ROUTES
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/status", summary="System health check")
def status():
    """Returns the health status of all system components."""
    ollama_ok  = check_ollama()
    chroma_ok  = check_chromadb()
    phoenix_ok = check_phoenix()

    # If Ollama is up, try to get the list of models
    models = []
    if ollama_ok:
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
            data = r.json()
            models = [m["name"] for m in data.get("models", [])]
        except Exception:
            pass

    return {
        "status":      "ok" if (ollama_ok and chroma_ok) else "degraded",
        "ollama":      {"ok": ollama_ok, "models": models},
        "chromadb":    {"ok": chroma_ok, "path": CHROMA_DIR},
        "phoenix":     {"ok": phoenix_ok, "url": PHOENIX_URL},
        "timestamp":   time.time(),
    }


@app.post("/query", response_model=QueryResponse, summary="Run a RAG query")
def query(req: QueryRequest):
    """
    Runs the full SentinelRAG pipeline for a given question.
    Returns the answer, routing decision, and all performance metrics.
    """
    if not req.question or not req.question.strip():
        return JSONResponse(status_code=400, content={"error": "Question cannot be empty."})

    if not check_ollama():
        return JSONResponse(status_code=503, content={"error": "Ollama is not running. Start it with: ollama serve"})

    if not check_chromadb():
        return JSONResponse(status_code=503, content={"error": "ChromaDB not found. Run: python ingest.py"})

    t_start = time.time()

    try:
        graph = get_rag_graph()

        initial_state = {
            "question":       req.question.strip(),
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

        result = graph.invoke(initial_state)

        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            grade=result.get("grade", ""),
            route=result.get("route", "generate"),
            ttft=result.get("ttft", 0.0),
            input_tokens=result.get("input_tokens", 0),
            output_tokens=result.get("output_tokens", 0),
            simulated_cost=result.get("simulated_cost", 0.0),
            node_log=result.get("node_log", []),
            elapsed_total=round(time.time() - t_start, 3),
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Pipeline error: {str(e)}"},
        )


@app.post("/ingest", summary="Re-ingest documents into ChromaDB")
def ingest():
    """Triggers the ingest.py script to re-embed all documents."""
    try:
        result = subprocess.run(
            ["python", "ingest.py"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "success":   result.returncode == 0,
            "stdout":    result.stdout,
            "stderr":    result.stderr,
        }
    except subprocess.TimeoutExpired:
        return JSONResponse(status_code=504, content={"error": "Ingestion timed out after 5 minutes."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/eval", summary="Run RAGAS faithfulness evaluation")
def eval_endpoint():
    """Runs eval_gate.py and returns the faithfulness score and pass/fail status."""
    if not check_ollama():
        return JSONResponse(status_code=503, content={"error": "Ollama is not running."})
    if not check_chromadb():
        return JSONResponse(status_code=503, content={"error": "ChromaDB not found. Run /ingest first."})

    try:
        from eval_gate import run_eval
        result = run_eval()
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ──────────────────────────────────────────────────────────────────────────────
#  WEBSOCKET — real-time streaming
# ──────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/query")
async def ws_query(websocket: WebSocket):
    """
    WebSocket endpoint for streaming RAG pipeline updates node-by-node.
    Client sends: {"question": "..."}
    Server sends: sequence of step events, then the final result.
    """
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        question = payload.get("question", "").strip()

        if not question:
            await websocket.send_json({"type": "error", "message": "Empty question"})
            return

        # Send pipeline start event
        await websocket.send_json({"type": "start", "question": question})

        if not check_ollama():
            await websocket.send_json({"type": "error", "message": "Ollama not running"})
            return

        if not check_chromadb():
            await websocket.send_json({"type": "error", "message": "ChromaDB not found — run /ingest"})
            return

        # Run pipeline in thread pool (it's synchronous)
        loop = asyncio.get_event_loop()

        def run_pipeline():
            graph = get_rag_graph()
            state = {
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
            return graph.invoke(state)

        result = await loop.run_in_executor(None, run_pipeline)

        # Stream back node logs
        for log in result.get("node_log", []):
            await websocket.send_json({"type": "node", "data": log})
            await asyncio.sleep(0.05)  # small delay for visual effect in UI

        # Send final result
        await websocket.send_json({
            "type":           "result",
            "answer":         result["answer"],
            "grade":          result.get("grade", ""),
            "route":          result.get("route", "generate"),
            "ttft":           result.get("ttft", 0.0),
            "input_tokens":   result.get("input_tokens", 0),
            "output_tokens":  result.get("output_tokens", 0),
            "simulated_cost": result.get("simulated_cost", 0.0),
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  SentinelRAG — API Server")
    print("  Gurugram University B.Tech Project")
    print("  Authors: Akshu Grewal · Ishantnu · Anish Singh Rawat")
    print("=" * 60)
    print(f"  API:  http://localhost:8000")
    print(f"  Docs: http://localhost:8000/docs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
