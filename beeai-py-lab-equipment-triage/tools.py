"""Three read-only tools over the fictional lab's local JSON files."""
import json
from pathlib import Path

from beeai_framework.tools import tool

DATA = Path(__file__).parent / "data"
TODAY = "2026-10-13"


def _load(name: str):
    return json.loads((DATA / name).read_text())


@tool
def lookup_instrument_log(instrument_id: str) -> str:
    """Return the instrument's model, location, owner, and maintenance log. instrument_id looks like CF-02, AC-01, FZ-80-B, SP-07."""
    for item in _load("instruments.json"):
        if item["id"].lower() == instrument_id.strip().lower():
            return json.dumps(item)
    known = [i["id"] for i in _load("instruments.json")]
    return f"No instrument '{instrument_id}'. Known ids: {known}"


@tool
def check_calibration_schedule(instrument_id: str) -> str:
    """Return the calibration interval, last and next due dates for an instrument id. Today is 2026-10-13."""
    entry = _load("calibration.json").get(instrument_id.strip().upper())
    return json.dumps({**entry, "today": TODAY}) if entry else f"No calibration record for '{instrument_id}'."


@tool
def find_service_contact(instrument_type: str) -> str:
    """Return who to contact for an instrument type: centrifuge, autoclave, ultra-low freezer, or spectrophotometer."""
    entry = _load("contacts.json").get(instrument_type.strip().lower())
    return json.dumps(entry) if entry else f"No contact for type '{instrument_type}'."
