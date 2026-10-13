import json

import pytest

import main
from opik import Attachment

URGENCIES = {"emergency", "same-day", "routine"}


def test_voicemail_data_loads():
    vms = json.loads((main.HERE / "data" / "voicemails.json").read_text())
    assert len(vms) == 4
    assert len({v["id"] for v in vms}) == 4
    for v in vms:
        assert v["voice"] and v["script"]


def test_triage_parses_and_validates_shape(stub):
    out = main.triage("Hi, this is Ann about Rex.")
    assert out["urgency"] in URGENCIES
    assert set(out["callback"]) == {"owner_name", "pet", "callback_number", "reason"}
    kind, kw = stub.calls[-1]
    assert kind == "chat"
    assert kw["model"] == main.TRIAGE_MODEL
    assert kw["response_format"] == {"type": "json_object"}
    assert kw["messages"][0]["content"] == main.TRIAGE_PROMPT


def test_triage_rejects_non_json_reply(stub):
    stub.reply = "not json"
    with pytest.raises(json.JSONDecodeError):
        main.triage("anything")


def test_prompt_lists_every_urgency_level():
    for level in URGENCIES:
        assert level in main.TRIAGE_PROMPT


def test_traced_pipeline_builds_mp3_attachment(stub, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "AUDIO_DIR", tmp_path)
    captured = {}
    monkeypatch.setattr(
        main.opik_context, "update_current_trace", lambda **kw: captured.update(kw)
    )
    vm = {"id": "vm-test", "voice": "nova", "script": "Hello there."}

    # triage_voicemail is @opik.track-decorated; with tracking disabled it just runs
    res = main.triage_voicemail(vm)

    mp3 = tmp_path / "vm-test.mp3"
    assert mp3.read_bytes() == b"ID3fake-mp3"
    (att,) = captured["attachments"]
    assert isinstance(att, Attachment)
    assert att.data == str(mp3)
    assert att.content_type == "audio/mpeg"
    assert captured["metadata"] == {"voicemail_id": "vm-test"}
    assert res["id"] == "vm-test" and res["urgency"] == "routine"
    assert [c[0] for c in stub.calls] == ["tts", "stt", "chat"]
    assert stub.calls[0][1]["voice"] == "nova"
    assert stub.calls[1][1]["model"] == main.STT_MODEL
