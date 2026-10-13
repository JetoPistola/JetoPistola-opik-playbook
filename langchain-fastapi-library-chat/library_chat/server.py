"""FastAPI chat backend for the Maple Street Library widget, traced with OpikTracer.

Each POST /chat is one LangChain run. The chain is string in -> string out, so the
trace's input is the patron's message and its output is the librarian's reply;
the OpikTracer's thread_id is the widget's conversation id.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load this example's .env, then walk up to the repo-root .env (existing values win).
for parent in Path(__file__).resolve().parents:
    if (parent / ".env").exists():
        load_dotenv(parent / ".env")

PROJECT_NAME = "langchain-fastapi-library-chat"
# Every trace lands in this Opik project (unless OPIK_PROJECT_NAME is already set).
os.environ.setdefault("OPIK_PROJECT_NAME", PROJECT_NAME)

import opik  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langchain_core.output_parsers import StrOutputParser  # noqa: E402
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder  # noqa: E402
from langchain_core.runnables import RunnableConfig, RunnableLambda  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402
from opik.integrations.langchain import OpikTracer  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from library_chat.catalog import format_books, search_catalog  # noqa: E402

SYSTEM_PROMPT = """You are Dewey, the chat assistant for the Maple Street Public Library.
Recommend books ONLY from the catalog excerpts provided below. Mention the title and author,
say in one line why it fits, and be honest about availability (offer to place a hold when
every copy is checked out). If nothing in the excerpts fits, say so instead of inventing a book.
Keep replies to 3 sentences or fewer; this is a small chat widget.

Catalog excerpts for this turn:
{books}"""

# conversation_id -> message history (the bot's memory)
HISTORY: dict[str, list] = {}


def prepare(message: str, config: RunnableConfig) -> dict:
    conversation_id = config["configurable"]["conversation_id"]
    history = HISTORY.setdefault(conversation_id, [])
    # Search on the new message plus the patron's earlier asks, so "something shorter" keeps its topic.
    earlier = " ".join(m.content for m in history if isinstance(m, HumanMessage))
    books = search_catalog(f"{message} {message} {earlier}")
    return {"books": format_books(books), "history": history, "message": message}


prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), MessagesPlaceholder("history"), ("human", "{message}")]
)
chain = (
    RunnableLambda(prepare).with_config(run_name="prepare-context")
    | prompt
    | ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    | StrOutputParser()
)

app = FastAPI(title="Maple Street Library chat")


class ChatRequest(BaseModel):
    message: str
    conversation_id: str


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    if not req.message.strip():
        raise HTTPException(400, "message must not be empty")
    # One OpikTracer per request: the run becomes a trace named `library-chat-turn` whose
    # children are prepare-context, ChatPromptTemplate, ChatOpenAI (llm span with tokens
    # and cost) and StrOutputParser. thread_id=conversation_id groups the turns of one chat
    # into a single thread in the Threads tab; without it every turn is an unrelated trace.
    tracer = OpikTracer(thread_id=req.conversation_id, project_name=PROJECT_NAME, tags=["library-widget"])
    reply = chain.invoke(
        req.message,
        config={
            "callbacks": [tracer],
            # run_name becomes the trace name in the Traces tab.
            "run_name": "library-chat-turn",
            "configurable": {"conversation_id": req.conversation_id},
        },
    )
    history = HISTORY[req.conversation_id]
    history += [HumanMessage(req.message), AIMessage(reply)]
    return {"reply": reply, "conversation_id": req.conversation_id}


@app.get("/health")
def health() -> dict:
    return {"ok": True}


def flush() -> None:
    # Traces are sent in the background; flush before the process exits or the last turns can be lost.
    opik.flush_tracker()
