# optimizer-app-review-intents

*A prompt that sorts app-store reviews goes from 0.75 to 1.00 accuracy, and Opik keeps the whole score curve.*

![Python](https://img.shields.io/badge/python-3.12+-blue?style=flat)
![opik-optimizer](https://img.shields.io/badge/opik--optimizer-3.2.0-orange?style=flat)

## The problem

Verdant is a made-up habit tracker, and its app-store page gets reviews like "Wow, such a delightful experience watching my streak vanish." That one is sarcasm, and it is really a bug report. Another review says "Great app, shame about the crash every time I open the stats tab", which is praise and a bug in one sentence. A first-draft prompt copes with the easy reviews and stumbles on the tricky ones, and it also answers in whatever shape it likes. You can nudge the wording by hand, or you can let an optimizer propose rewrites and keep only the ones that score higher on labeled data.

## What you'll build

One script (`main.py`) that:

1. Loads 28 fictional, labeled reviews from `data/reviews.jsonl` into an Opik dataset called `app-review-intents`. Five intents: `bug_report`, `feature_request`, `billing_complaint`, `praise`, `usability_confusion`. Several reviews are sarcastic or mixed.
2. Saves a hand-written baseline prompt as version 1 of `review-intent-classifier` in the Opik prompt library.
3. Runs `MetaPromptOptimizer` (gpt-4o-mini for both classifying and reasoning, 3 candidates per round, budget of 6 trials) against an exact-match metric. The metric passes a `reason` string such as "expected exactly 'bug_report' and nothing else; got ..." that the optimizer reads when it reasons about failures.
4. If the best prompt beats the baseline, saves it as version 2 in the library.
5. Prints a link to the run that is pinned to the right project.

## See it in Opik

Open the `optimizer-app-review-intents` project and go to **Optimization runs**. You will find one completed run on the dataset `app-review-intents`, objective `intent_match`. In the verified run the optimizer evaluated 4 prompts on all 28 reviews:

| prompt | accuracy |
|---|---|
| baseline | 0.750 |
| candidate | 0.929 |
| candidate | 0.179 |
| candidate (winner) | 1.000 |

Click into the run to see the score curve go from 0.75 to a dip at 0.179 and up to 1.00. The dip is worth opening: that candidate asked for a rationale again and buried the label in prose, so almost nothing matched exactly. Opik records 4 trials for the run (the baseline plus 3 candidates, within the budget of 6); the optimizer stopped once a candidate scored perfectly. The tracked spend covers the classification calls; the optimizer's own reasoning calls are not included in that figure. The project also holds 113 traces: 112 `evaluation_task` traces (4 prompts x 28 reviews) plus one `optimization_algorithm` trace. Together they cost about $0.002 in tracked LLM spend.

Then open **Prompt library** and find `review-intent-classifier`. It has two versions: your baseline, and the winner, whose text ends with "Your answer should only include the intent label without any extra commentary."

Your numbers will differ somewhat from these. gpt-4o-mini is not deterministic, and the optimizer follows whatever failures it happens to see.

## Run it yourself

1. Make sure Opik is reachable (`opik configure`, or set `OPIK_URL_OVERRIDE` and `OPIK_WORKSPACE`).
2. `cp .env.example .env` and add `OPENAI_API_KEY` (a `.env` in any parent folder also works).
3. `uv sync`
4. `uv run main.py`. It took about 30 seconds for the run above and costs a few cents at most.
5. Open the "run link" the script prints; it points straight at the run inside this project.
6. Optional, offline: `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest` checks the dataset, the metric's `reason` text, the baseline prompt and the pinned link with a fake Opik client and optimizer. No key, no network, a few seconds.

## Poke around

- Edit `BASELINE_SYSTEM` to drop "Keep it brief." and re-run. The baseline will likely score near zero because replies turn into sentences. See how far the optimizer gets from there.
- Add 10 more sarcastic or mixed-intent reviews to `data/reviews.jsonl` and check whether the winner still hits 1.00.
- Set `MAX_TRIALS = 2` and see whether the best prompt survives the smaller budget.
- Change the metric to accept the first label found anywhere in the reply. The baseline jumps to 1.00 on this dataset, so there is nothing left to optimize. That shows the metric defines the problem.

## Gotchas we hit

**The run link opens an empty page.** `result.get_run_link()` builds a `/v1/session/redirect/optimizations/...` URL with no project in it, so the UI opens the run inside whichever project you last had open, and from any other project it looks empty. `main.py` prints a pinned link instead, built from the optimization's own `project_id`:

```python
info = client.rest_client.optimizations.get_optimization_by_id(result.optimization_id)
print(f"{ui}/{client.config.workspace}/projects/{info.project_id}/optimizations/{result.optimization_id}")
```

## How it's put together

- `main.py`: dataset upload, the metric, the baseline prompt, the optimizer run, the library save, and the pinned link.
- `data/reviews.jsonl`: 28 labeled fictional reviews.
- `pyproject.toml`: pins `opik-optimizer==3.2.0`.
- `.env.example`: the one provider key needed.
- `tests/conftest.py`: imports `main.py` with a fake Opik client and optimizer, so tests need no key or server.
- `tests/test_app.py`: dataset, metric, baseline prompt, optimizer settings, winner save and pinned-link checks.

---

*built with Opik · inspired by Opik's examples and documentation*
