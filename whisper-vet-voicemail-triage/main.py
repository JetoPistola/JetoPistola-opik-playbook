"""After-hours vet voicemail triage, traced with Opik.

One trace per voicemail in the "whisper-vet-voicemail-triage" project:

    triage-voicemail          <- whole pipeline, MP3 attached
    |- speak-voicemail        <- TTS (generates the fictional caller audio)
    |- transcribe-voicemail   <- speech-to-text
    '- triage-transcript      <- gpt-4o-mini -> urgency + callback entry
       '- chat_completion_create  (track_openai: tokens + cost)
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
AUDIO_DIR, OUT_DIR = HERE / "audio", HERE / "out"
PROJECT = "whisper-vet-voicemail-triage"

load_dotenv(HERE.parent / ".env")
# Project name must be set before the SDK is imported so every trace lands in this project
os.environ["OPIK_PROJECT_NAME"] = PROJECT
os.environ.pop("OPENAI_BASE_URL", None)

import opik
from openai import OpenAI
from opik import Attachment, opik_context
from opik.integrations.openai import track_openai

TTS_MODEL = "gpt-4o-mini-tts"
STT_MODEL = "whisper-1"
TRIAGE_MODEL = "gpt-4o-mini"

TRIAGE_PROMPT = """\
You are the after-hours triage assistant for Maple Hollow Animal Clinic.
You read a voicemail transcript and reply with JSON only, exactly:

{
  "urgency": "emergency" | "same-day" | "routine",
  "reason_for_urgency": "one sentence",
  "callback": {"owner_name": "...", "pet": "name and species/breed if said",
               "callback_number": "digits as spoken, or null", "reason": "short"}
}

Urgency rules:
- emergency: possible poisoning/toxin ingestion, bloat signs, breathing
  trouble, seizures, heavy bleeding, trauma. Someone must call back now.
- same-day: pain or injury that is not life-threatening; call back next morning.
- routine: bookings, refills, questions.
Copy names and numbers exactly as in the transcript; never invent details.
"""

# track_openai wraps the client: chat calls become llm spans with tokens and cost;
# TTS shows up as an llm span with a token-based cost, whisper-1 transcription gets no cost
client = track_openai(OpenAI())


# type="tool" shows this step as a tool span; the TTS llm span nests inside it
@opik.track(name="speak-voicemail", type="tool")
def speak(vm: dict, path: Path) -> dict:
    audio = client.audio.speech.create(
        model=TTS_MODEL, voice=vm["voice"], input=vm["script"], response_format="mp3"
    ).content
    path.write_bytes(audio)
    return {"voice": vm["voice"], "size_bytes": len(audio), "chars": len(vm["script"])}


# tool span holding the transcript as output (the transcription call itself has no cost in Opik)
@opik.track(name="transcribe-voicemail", type="tool")
def transcribe(path: Path) -> str:
    with path.open("rb") as f:
        return client.audio.transcriptions.create(
            model=STT_MODEL, file=f, response_format="text"
        )


# general span that parents the chat_completion_create llm span
@opik.track(name="triage-transcript")
def triage(transcript: str) -> dict:
    r = client.chat.completions.create(
        model=TRIAGE_MODEL,
        messages=[
            {"role": "system", "content": TRIAGE_PROMPT},
            {"role": "user", "content": transcript},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(r.choices[0].message.content)


# root span: one trace per voicemail
@opik.track(name="triage-voicemail")
def triage_voicemail(vm: dict) -> dict:
    path = AUDIO_DIR / f"{vm['id']}.mp3"
    speak(vm, path)  # always regenerated: audio is output, not committed
    transcript = transcribe(path)
    result = triage(transcript)
    # Attachment uploads the MP3 to the trace: it appears as a playable file in the trace's attachments panel
    opik_context.update_current_trace(
        attachments=[Attachment(data=str(path), content_type="audio/mpeg")],
        metadata={"voicemail_id": vm["id"]},
    )
    return {"id": vm["id"], "transcript": transcript, **result}


if __name__ == "__main__":
    AUDIO_DIR.mkdir(exist_ok=True)
    OUT_DIR.mkdir(exist_ok=True)
    results = []
    for vm in json.loads((HERE / "data" / "voicemails.json").read_text()):
        res = triage_voicemail(vm)
        results.append(res)
        c = res["callback"]
        print(f"\n[{res['urgency'].upper()}] {vm['id']}")
        print(f"  heard:    {res['transcript'].strip()}")
        print(f"  callback: {c['owner_name']} / {c['pet']} / {c['callback_number']} / {c['reason']}")
    (OUT_DIR / "triage.json").write_text(json.dumps(results, indent=2))
    # flush so queued traces and attachment uploads are sent before the process exits
    opik.flush_tracker()
    print(f"\nDone. Open the {PROJECT} project in Opik.")
