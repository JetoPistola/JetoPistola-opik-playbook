import sys

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage


class _FakeEmbeddings(DeterministicFakeEmbedding):
    def __init__(self, **_):
        super().__init__(size=32)


@pytest.fixture(scope="session")
def app_module():
    """Import main with the OpenAI classes replaced, so no key or network is needed."""
    import langchain_openai

    saved = (langchain_openai.OpenAIEmbeddings, langchain_openai.ChatOpenAI)
    langchain_openai.OpenAIEmbeddings = _FakeEmbeddings
    langchain_openai.ChatOpenAI = lambda **_: GenericFakeChatModel(
        messages=iter([AIMessage(content="stub")] * 100)
    )
    sys.modules.pop("main", None)
    import main

    yield main
    langchain_openai.OpenAIEmbeddings, langchain_openai.ChatOpenAI = saved
