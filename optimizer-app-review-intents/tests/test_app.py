import json
import pathlib
from collections import Counter

import pytest

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "reviews.jsonl"
LABELS = {"bug_report", "feature_request", "billing_complaint", "praise", "usability_confusion"}


def test_dataset_has_28_labeled_reviews():
    rows = [json.loads(line) for line in DATA.read_text().splitlines() if line]
    assert len(rows) == 28
    assert all(set(r) == {"review", "label"} for r in rows)
    assert {r["label"] for r in rows} == LABELS
    # every intent has more than a couple of examples
    assert min(Counter(r["label"] for r in rows).values()) >= 3


def test_dataset_is_uploaded_whole(app):
    assert len(app.module.REVIEWS) == 28
    app.client.get_or_create_dataset.assert_called_once()
    inserted = app.client.get_or_create_dataset.return_value.insert.call_args.args[0]
    assert inserted == app.module.REVIEWS
    assert set(app.module.LABELS) == LABELS


@pytest.mark.parametrize("reply", ["bug_report", "Bug_Report", " bug_report.\n", '"bug_report"', "`bug_report`", "**bug_report**"])
def test_metric_forgives_case_quotes_and_punctuation(app, reply):
    score = app.module.intent_match({"label": "bug_report"}, reply)
    assert score.name == "intent_match"
    assert score.value == 1.0
    assert score.reason == "exact label"


def test_metric_rejects_prose_and_explains_why(app):
    reply = "This looks like a bug_report because the app crashes."
    score = app.module.intent_match({"label": "bug_report"}, reply)
    assert score.value == 0.0
    assert score.reason == f"expected exactly 'bug_report' and nothing else; got {reply!r}"


def test_metric_reason_truncates_long_replies(app):
    score = app.module.intent_match({"label": "praise"}, "x" * 500)
    assert score.value == 0.0
    assert "x" * 120 in score.reason and "x" * 121 not in score.reason


def test_metric_rejects_wrong_label(app):
    assert app.module.intent_match({"label": "praise"}, "bug_report").value == 0.0


def test_baseline_names_every_label_and_asks_for_brevity(app):
    system = app.module.BASELINE_SYSTEM
    for label in LABELS:
        assert label in system
    assert "Keep it brief." in system
    # the baseline is a prose prompt: it never says "label only", which is what the optimizer has to add
    assert "only" not in system.lower()


def test_prompt_and_optimizer_are_wired(app):
    prompt = app.module.prompt
    assert prompt.name == "review-intent-classifier"
    assert prompt.model == "openai/gpt-4o-mini"
    assert [m["role"] for m in prompt.get_messages()] == ["system", "user"]
    opt = app.optimizer.last
    assert opt.init_kwargs == {"model": "openai/gpt-4o-mini", "prompts_per_round": 3, "seed": 7, "verbose": 1}
    assert opt.call_kwargs["max_trials"] == 6
    assert opt.call_kwargs["n_samples"] == 28
    assert opt.call_kwargs["metric"] is app.module.intent_match
    assert opt.call_kwargs["project_name"] == "optimizer-app-review-intents"


def test_link_is_pinned_to_project_not_get_run_link(app):
    expected = "http://localhost:5173/default/projects/proj-456/optimizations/opt-123"
    assert f"run link          : {expected}" in app.stdout
    app.client.rest_client.optimizations.get_optimization_by_id.assert_called_with("opt-123")


def test_winner_saved_with_mustache_placeholder(app):
    calls = app.client.create_chat_prompt.call_args_list
    assert len(calls) == 2  # v1 baseline, then the winner
    baseline, winner = calls[0].kwargs, calls[1].kwargs
    assert baseline["name"] == winner["name"] == "review-intent-classifier"
    assert baseline["messages"][0]["content"] == app.module.BASELINE_SYSTEM
    assert baseline["messages"][1]["content"] == "{{review}}"
    assert winner["messages"][1]["content"] == "{{review}}"
    assert winner["change_description"] == "MetaPromptOptimizer winner: 0.750 -> 1.000 on app-review-intents"
    assert "baseline accuracy : 0.750" in app.stdout
    assert "best accuracy     : 1.000  (+0.250)" in app.stdout
