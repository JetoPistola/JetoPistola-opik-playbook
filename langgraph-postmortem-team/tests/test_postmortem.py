import main

ALL = ["alert-timeline.md", "chat-transcript.md", "deploy-history.md", "logs.md"]


def test_evidence_loaded_from_data_dir():
    assert sorted(main.EVIDENCE) == ALL
    assert all(text.strip() for text in main.EVIDENCE.values())


def test_lead_drops_unknown_files_and_caps_the_list(fake_llm):
    fake_llm("logs.md", "nope.md", *ALL, "logs.md")
    out = main.lead({"incident": "INC"})
    sources = [t["source"] for t in out["tasks"]]
    assert "nope.md" not in sources
    assert len(sources) == main.MAX_INVESTIGATIONS
    assert out["findings"] == []


def test_max_investigations_cap_with_lower_value(fake_llm, monkeypatch):
    monkeypatch.setattr(main, "MAX_INVESTIGATIONS", 2)
    fake_llm(*ALL)
    assert len(main.lead({"incident": "INC"})["tasks"]) == 2


def test_route_loops_until_every_task_has_a_finding():
    tasks = [{"source": "logs.md", "focus": "f"}] * 2
    one = [{"source": "logs.md", "focus": "f", "notes": "n"}]
    assert main.route({"tasks": tasks, "findings": one}) == "investigator"
    assert main.route({"tasks": tasks, "findings": one * 2}) == "writer"


def test_investigator_appends_a_finding_for_the_next_task(fake_llm):
    fake_llm()
    state = {
        "tasks": [{"source": "logs.md", "focus": "a"}, {"source": "deploy-history.md", "focus": "b"}],
        "findings": [{"source": "logs.md", "focus": "a", "notes": "x"}],
    }
    out = main.investigator(state)
    assert [f["source"] for f in out["findings"]] == ["logs.md", "deploy-history.md"]


def test_full_graph_run_with_tracking_disabled(fake_llm):
    fake = fake_llm("logs.md", "alert-timeline.md", "deploy-history.md")
    # main.app is the track_langgraph-wrapped graph; it runs fine untracked.
    result = main.app.invoke({"incident": "INC-2291"})
    assert len(result["tasks"]) == 3
    assert len(result["findings"]) == 3
    # 3 investigator passes + 1 writer call
    assert len(fake.calls) == 4
    assert result["postmortem"] == "notes-4"
