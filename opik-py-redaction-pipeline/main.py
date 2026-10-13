"""Document redaction pipeline: regex detector, LLM detector, redactor, verifier."""

import json
import re
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

load_dotenv(find_dotenv(usecwd=False))  # walks up to the repo-root .env

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

openai_client = OpenAI()


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


def process(path: Path, truth: list[str]) -> tuple[float, list[str]]:
    text = path.read_text()

    # Stage 1: regex detector
    regex_hits = regex_detect(text)

    # Stage 2: contextual detector (LLM)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    resp = openai_client.chat.completions.create(
        model=MODEL, messages=messages, temperature=0,
        response_format={"type": "json_object"},
    )
    llm_hits = json.loads(resp.choices[0].message.content).get("findings", [])

    # Stage 3: redactor
    redacted = redact(text, regex_hits + llm_hits)

    # Stage 4: verifier. It only re-runs the regexes, so it can confirm the
    # stage-1 shapes are gone but cannot see anything the detectors missed.
    residual = regex_detect(redacted)

    leaked = [t for t in truth if t in redacted]
    recall = (len(truth) - len(leaked)) / len(truth) if truth else 1.0
    print(f"{path.name:24} detected={len(regex_hits) + len(llm_hits):2}  "
          f"verifier={'pass' if not residual else 'FAIL'}  recall={recall:.2f}  leaked={leaked}")
    return recall, leaked


def main() -> None:
    truth = json.loads((DATA / "ground_truth.json").read_text())
    for path in sorted(DATA.glob("*.txt")):
        process(path, truth[path.name])


if __name__ == "__main__":
    main()
