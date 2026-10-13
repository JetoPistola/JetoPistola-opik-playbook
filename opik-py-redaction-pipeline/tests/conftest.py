import os
import sys
from pathlib import Path

# main.py builds OpenAI() and opik.Opik() at import time. A dummy key lets the import
# succeed with no real credentials; tracking is switched off so nothing is sent.
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-real")
os.environ["OPIK_TRACK_DISABLE"] = "true"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
