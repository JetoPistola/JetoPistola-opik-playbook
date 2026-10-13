"""Split the observing logs into one chunk per '##' session entry."""
from pathlib import Path

from langchain_core.documents import Document


def load_chunks(docs_dir: Path) -> list[Document]:
    chunks: list[Document] = []
    for path in sorted(docs_dir.glob("*.md")):
        title, *sections = path.read_text().split("\n## ")
        for section in sections:
            heading = section.splitlines()[0].strip()
            chunks.append(Document(
                page_content=f"{title.strip()}\n\n## {section.strip()}",
                metadata={"source": path.name, "entry": heading},
            ))
    return chunks
