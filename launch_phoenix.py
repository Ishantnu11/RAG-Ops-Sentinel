"""
launch_phoenix.py — Start Arize Phoenix observability dashboard.
Run this BEFORE api_server.py in a separate terminal.

SentinelRAG | Gurugram University B.Tech Project
Authors: Akshu Grewal · Ishantnu · Anish Singh Rawat

Usage:
    python launch_phoenix.py

Dashboard: http://localhost:6006
"""

import time


def main():
    print("=" * 60)
    print("  SentinelRAG — Arize Phoenix Dashboard")
    print("  Gurugram University B.Tech Project")
    print("=" * 60)
    print("[phoenix] Starting Phoenix server...")
    print("[phoenix] Dashboard -> http://localhost:6006")
    print("[phoenix] OTLP traces -> http://localhost:6006/v1/traces")
    print("[phoenix] Press Ctrl+C to stop.\n")

    try:
        import phoenix as px
        session = px.launch_app()
        print(f"[phoenix] [OK] Phoenix running at: {session.url}")
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n[phoenix] Shutting down.")
    except ImportError:
        print("[phoenix] [ERROR] arize-phoenix not installed. Run: pip install arize-phoenix==4.29.0")
    except AttributeError:
        # Newer phoenix versions use serve() instead of launch_app()
        try:
            import phoenix as px
            px.serve()
        except Exception as e:
            print(f"[phoenix] [ERROR] Error starting Phoenix: {e}")
            print("[phoenix] Try: pip install arize-phoenix --upgrade")


if __name__ == "__main__":
    main()
