"""The retrieve-then-answer chain, local ChatOllama only."""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import ChatOllama

from .config import CHAT_MODEL, OLLAMA_BASE_URL
from .retrieve import make_retriever

PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are the Marlowe Ridge Astronomy Club's logbook assistant. Answer "
     "using only the log excerpts below. If they do not cover it, say so. "
     "Answer in at most three sentences.\n\n{context}"),
    ("human", "{question}"),
])


def build_chain(store):
    llm = ChatOllama(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL,
                     temperature=0, num_predict=200)
    chain = (
        {"context": make_retriever(store), "question": RunnablePassthrough()}
        | PROMPT | llm | StrOutputParser()
    )
    return chain.with_config({"run_name": "ask_the_logbook"})
