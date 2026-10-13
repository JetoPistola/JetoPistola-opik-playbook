"""Shared settings: project name, paths, env loading, and model setup, and the Opik handler."""

import os
import pathlib

PROJECT_NAME = "llamaindex-syllabus-pdf-qa"
# Opik reads this at import time: all traces land in this project instead of "Default Project".
os.environ.setdefault("OPIK_PROJECT_NAME", PROJECT_NAME)

import dotenv

ROOT = pathlib.Path(__file__).resolve().parents[1]
SYLLABI_DIR = ROOT / "data" / "syllabi"

# Walk up to find the nearest .env (repo root or this folder).
for parent in [ROOT, *ROOT.parents]:
    if (parent / ".env").exists():
        dotenv.load_dotenv(parent / ".env")
        break

LLM_MODEL = "gpt-4o-mini"
EMBED_MODEL = "text-embedding-3-small"
TOP_K = 3

_configured = False


def configure_llama_index() -> None:
    """Install the Opik callback handler and default models (idempotent)."""
    global _configured
    if _configured:
        return
    from llama_index.core import Settings, set_global_handler
    from llama_index.embeddings.openai import OpenAIEmbedding
    from llama_index.llms.openai import OpenAI

    # The whole Opik integration: every query becomes a trace, with a retrieve span
    # (embedding + fetched chunks) and a synthesize span (chunking, templating, llm with usage and cost).
    # Index builds show up as index_construction traces.
    set_global_handler("opik")
    Settings.llm = OpenAI(model=LLM_MODEL, temperature=0.0)
    Settings.embed_model = OpenAIEmbedding(model=EMBED_MODEL)
    _configured = True
