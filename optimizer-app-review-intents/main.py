"""Tune a review-intent prompt for Verdant, a fictional habit tracker, with Opik's optimizer."""

import json
import os
import pathlib

HERE = pathlib.Path(__file__).parent
PROJECT_NAME = "optimizer-app-review-intents"
os.environ["OPIK_PROJECT_NAME"] = PROJECT_NAME

import dotenv

# Walk up from this folder until a .env is found (repo root or here).
for folder in [HERE, *HERE.parents]:
    if (folder / ".env").exists():
        dotenv.load_dotenv(folder / ".env")
        break

import opik
from opik.evaluation.metrics.score_result import ScoreResult
from opik_optimizer import ChatPrompt, MetaPromptOptimizer

MODEL = "openai/gpt-4o-mini"
DATASET_NAME = "app-review-intents"
LIBRARY_PROMPT_NAME = "review-intent-classifier"
MAX_TRIALS = 6
LABELS = ["bug_report", "feature_request", "billing_complaint", "praise", "usability_confusion"]

REVIEWS = [json.loads(line) for line in (HERE / "data/reviews.jsonl").read_text().splitlines() if line]

# One client for dataset, prompt library and the pinned link; the project comes from OPIK_PROJECT_NAME set above.
client = opik.Opik()
dataset = client.get_or_create_dataset(
    name=DATASET_NAME, description=f"{len(REVIEWS)} fictional Verdant app-store reviews with intent labels"
)
# Dataset items show up under Datasets; the optimizer scores every prompt on all of them.
dataset.insert(REVIEWS)


def intent_match(dataset_item: dict, llm_output: str) -> ScoreResult:
    """1.0 only if the reply is exactly the label (case, quotes, trailing dots forgiven).

    The `reason` is what the optimizer reads when it reasons about failures.
    The metric name `intent_match` becomes the run's objective in Optimization runs.
    """
    answer = llm_output.strip().lower().strip(".!\"'` *")
    ok = answer == dataset_item["label"]
    reason = "exact label" if ok else (
        f"expected exactly '{dataset_item['label']}' and nothing else; got {llm_output.strip()[:120]!r}"
    )
    return ScoreResult(name="intent_match", value=1.0 if ok else 0.0, reason=reason)


BASELINE_SYSTEM = (
    "You read app-store reviews for Verdant, a habit tracker. Work out what the "
    "reviewer is trying to say and tell us which of these intents fits: "
    "bug_report, feature_request, billing_complaint, praise, usability_confusion. Keep it brief."
)

prompt = ChatPrompt(name="review-intent-classifier", system=BASELINE_SYSTEM, user="{review}", model=MODEL)

# Prompt library: v1 of review-intent-classifier = the hand-written baseline.
# v1 in the library = the hand-written baseline.
client.create_chat_prompt(
    name=LIBRARY_PROMPT_NAME,
    messages=[
        {"role": "system", "content": BASELINE_SYSTEM},
        {"role": "user", "content": "{{review}}"},
    ],
    change_description="Hand-written baseline (before optimization)",
    project_name=PROJECT_NAME,
)

# The optimizer creates the optimization run (Optimization runs tab) and logs one
# evaluation_task trace per prompt x review into the project.
optimizer = MetaPromptOptimizer(model=MODEL, prompts_per_round=3, seed=7, verbose=1)
result = optimizer.optimize_prompt(
    prompt=prompt,
    dataset=dataset,
    metric=intent_match,
    n_samples=len(REVIEWS),
    max_trials=MAX_TRIALS,
    project_name=PROJECT_NAME,
)

initial = result.initial_score or 0.0
best = result.score
print("\n" + "=" * 60)
print(f"baseline accuracy : {initial:.3f}")
print(f"best accuracy     : {best:.3f}  ({best - initial:+.3f})")
print(f"trials completed  : {result.details.get('trials_completed')} (budget {MAX_TRIALS})")
print(f"llm cost (optim.) : {result.llm_cost_total}")

# result.get_run_link() lands in whichever project the UI last showed; print a pinned link.
info = client.rest_client.optimizations.get_optimization_by_id(result.optimization_id)
ui = client.config.url_override.rstrip("/").removesuffix("/api")
print(f"run link          : {ui}/{client.config.workspace}/projects/{info.project_id}/optimizations/{result.optimization_id}")
print("=" * 60)

# Only a real improvement is saved: it becomes version 2 in the Prompt library.
if best > initial:
    messages = result.prompt.get_messages()
    for m in messages:
        m["content"] = m["content"].replace("{review}", "{{review}}")
    client.create_chat_prompt(
        name=LIBRARY_PROMPT_NAME,
        messages=messages,
        change_description=f"MetaPromptOptimizer winner: {initial:.3f} -> {best:.3f} on {DATASET_NAME}",
        project_name=PROJECT_NAME,
    )
    print(f"Saved winner as new version of '{LIBRARY_PROMPT_NAME}'.\n\n{messages[0]['content']}")
else:
    print("No improvement; library keeps only v1.")

# Flush so queued traces and the prompt version are sent before the script exits.
opik.flush_tracker()
