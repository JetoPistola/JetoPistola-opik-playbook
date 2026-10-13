import asyncio
import json

from tools import check_calibration_schedule, find_service_contact, lookup_instrument_log


def call(tool, **kwargs) -> str:
    """Run a BeeAI tool the way the agent does and return its text output."""
    async def go():
        return await tool.run(kwargs)

    return asyncio.run(go()).get_text_content()


def test_lookup_instrument_log_is_case_insensitive():
    out = json.loads(call(lookup_instrument_log, instrument_id=" sp-07 "))
    assert out["id"] == "SP-07"


def test_lookup_instrument_log_unknown_lists_known_ids():
    out = call(lookup_instrument_log, instrument_id="ZZ-99")
    assert "No instrument 'ZZ-99'" in out and "FZ-80-B" in out


def test_calibration_schedule_adds_today_and_flags_overdue():
    out = json.loads(call(check_calibration_schedule, instrument_id="sp-07"))
    assert out["next_due"] == "2026-10-12"
    assert out["today"] == "2026-10-13"


def test_calibration_schedule_unknown():
    assert "No calibration record" in call(check_calibration_schedule, instrument_id="ZZ-99")


def test_find_service_contact():
    out = json.loads(call(find_service_contact, instrument_type=" Centrifuge "))
    assert out["name"] == "Halden Service Desk"
    assert "No contact" in call(find_service_contact, instrument_type="microscope")
