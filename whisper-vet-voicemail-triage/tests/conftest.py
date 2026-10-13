"""Offline setup: no provider key, no Opik, no .env, stubbed OpenAI client."""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

# Importing main builds OpenAI() at module level, which needs some key; a dummy is enough.
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["OPIK_TRACK_DISABLE"] = "true"  # @track and track_openai become pass-throughs
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dotenv  # noqa: E402

dotenv.load_dotenv = lambda *a, **k: False  # never read a real .env during tests

import main  # noqa: E402


class StubClient:
    """Stands in for the OpenAI client: TTS, transcription and chat."""

    def __init__(self, transcript="Hi, this is Ann about Rex. Call 555-0100.", reply=None):
        self.reply = reply if reply is not None else (
            '{"urgency": "routine", "reason_for_urgency": "Booking.",'
            ' "callback": {"owner_name": "Ann", "pet": "Rex", "callback_number": "555-0100",'
            ' "reason": "booking"}}'
        )
        self.calls = []
        speech = SimpleNamespace(create=self._speech)
        transcriptions = SimpleNamespace(create=self._transcribe)
        self.audio = SimpleNamespace(speech=speech, transcriptions=transcriptions)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))
        self._transcript = transcript

    def _speech(self, **kw):
        self.calls.append(("tts", kw))
        return SimpleNamespace(content=b"ID3fake-mp3")

    def _transcribe(self, **kw):
        self.calls.append(("stt", kw))
        return self._transcript

    def _chat(self, **kw):
        self.calls.append(("chat", kw))
        msg = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


@pytest.fixture
def stub(monkeypatch):
    s = StubClient()
    monkeypatch.setattr(main, "client", s)
    return s
