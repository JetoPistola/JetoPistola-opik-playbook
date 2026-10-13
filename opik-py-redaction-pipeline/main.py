"""Document redaction, traced by hand with the low-level Opik client.

No @opik.track, no track_openai: every trace, span, usage block and feedback
score below is an explicit SDK call. Read top to bottom.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import opik
from opik.id_helpers import generate_id
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

load_dotenv(find_dotenv(usecwd=False))  # walks up to the repo-root .env

PROJECT = os.getenv("OPIK_PROJECT_NAME", "opik-py-redaction-pipeline")
MODEL = "gpt-4o-mini"
DATA = Path(__file__).parent / "data"
# Demo switches for the flush/end lessons (see the README "Poke around" section).
SKIP_FLUSH = "--no-flush" in sys.argv  # experiment: lose the batch on purpose
SKIP_END = "--no-end" in sys.argv      # experiment: never close the spans

# The regex stage only knows these shapes. That is deliberate: it is cheap and
# precise, and the LLM stage is supposed to cover what it cannot.
PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(r"\b555-\d{4}\b"),
    "gov_id": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}

SYSTEM_PROMPT = (
    "You find personal information in a document. List every exact substring that is a "
    "person's full name, a street address, a date of birth, or a health condition or "
    "medication detail. Copy each substring exactly as written. Do not list emails or "
    "555-xxxx phone numbers (another tool handles them), and do not list organisations. "
    'Reply as JSON: {"findings": [{"text": "...", "kind": "name|address|dob|health"}]}'
)

# Low-level client: nothing is traced unless we call client.trace(...) / trace.span(...)
# ourselves. project_name decides which Opik project the traces land in.
client = opik.Opik(project_name=PROJECT)
openai_client = OpenAI()


def now() -> datetime:
    return datetime.now(timezone.utc)


def closed(t: datetime) -> datetime | None:
    """The end_time to send. With --no-end it is None, so the span stays 'open'.

    Opik: a span or trace sent without end_time arrives with no duration.
    """
    return None if SKIP_END else t


def regex_detect(text: str) -> list[dict]:
    return [
        {"text": m.group(0), "kind": kind}
        for kind, pat in PATTERNS.items()
        for m in pat.finditer(text)
    ]


def redact(text: str, findings: list[dict]) -> str:
    for f in sorted(findings, key=lambda f: -len(f["text"])):  # longest first
        text = text.replace(f["text"], f"[{f['kind'].upper()}]")
    return text


def process(path: Path, truth: list[str]) -> tuple[str, float, list[str]]:
    # Batching lesson: every span below is created ONCE, complete (input, output, usage,
    # start/end time), after its work is done. Create-then-update/end within milliseconds
    # makes the SDK warn about possible data loss. IDs are generated up front so the
    # parent/child links are explicit.
    text = path.read_text()
    t_trace = now()
    trace_id, contextual_id = generate_id(), generate_id()
    spans: list[dict] = []

    # Stage 1: regex detector -> guardrail span
    t0 = now()
    regex_hits = regex_detect(text)
    # guardrail span: shows up as a "guardrail" step under the trace, with the findings as output.
    spans.append(dict(name="regex-detector", type="guardrail", start_time=t0, end_time=closed(now()),
                      input={"text": text}, output={"findings": regex_hits},
                      metadata={"patterns": list(PATTERNS)}))

    # Stage 2: contextual detector -> general span (contextual_id) with one llm child
    t0 = now()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    t_llm = now()
    resp = openai_client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0,
        response_format={"type": "json_object"},
    )
    t_llm_end = now()
    llm_hits = json.loads(resp.choices[0].message.content).get("findings", [])
    # llm span, parented to contextual-detector via the pre-generated id; it is created
    # after the call returns so it is sent once, complete (no create-then-update).
    spans.append(dict(
        name=f"chat {MODEL}", type="llm", parent_span_id=contextual_id,
        start_time=t_llm, end_time=closed(t_llm_end),
        input={"messages": messages}, output={"findings": llm_hits},
        # Hand-recorded usage: model + provider + token counts is what lets Opik
        # compute total_estimated_cost on the server.
        model=resp.model, provider="openai",
        usage={
            "prompt_tokens": resp.usage.prompt_tokens,
            "completion_tokens": resp.usage.completion_tokens,
            "total_tokens": resp.usage.total_tokens,
        },
    ))
    # general span that owns the llm child: id=contextual_id is what makes the nesting explicit.
    spans.append(dict(name="contextual-detector", type="general", id=contextual_id,
                      start_time=t0, end_time=closed(now()),
                      input={"file": path.name}, output={"findings": llm_hits}))

    # Stage 3: redactor -> tool span
    t0 = now()
    redacted = redact(text, regex_hits + llm_hits)
    # tool span: its output is the redacted text, so leaks are readable in context.
    spans.append(dict(name="redactor", type="tool", start_time=t0, end_time=closed(now()),
                      input={"n_regex": len(regex_hits), "n_llm": len(llm_hits)},
                      output={"redacted_text": redacted}))

    # Stage 4: verifier -> guardrail span. It only re-runs the regexes, so it can
    # confirm the stage-1 shapes are gone but cannot see anything the detectors missed.
    t0 = now()
    residual = regex_detect(redacted)
    # guardrail span: passes whenever the regexes find nothing, even if names leaked.
    spans.append(dict(name="verifier", type="guardrail", start_time=t0, end_time=closed(now()),
                      input={"redacted_text": redacted},
                      output={"passed": not residual, "residual": residual}))

    # One trace per document, created with the id the spans point at (trace_id);
    # it appears as a row in the project's Traces tab.
    trace = client.trace(
        id=trace_id, name="redact-document", project_name=PROJECT, tags=["redaction"],
        start_time=t_trace, end_time=closed(now()),
        input={"file": path.name, "chars": len(text)},
        output={"redacted_text": redacted, "verifier_passed": not residual},
    )
    for sp in spans:
        trace.span(**sp)  # each call sends one complete span under this trace

    leaked = [t for t in truth if t in redacted]
    recall = (len(truth) - len(leaked)) / len(truth) if truth else 1.0
    print(f"{path.name:24} detected={len(regex_hits) + len(llm_hits):2}  "
          f"verifier={'pass' if not residual else 'FAIL'}  recall={recall:.2f}  leaked={leaked}")
    return trace_id, recall, leaked


def main() -> None:
    truth = json.loads((DATA / "ground_truth.json").read_text())
    scores = []
    for path in sorted(DATA.glob("*.txt")):
        trace_id, recall, leaked = process(path, truth[path.name])
        # Feedback score payloads for the trace we just sent: the values come from
        # data/ground_truth.json, which the pipeline itself never sees.
        scores += [
            {"id": trace_id, "name": "redaction_recall", "value": recall,
             "reason": f"leaked: {leaked}" if leaked else "every ground-truth item was removed"},
            {"id": trace_id, "name": "leaked_pii_count", "value": float(len(leaked)),
             "reason": ", ".join(leaked) or "none"},
        ]
    if SKIP_FLUSH:
        print("--no-flush: exiting without client.flush()")
        # os._exit skips atexit hooks too: with no flush, the traces still queued in the
        # background sender are lost (3 of 4 arrived in my run) and no scores are sent.
        os._exit(0)
    # Flush first: a score can only attach to a trace Opik already has.
    client.flush()
    # Feedback scores show up as columns in the Traces tab (one row per trace).
    client.log_traces_feedback_scores(scores, project_name=PROJECT)
    client.flush()  # ship the score batch too
    opik.flush_tracker()
    print(f"done -> project '{PROJECT}'")


if __name__ == "__main__":
    main()
