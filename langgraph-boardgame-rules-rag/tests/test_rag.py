"""Offline tests: fake embeddings and a fake chat model, Opik tracking disabled."""

import os

os.environ["OPIK_TRACK_DISABLE"] = "true"


def test_chunks_are_one_per_section_with_game_prefix(app_module):
    chunks = app_module.load_chunks()
    assert len(chunks) >= 4
    assert all(c.startswith("[") and "\n## " in c for c in chunks)
    games = {c.split("]")[0].lstrip("[") for c in chunks}
    assert any(g.startswith("Lantern Harbor") for g in games)
    assert any(g.startswith("Obsidian Crown") for g in games)


def test_search_rulebooks_is_tracked_and_respects_k(app_module):
    # Calling the @opik.track-ed function with tracking disabled behaves like a plain function.
    assert len(app_module.search_rulebooks("lantern cost", k=2)) == 2
    assert len(app_module.search_rulebooks("lantern cost")) == app_module.TOP_K == 3


def test_graph_returns_context_and_answer(app_module):
    result = app_module.app.invoke({"question": "How many coins to light a lantern?"})
    assert result["answer"] == "stub"
    assert len(result["context"]) == 3


def test_dataset_items_are_well_formed(app_module):
    items = app_module.DATASET_ITEMS
    assert len(items) == 6
    assert all(i["question"] and i["expected_output"] for i in items)


def test_rag_task_returns_output_and_context(app_module):
    out = app_module.rag_task(app_module.DATASET_ITEMS[0])
    assert out["output"] == "stub"
    assert isinstance(out["context"], list) and out["context"]
