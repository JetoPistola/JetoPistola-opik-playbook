import json
from types import SimpleNamespace

import main

TRUTH = json.loads((main.DATA / "ground_truth.json").read_text())


def fake_openai(findings):
    """Stub for openai_client.chat.completions.create returning canned findings."""
    def create(**kwargs):
        return SimpleNamespace(
            model="gpt-4o-mini-test",
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"findings": findings})))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


class FakeSpyClient:
    """Records what would be sent to Opik, so the manual-trace path is checked offline."""
    def __init__(self):
        self.traces, self.spans = [], []

    def trace(self, **kw):
        self.traces.append(kw)
        return SimpleNamespace(span=lambda **s: self.spans.append(s))


def test_regex_detector_finds_known_shapes():
    hits = main.regex_detect("mail a.b@x.example, call 555-0142, id 482-55-1907")
    assert {(h["kind"], h["text"]) for h in hits} == {
        ("email", "a.b@x.example"), ("phone", "555-0142"), ("gov_id", "482-55-1907")}


def test_regex_detector_misses_spoken_phone():
    assert main.regex_detect("five five five, oh one four two") == []


def test_redactor_longest_first():
    findings = [{"text": "Ann", "kind": "name"}, {"text": "Ann Lee", "kind": "name"}]
    assert main.redact("Ann Lee met Ann", findings) == "[NAME] met [NAME]"


def test_verifier_blind_spot_passes_leaked_name():
    redacted = main.redact("Ellis Thackeray, 555-0198", main.regex_detect("Ellis Thackeray, 555-0198"))
    assert "Ellis Thackeray" in redacted          # leaked
    assert main.regex_detect(redacted) == []      # yet the regex-only verifier passes


def test_recall_and_leak_scoring_against_ground_truth(monkeypatch):
    monkeypatch.setattr(main, "openai_client", fake_openai([]))
    path = main.DATA / "rental_inquiry.txt"
    recall, leaked = main.process(path, TRUTH[path.name])[1:]
    assert 0 < recall < 1
    assert "Ellis Thackeray" in leaked          # LLM stub found nothing
    assert len(leaked) == round((1 - recall) * len(TRUTH[path.name]))


def test_clean_document_scores_perfect(monkeypatch):
    monkeypatch.setattr(main, "openai_client", fake_openai([]))
    path = main.DATA / "incident_email.txt"
    assert main.process(path, TRUTH[path.name])[1:] == (1.0, [])


def test_manual_trace_path_runs_with_tracking_disabled(monkeypatch):
    # The low-level client has no decorator to disable: OPIK_TRACK_DISABLE only
    # affects @track / integrations, so we spy on client.trace to see what is built.
    spy = FakeSpyClient()
    monkeypatch.setattr(main, "client", spy)
    monkeypatch.setattr(main, "openai_client", fake_openai([{"text": "Ellis Thackeray", "kind": "name"}]))
    path = main.DATA / "rental_inquiry.txt"
    trace_id, recall, leaked = main.process(path, TRUTH[path.name])
    assert spy.traces[0]["id"] == trace_id
    kinds = {s["name"]: s["type"] for s in spy.spans}
    assert kinds == {"regex-detector": "guardrail", "chat gpt-4o-mini": "llm",
                     "contextual-detector": "general", "redactor": "tool", "verifier": "guardrail"}
    llm = next(s for s in spy.spans if s["type"] == "llm")
    contextual = next(s for s in spy.spans if s["name"] == "contextual-detector")
    assert llm["parent_span_id"] == contextual["id"]
    assert llm["usage"]["total_tokens"] == 15 and llm["provider"] == "openai"
    assert "Ellis Thackeray" not in leaked
