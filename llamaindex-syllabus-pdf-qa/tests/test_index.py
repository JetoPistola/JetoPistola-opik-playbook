import shutil

from llama_index.core import Settings
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.llms import MockLLM

from syllabus_qa import index
from syllabus_qa.config import SYLLABI_DIR


def _use_mock_models():
    Settings.llm = MockLLM()
    Settings.embed_model = MockEmbedding(embed_dim=8)


def test_pdfs_load_as_text_not_raw_bytes(tmp_path, monkeypatch):
    # Copy to tmp_path so a hidden parent directory can't make the reader skip the files.
    shutil.copytree(SYLLABI_DIR, tmp_path / "syllabi")
    monkeypatch.setattr(index, "SYLLABI_DIR", tmp_path / "syllabi")
    monkeypatch.setattr(index, "configure_llama_index", _use_mock_models)

    idx = index.build_index()
    texts = [n.get_content() for n in idx.docstore.docs.values()]
    assert len(texts) == 3
    assert not any("%PDF" in t for t in texts)  # raw PDF bytes mean the PDF reader is missing
    assert any("laboratory reports 30%" in t for t in texts)


def test_query_engine_uses_top_k(tmp_path, monkeypatch):
    shutil.copytree(SYLLABI_DIR, tmp_path / "syllabi")
    monkeypatch.setattr(index, "SYLLABI_DIR", tmp_path / "syllabi")
    monkeypatch.setattr(index, "configure_llama_index", _use_mock_models)
    assert index.build_query_engine()._retriever._similarity_top_k == index.TOP_K
