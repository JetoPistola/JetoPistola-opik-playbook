"""Offline tests: litellm.completion is monkeypatched, so no keys and no Opik are needed."""

import json
from types import SimpleNamespace

import pytest

import main


def fake_response(text="One. Two three. Four five six.", tokens=100, cost=0.001):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(total_tokens=tokens),
        _hidden_params={"response_cost": cost},
    )


@pytest.fixture
def calls(monkeypatch):
    seen = []

    def fake_completion(**kwargs):
        seen.append(kwargs)
        return fake_response()

    monkeypatch.setattr(main.litellm, "completion", fake_completion)
    return seen


def test_passages_load():
    passages = json.loads((main.HERE / "data" / "passages.json").read_text())
    assert len(passages) == 3
    assert all({"id", "title", "text"} <= p.keys() for p in passages)


def test_words_per_sentence():
    assert main.words_per_sentence("One two. Three four five six.") == pytest.approx(3.0)
    assert main.words_per_sentence("") == 0


def test_rewrite_builds_prompt_and_tags(calls):
    passage = {"id": "p1", "title": "A title", "text": "Some body text."}
    row = main.rewrite("openai/gpt-4o-mini", passage, "age-8")
    sent = calls[0]
    prompt = sent["messages"][0]["content"]
    assert main.LEVELS["age-8"] in prompt
    assert "Title: A title\nSome body text." in prompt
    # the tags are what Opik shows on the trace: model, level, passage id
    assert sent["metadata"]["opik"]["tags"] == ["gpt-4o-mini", "age-8", "p1"]
    assert row["model"] == "gpt-4o-mini" and row["tokens"] == 100 and row["cost"] == 0.001


def test_missing_cost_becomes_zero(monkeypatch):
    resp = fake_response()
    resp._hidden_params = {}
    monkeypatch.setattr(main.litellm, "completion", lambda **kw: resp)
    row = main.rewrite("anthropic/x", {"id": "p", "title": "t", "text": "x"}, "adult")
    assert row["cost"] == 0.0


def test_main_summary_table(calls, capsys):
    # The OpikLogger callback is registered at import, yet main() runs fine offline: the stubbed
    # completion never triggers it, and OPIK_TRACK_DISABLE keeps the SDK quiet.
    main.main()
    out = capsys.readouterr().out
    assert len(calls) == 18  # 2 models x 3 passages x 3 levels
    assert "gpt-4o-mini" in out and "claude-haiku-4-5-20251001" in out
    # 9 calls per model, 900 tokens, 9 x $0.001
    row = next(line for line in out.splitlines() if line.startswith("gpt-4o-mini  "))
    assert row.replace("$", "").split()[:4] == ["gpt-4o-mini", "9", "900", "0.009000"]
    assert "Mean words per sentence by level" in out
