"""The typed state that flows through the graph."""
from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict


def append(left: list, right: list) -> list:
    """Reducer: nodes contribute to a list rather than overwriting it."""
    return (left or []) + (right or [])


class AgentState(TypedDict, total=False):
    question: str
    plan: list[str]
    findings: Annotated[list[dict], append]
    draft: str
    verdict: Literal["approved", "needs_human", "blocked"]
    reason: str
    gate: dict[str, Any]
    halted: bool
