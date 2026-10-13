from llama_index.core import Document, Settings, VectorStoreIndex, set_global_handler
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.llms import MockLLM

from syllabus_qa import corpus
from syllabus_qa.qa import SYSTEM_HINT, ask


def _engine():
    Settings.llm = MockLLM()
    Settings.embed_model = MockEmbedding(embed_dim=8)
    docs = [
        Document(text=" ".join(p for _, paras in spec["sections"] for p in paras))
        for spec in corpus.COURSES.values()
    ]
    return VectorStoreIndex.from_documents(docs).as_query_engine(similarity_top_k=2)


def test_ask_returns_answer_and_retrieved_excerpts():
    answer = ask(_engine(), "What is the BIO 101 late penalty?")
    assert answer.question.startswith("What is the BIO 101")
    assert answer.text  # MockLLM echoes the prompt
    assert len(answer.excerpts) == 2


def test_prompt_carries_the_system_hint():
    assert SYSTEM_HINT in ask(_engine(), "Anything?").text


def test_ask_with_the_opik_handler_installed_and_tracking_disabled():
    # The global Opik handler is active but OPIK_TRACK_DISABLE=true, so the query runs untouched.
    set_global_handler("opik")
    assert ask(_engine(), "Office hours?").excerpts
