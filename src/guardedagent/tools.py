"""Tools the agent may call.

The corpus is a small offline fixture so the repository is runnable and
testable without a network. Swap ``search`` and ``read`` for real
implementations and the graph is unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass

CORPUS: dict[str, str] = {
    "tides": (
        "Tides are caused by the gravitational pull of the Moon and, to a lesser "
        "extent, the Sun. Most coasts see two high tides a day."
    ),
    "photosynthesis": (
        "Photosynthesis converts light energy into chemical energy, producing "
        "glucose and releasing oxygen as a by-product."
    ),
    "monsoon": (
        "A monsoon is a seasonal reversal in prevailing wind direction, bringing "
        "a pronounced wet season to much of South and Southeast Asia."
    ),
}


@dataclass
class Document:
    doc_id: str
    text: str

    def to_finding(self, query: str) -> dict:
        return {"doc_id": self.doc_id, "query": query, "text": self.text}


def search(query: str, limit: int = 3) -> list[str]:
    """Return doc ids whose id or text matches any word in the query."""
    words = {w.strip(".,?!").lower() for w in query.split() if len(w) > 3}
    hits = [
        doc_id for doc_id, text in CORPUS.items()
        if doc_id in words or any(w in text.lower() for w in words)
    ]
    return sorted(hits)[:limit]


def read(doc_id: str) -> Document:
    if doc_id not in CORPUS:
        raise KeyError(f"unknown document: {doc_id!r}")
    return Document(doc_id=doc_id, text=CORPUS[doc_id])


#: A tool that changes the world. Never reached without passing the gate.
def publish(draft: str, destination: str) -> dict:
    return {"published": True, "destination": destination, "chars": len(draft)}


TOOLS = {"search": search, "read": read}
IRREVERSIBLE = {"publish": publish}
