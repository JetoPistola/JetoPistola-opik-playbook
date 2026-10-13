import pytest

from podcast_planner import cli, crew
from podcast_planner.agents import MODEL, build_agents
from podcast_planner.tasks import build_tasks


@pytest.fixture(autouse=True)
def _dummy_key(monkeypatch):
    # Agent construction wants a key present; the value is never used because no model is called.
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-a-real-key")


def test_cli_defaults():
    args = cli.build_parser().parse_args([])
    assert args.brief == cli.DEFAULT_BRIEF
    assert args.notes is None


def test_cli_brief_and_notes(tmp_path):
    notes = tmp_path / "n.md"
    args = cli.build_parser().parse_args(["A short episode", "--notes", str(notes)])
    assert args.brief == "A short episode"
    assert args.notes == notes


def test_agents_roles_and_model():
    agents = build_agents()
    assert [a.role for a in agents] == ["Topic Researcher", "Outline Writer", "Show-Notes Editor"]
    assert MODEL == "gpt-4o-mini"


def test_tasks_wiring():
    researcher, outliner, editor = build_agents()
    research, outline, notes = build_tasks(researcher, outliner, editor)
    assert [t.agent for t in (research, outline, notes)] == [researcher, outliner, editor]
    assert not isinstance(research.context, list)  # the first task has no upstream context
    assert outline.context == [research]
    assert notes.context == [research, outline]
    assert "{brief}" in research.description and "{notes}" in research.description


def test_default_notes_file_loads():
    text = crew.DEFAULT_NOTES.read_text()
    assert "Brannock Point" in text


def test_build_crew_with_tracking_disabled():
    # build_crew calls track_crewai; with OPIK_TRACK_DISABLE=true it must not get in the way.
    c = crew.build_crew()
    assert len(c.agents) == 3 and len(c.tasks) == 3


def test_plan_episode_passes_notes_to_kickoff(tmp_path, monkeypatch):
    notes = tmp_path / "custom.md"
    notes.write_text("custom notes body")
    seen = {}

    class FakeCrew:
        def kickoff(self, inputs):
            seen.update(inputs)
            return "done"

    monkeypatch.setattr(crew, "build_crew", lambda: FakeCrew())
    assert crew.plan_episode("my brief", notes) == "done"
    assert seen == {"brief": "my brief", "notes": "custom notes body"}
