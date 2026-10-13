"""Tiny keyword retriever over the fictional Maple Street Library catalog."""
import json
import re
from pathlib import Path

CATALOG = json.loads((Path(__file__).parent.parent / "data" / "catalog.json").read_text())
STOP = {"a", "an", "the", "i", "me", "my", "is", "are", "do", "you", "have", "any", "for", "to", "of",
        "and", "or", "it", "that", "this", "what", "something", "something", "like", "want", "can", "in", "on", "with", "about", "please", "more", "one", "some", "got"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP}


def search_catalog(query: str, k: int = 3) -> list[dict]:
    """Rank books by keyword overlap with title, genre, tags and summary."""
    q = _words(query)
    scored = []
    for book in CATALOG:
        haystack = _words(" ".join([book["title"], book["genre"], book["summary"], *book["tags"]]))
        tag_hits = q & _words(" ".join(book["tags"] + [book["genre"]]))
        score = len(q & haystack) + 2 * len(tag_hits)
        if score:
            scored.append((score, book))
    scored.sort(key=lambda s: -s[0])
    return [b for _, b in scored[:k]]


def format_books(books: list[dict]) -> str:
    if not books:
        return "(no matching books found in the catalog)"
    return "\n".join(
        f"- {b['title']} by {b['author']} [{b['genre']}] - {b['summary']} "
        f"({'%d copies available' % b['copies_available'] if b['copies_available'] else 'all copies checked out'})"
        for b in books
    )
