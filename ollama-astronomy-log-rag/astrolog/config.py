import os
from pathlib import Path

PROJECT_NAME = "ollama-astronomy-log-rag"
# Default project for every trace the SDK and OpikTracer send (no per-call project needed).
os.environ.setdefault("OPIK_PROJECT_NAME", PROJECT_NAME)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = "llama3.2:1b"
EMBED_MODEL = "nomic-embed-text"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
TOP_K = 2
