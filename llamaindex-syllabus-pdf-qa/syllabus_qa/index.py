"""Load the syllabus PDFs and build a vector index over them."""

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.query_engine import BaseQueryEngine

from syllabus_qa.config import SYLLABI_DIR, TOP_K, configure_llama_index
from syllabus_qa.corpus import generate_syllabi


def build_index() -> VectorStoreIndex:
    configure_llama_index()
    generate_syllabi()  # no-op when the committed PDFs are present
    docs = SimpleDirectoryReader(str(SYLLABI_DIR), required_exts=[".pdf"]).load_data()
    return VectorStoreIndex.from_documents(docs)


def build_query_engine(index: VectorStoreIndex | None = None) -> BaseQueryEngine:
    return (index or build_index()).as_query_engine(similarity_top_k=TOP_K)
