"""Retrieval wrapped in a named tool span.

Retrieval is a plain function decorated with @opik.track(type="tool"), so it
always appears as its own named tool span, whatever the tracer does with
LangChain retriever runs.
"""
import opik
from langchain_core.vectorstores import InMemoryVectorStore

from .config import TOP_K


def make_retriever(store: InMemoryVectorStore):
    # type="tool": retrieval gets its own named tool span (input = question, output = joined excerpts).
    @opik.track(name="search_observing_logs", type="tool")
    def search_observing_logs(question: str) -> str:
        docs = store.similarity_search(question, k=TOP_K)
        # Metadata on the tool span lists which log entries were retrieved, so you can judge retrieval apart from the model.
        opik.opik_context.update_current_span(
            metadata={"entries": [d.metadata["entry"] for d in docs], "k": TOP_K}
        )
        return "\n\n---\n\n".join(d.page_content for d in docs)

    return search_observing_logs
