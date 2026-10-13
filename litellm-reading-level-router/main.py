"""Rewrite the same passages at three reading levels on two providers.

Every call goes through LiteLLM; Opik's OpikLogger callback records each one
as a trace in the "litellm-reading-level-router" project. The script then
prints a per-model table (tokens, cost, latency) built from the same
responses, so you can check it against Opik's own numbers.
"""

import json
import logging
import os
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
for parent in HERE.parents:  # find the repo-root .env, if any
    if (parent / ".env").exists():
        load_dotenv(parent / ".env")
        break
load_dotenv(HERE / ".env", override=True)

PROJECT = "litellm-reading-level-router"
# Opik reads the project name from this env var; it must be set before opik / OpikLogger load,
# or traces land in "Default Project".
os.environ["OPIK_PROJECT_NAME"] = PROJECT
os.environ.pop("ANTHROPIC_BASE_URL", None)  # always talk to the real API

import litellm
import opik
from litellm.integrations.opik.opik import OpikLogger

logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
# OpikLogger callback: every litellm.completion call becomes one trace with one llm span
# (model, token usage, estimated cost); no decorator or client wrapper needed.
# It prints a harmless "periodic_flush was never awaited" RuntimeWarning in a plain script.
litellm.callbacks = [OpikLogger()]

MODELS = ["openai/gpt-4o-mini", "anthropic/claude-haiku-4-5-20251001"]

LEVELS = {
    "age-8": "a curious 8-year-old: short sentences, everyday words, one friendly comparison",
    "age-12": "a 12-year-old: clear and engaging, define any technical term once",
    "adult": "an educated adult reader: precise, concise, with the right terminology",
}


def words_per_sentence(text: str) -> float:
    sentences = [s for s in re.split(r"[.!?]+\s", text.strip()) if s]
    return len(text.split()) / max(len(sentences), 1)


def rewrite(model: str, passage: dict, level: str) -> dict:
    prompt = (
        f"Rewrite the passage below for {LEVELS[level]}. Keep every fact, "
        f"use at most 80 words, and reply with the rewrite only.\n\n"
        f"Title: {passage['title']}\n{passage['text']}"
    )
    start = time.perf_counter()
    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        # metadata["opik"]["tags"] become the trace tags in Opik, so the Traces table can be
        # filtered by model, reading level or passage.
        metadata={"opik": {"tags": [model.split("/")[-1], level, passage["id"]]}},
    )
    latency = time.perf_counter() - start
    text = response.choices[0].message.content
    return {
        "model": model.split("/")[-1],
        "level": level,
        "latency": latency,
        "cost": response._hidden_params.get("response_cost") or 0.0,
        "tokens": response.usage.total_tokens,
        "wps": words_per_sentence(text),
        "preview": text[:70].replace("\n", " "),
    }


def main() -> None:
    passages = json.loads((HERE / "data" / "passages.json").read_text())
    rows: list[dict] = []
    for model in MODELS:
        print(f"\n=== {model} ===")
        for passage in passages:
            for level in LEVELS:
                r = rewrite(model, passage, level)
                rows.append(r)
                print(f"  {passage['id']:<15} {level:<7} [{r['latency']:5.2f}s ${r['cost']:.6f} "
                      f"{r['tokens']:4d} tok] {r['preview']}...")

    print(f"\n{'Model':<26}{'Calls':>6}{'Tokens':>8}{'Total cost':>12}{'Mean latency':>14}")
    print("-" * 66)
    by_model = defaultdict(list)
    for r in rows:
        by_model[r["model"]].append(r)
    for model, rs in by_model.items():
        print(f"{model:<26}{len(rs):>6}{sum(r['tokens'] for r in rs):>8}"
              f"  ${sum(r['cost'] for r in rs):>9.6f}{statistics.mean(r['latency'] for r in rs):>13.2f}s")

    print("\nMean words per sentence by level (lower = simpler):")
    for level in LEVELS:
        cells = "  ".join(
            f"{m}: {statistics.mean(r['wps'] for r in rs if r['level'] == level):.1f}"
            for m, rs in by_model.items()
        )
        print(f"  {level:<7} {cells}")

    # The OpikLogger sends in batches; flush so the last traces are not lost when the script exits.
    opik.flush_tracker()


if __name__ == "__main__":
    main()
