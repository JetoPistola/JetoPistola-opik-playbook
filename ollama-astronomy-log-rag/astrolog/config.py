import os
from pathlib import Path

PROJECT_NAME = "ollama-astronomy-log-rag"

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = "llama3.2:1b"
EMBED_MODEL = "nomic-embed-text"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
TOP_K = 2
