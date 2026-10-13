# whisper-vet-voicemail-triage

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)
![Opik 2.2.99](https://img.shields.io/badge/opik-2.2.99-2f54eb)

*Four voicemails to a fictional animal clinic, sorted into emergency / same-day / routine, with the audio one click away from every trace.*

At 11pm nobody is at the front desk of Maple Hollow Animal Clinic (invented). Callers leave voicemails, and a pipeline decides who gets a phone call now and who waits for morning. If it files a bloat case as "routine", nothing crashes. The voicemail is just wrong, and by the time someone notices, the only evidence is a recording nobody kept. This example keeps the recording. It attaches each caller's MP3 to its trace and checks the triage decisions with a small test suite.

## What you'll build

For each of four scripted voicemails in `data/voicemails.json`, one pipeline run: text-to-speech turns the script into an MP3 (so you need no real recordings), Whisper transcribes it back, and `gpt-4o-mini` returns an urgency level plus a callback-list entry (owner, pet, number, reason). Then `evaluate.py` re-runs the triage step inside an Opik test suite, where an LLM judge checks three assertions. Each item runs three times and has to pass two, so a single odd judge verdict does not fail the suite.

## See it in Opik

Open the `whisper-vet-voicemail-triage` project. The Traces tab has 16 traces after both scripts have run. The four named `triage-voicemail` are the pipeline runs (the other twelve, `evaluation_task`, come from the suite).

Open one `triage-voicemail` trace. Its span tree is `speak-voicemail` (a tool span, with an `audio.speech.create` LLM span inside), `transcribe-voicemail` (tool span), and `triage-transcript` containing `chat_completion_create`. In my run each `chat_completion_create` span logged about 320-340 tokens and a cost near $0.00009. The TTS span also carries a cost (about $0.00014-$0.00018). The transcription span carries no cost, so Whisper spend does not show up in the trace total. Whole-trace cost was about $0.00023-$0.00027.

The attachments panel of each trace holds that voicemail's MP3 (for example `vm-01-bloat.mp3`, `audio/mpeg`). Press play and compare it with the transcript in the `transcribe-voicemail` span. The Great Dane call is triaged `emergency` and the cat's limp `same-day`. The beagle's vaccine and flea-tablet request is `routine`, and the chocolate puppy is `emergency`. Whisper rendered the spoken digits "five five five, zero one four two" as `555-0142`, and the callback entries kept the numbers intact.

Then open Datasets and find `vet-voicemail-triage-suite` (4 items), then its experiment. In my run the suite passed 4/4 items (pass rate 100%, 12 runs in total). The per-assertion view is more interesting: "urgency is justified" and "callback fields match the transcript" passed 12/12, but "nothing is invented" passed only 11/12, because one judge run disagreed. With a single run that would have been a red build over a judge wobble. With `runs_per_item=3, pass_threshold=2` it was absorbed.

Cost for the whole thing, from Opik's `total_estimated_cost`: about $0.001 across the four pipeline traces, plus the suite's own triage calls and judge calls (not priced here). Wall time of the evaluation was about 14 seconds of work.

## Run it yourself

1. `cd whisper-vet-voicemail-triage && cp .env.example .env` and add `OPENAI_API_KEY` (a repo-root `.env` also works).
2. Point the SDK at Opik: `opik configure`, or for a local instance `export OPIK_URL_OVERRIDE=http://localhost:5173/api/`.
3. `uv sync`
4. `uv run main.py` generates `audio/*.mp3`, transcribes, triages, and writes `out/triage.json`.
5. `uv run evaluate.py` creates the suite and runs it.
6. Open the project in Opik and play an attachment.
7. Offline tests, no keys and no Opik needed: `env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY OPIK_TRACK_DISABLE=true uv run pytest` (`OPIK_TRACK_DISABLE=true` is the SDK's switch that turns tracking into a no-op).

The audio and `out/` are regenerated on every run and git-ignored. Everything is fictional: the clinic, the callers, the pets, and the phone numbers.

## Poke around

- Change `voice` for one voicemail in `data/voicemails.json` (try `echo` or `coral`) and see whether the transcript or triage changes.
- Rewrite a script to be ambiguous ("he ate something off the floor and seems quiet") and check which urgency the model picks. Then see whether the suite notices.
- Set `runs_per_item` to 1 in `evaluate.py` and run the suite several times to see how often a single judge run flips.
- Delete the "never invent details" sentence from `TRIAGE_PROMPT` in `main.py` and watch the third assertion.

## Gotchas we hit

- **Whisper spend is invisible in Opik: the `transcribe-voicemail` span has no cost and the trace total leaves it out.** `track_openai` patches `chat.completions` and `audio.speech` only (checked in `opik/integrations/openai/opik_tracker.py` for opik 2.2.99), so `audio.transcriptions.create` never becomes an llm span. The only span around it is the `@opik.track(type="tool")` one, which carries no usage. Fix: if you need the number, compute it yourself from the audio duration (whisper-1 is billed per minute) and put it in the span's metadata, for example `opik_context.update_current_span(metadata={"est_cost_usd": minutes * 0.006})`.
- **TTS shows up as an llm span with a token-based cost, not as a tool or audio span.** The `audio.speech.create` span nested inside `speak-voicemail` is typed `llm` and priced from tokens, so its cost line looks like a chat call's. Treat it as an estimate and cross-check it against your OpenAI bill.
- **`httpx.UnsupportedProtocol: Request URL is missing an 'http://' or 'https://' protocol` when `OPIK_URL_OVERRIDE` is exported but empty.** An empty value is treated as a URL rather than as unset, and every request the SDK makes fails. Fix: `unset OPIK_URL_OVERRIDE`, or export the real value, `http://localhost:5173/api/`.

## How it's put together

- `main.py` - the pipeline: TTS, transcription, triage, with the MP3 attached to each trace (`track_openai` plus `@opik.track`).
- `evaluate.py` - the Opik test suite: three judge assertions and the execution policy.
- `data/voicemails.json` - four fictional voicemail scripts and the TTS voice for each.
- `tests/conftest.py` - offline setup: dummy key, tracking disabled, and a stub OpenAI client (TTS, transcription, chat).
- `tests/test_voicemail.py` - voicemail data loading, triage parsing and validation, the MP3 attachment (path and `audio/mpeg`), and the traced pipeline called with tracking disabled.
- `pyproject.toml`, `.env.example`, `.gitignore` - dependencies (opik 2.2.99), key template, ignored output.

---

*built with Opik · inspired by Opik's examples and documentation*
