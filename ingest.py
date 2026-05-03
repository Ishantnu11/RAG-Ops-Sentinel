"""
ingest.py — Step 1: Chunk documents and embed them into ChromaDB.
Run this ONCE (with all other processes stopped) before running
api_server.py or rag_system.py.

SentinelRAG | Gurugram University B.Tech Project
Authors: Akshu Grewal · Ishantnu · Anish Singh Rawat

Usage:
    python ingest.py
"""

import os
import sys
import stat
import time
import shutil
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# ─── CONFIG ────────────────────────────────────────────────────────────────────
DOCS_DIR      = "./docs"
CHROMA_DIR    = "./chroma_db"
EMBED_MODEL   = "llama3.2"
CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 200


# ─── HELPERS ───────────────────────────────────────────────────────────────────

def _on_rm_error(func, path, exc_info):
    """Error handler for shutil.rmtree on Windows locked files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass  # best-effort; re-creation will fail below if still locked


def clear_chroma_dir():
    """
    Delete the existing ChromaDB directory.
    On Windows, files may be locked by api_server.py or rag_system.py.
    This function retries up to 3 times and exits with a clear message
    if still locked so the user knows exactly what to do.
    """
    if not os.path.exists(CHROMA_DIR):
        return  # nothing to clear

    for attempt in range(1, 4):
        try:
            shutil.rmtree(CHROMA_DIR, onerror=_on_rm_error)
            if not os.path.exists(CHROMA_DIR):
                print(f"[ingest] Cleared old ChromaDB at '{CHROMA_DIR}'")
                return
        except Exception as e:
            print(f"[ingest] WARNING: Delete attempt {attempt}/3 failed: {e}")
            time.sleep(1)

    # All attempts failed — directory is still locked
    print("\n" + "=" * 60)
    print("  ERROR: Cannot delete locked ChromaDB directory.")
    print("  Another process (api_server.py, rag_system.py) is using it.")
    print()
    print("  ► STOP ALL OTHER TERMINALS first, then run this again:")
    print("      Ctrl+C  in all terminal windows")
    print("      then:  .\\venv\\Scripts\\python ingest.py")
    print("=" * 60 + "\n")
    sys.exit(1)


# ─── PIPELINE ──────────────────────────────────────────────────────────────────

def load_documents():
    """Load all PDF and TXT files from the docs directory."""
    supported_files = []
    for root, _, files in os.walk(DOCS_DIR):
        for f in files:
            ext = f.lower().split('.')[-1]
            if ext in ["pdf", "txt"]:
                supported_files.append(os.path.join(root, f))

    if not supported_files:
        print(f"[ingest] No supported files found in '{DOCS_DIR}'")
        print(f"          Place your PDF or TXT documents in the docs/ folder and re-run.")
        sys.exit(1)

    print(f"[ingest] Found {len(supported_files)} file(s):")
    for p in supported_files:
        print(f"          • {p}")

    # Load PDFs
    from langchain_community.document_loaders import TextLoader
    
    docs = []
    for file_path in supported_files:
        if file_path.lower().endswith(".pdf"):
            loader = PyPDFLoader(file_path)
            docs.extend(loader.load())
        elif file_path.lower().endswith(".txt"):
            loader = TextLoader(file_path, encoding="utf-8")
            docs.extend(loader.load())

    print(f"[ingest] Loaded {len(docs)} page/document(s) from '{DOCS_DIR}'")
    return docs


def split_documents(docs):
    """Split documents into overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(docs)
    print(
        f"[ingest] Split into {len(chunks)} chunk(s) "
        f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})"
    )
    return chunks


def embed_and_store(chunks):
    """Embed chunks using Ollama and persist to ChromaDB."""
    print(f"[ingest] Embedding with Ollama model: {EMBED_MODEL}")
    print("[ingest] This may take a few minutes depending on document size...")

    embeddings = OllamaEmbeddings(model=EMBED_MODEL)

    # Wipe existing DB to avoid duplicates on re-run
    clear_chroma_dir()

    start = time.time()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
    )
    elapsed = time.time() - start

    print(
        f"\n[ingest] DONE: Stored {len(chunks)} chunks in ChromaDB "
        f"at '{CHROMA_DIR}' ({elapsed:.1f}s)"
    )
    return vectorstore


# ─── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  SentinelRAG — Document Ingestion Pipeline")
    print("  Gurugram University B.Tech Project")
    print("=" * 60)

    docs   = load_documents()
    chunks = split_documents(docs)
    embed_and_store(chunks)

    print("\n[ingest] Ingestion complete!")
    print("[ingest]    Now start the system:")
    print("           1. python launch_phoenix.py")
    print("           2. .\\venv\\Scripts\\python api_server.py")
    print("           3. .\\venv\\Scripts\\python rag_system.py   (or use the UI)")
