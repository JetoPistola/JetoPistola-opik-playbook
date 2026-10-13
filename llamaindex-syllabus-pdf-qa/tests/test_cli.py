import pytest

from syllabus_qa import cli


def _run(monkeypatch, argv):
    calls = []
    monkeypatch.setattr(cli, "_cmd_build", lambda: calls.append("build"))
    monkeypatch.setattr(cli, "_cmd_ask", lambda q: calls.append(("ask", q)))
    monkeypatch.setattr(cli, "_cmd_demo", lambda: calls.append("demo"))
    monkeypatch.setattr(cli, "_cmd_suite", lambda: calls.append("suite"))
    monkeypatch.setattr("sys.argv", ["syllabus-qa", *argv])
    cli.main()
    return calls


def test_subcommands_dispatch(monkeypatch):
    assert _run(monkeypatch, ["build"]) == ["build"]
    assert _run(monkeypatch, ["ask", "When?"]) == [("ask", "When?")]
    assert _run(monkeypatch, ["suite"]) == ["suite"]


def test_default_runs_build_demo_and_suite(monkeypatch):
    assert _run(monkeypatch, []) == ["build", "demo", "suite"]


def test_ask_requires_a_question(monkeypatch):
    with pytest.raises(SystemExit):
        _run(monkeypatch, ["ask"])
