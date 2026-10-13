"""Document redaction, traced by hand with the low-level Opik client.

No @opik.track, no track_openai: every trace, span and usage block below is an
explicit SDK call. Read top to bottom.
"""

import json
import os
import re
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
    spans.append(dict(name="regex-detector", type="guardrail", start_time=t0, end_time=now(),
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
        start_time=t_llm, end_time=t_llm_end,
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
                      start_time=t0, end_time=now(),
                      input={"file": path.name}, output={"findings": llm_hits}))

    # Stage 3: redactor -> tool span
    t0 = now()
    redacted = redact(text, regex_hits + llm_hits)
    # tool span: its output is the redacted text, so leaks are readable in context.
    spans.append(dict(name="redactor", type="tool", start_time=t0, end_time=now(),
                      input={"n_regex": len(regex_hits), "n_llm": len(llm_hits)},
                      output={"redacted_text": redacted}))

    # Stage 4: verifier -> guardrail span. It only re-runs the regexes, so it can
    # confirm the stage-1 shapes are gone but cannot see anything the detectors missed.
    t0 = now()
    residual = regex_detect(redacted)
    # guardrail span: passes whenever the regexes find nothing, even if names leaked.
    spans.append(dict(name="verifier", type="guardrail", start_time=t0, end_time=now(),
                      input={"redacted_text": redacted},
                      output={"passed": not residual, "residual": residual}))

    # One trace per document, created with the id the spans point at (trace_id);
    # it appears as a row in the project's Traces tab.
    trace = client.trace(
        id=trace_id, name="redact-document", project_name=PROJECT, tags=["redaction"],
        start_time=t_trace, end_time=now(),
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
    for path in sorted(DATA.glob("*.txt")):
        process(path, truth[path.name])
    # The SDK sends in a background thread; flush() blocks until every queued
    # trace and span is delivered. Without it a short script can exit and lose some.
    client.flush()
    print(f"done -> project '{PROJECT}'")


if __name__ == "__main__":
    main()
