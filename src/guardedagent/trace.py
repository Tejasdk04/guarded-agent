"""A structured record of what the agent did, written for humans reading an incident."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Span:
    name: str
    kind: str                      # "node" | "model" | "tool" | "gate"
    started_at: float
    ended_at: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def duration_ms(self) -> float:
        if self.ended_at is None:
            return 0.0
        return round((self.ended_at - self.started_at) * 1000, 3)


class Trace:
    """Collects spans for one run. Export it, diff it, attach it to a ticket."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.spans: list[Span] = []
        self._clock = time.monotonic

    def span(self, name: str, kind: str, **attributes: Any) -> "_SpanCtx":
        return _SpanCtx(self, name, kind, attributes)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "span_count": len(self.spans),
            "spans": [
                {**asdict(s), "duration_ms": s.duration_ms} for s in self.spans
            ],
        }

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str) + "\n")
        return path

    def summary(self) -> str:
        by_kind: dict[str, int] = {}
        for s in self.spans:
            by_kind[s.kind] = by_kind.get(s.kind, 0) + 1
        errors = sum(1 for s in self.spans if s.error)
        parts = ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items()))
        return f"run {self.run_id}: {parts}, errors={errors}"


class _SpanCtx:
    def __init__(self, trace: Trace, name: str, kind: str, attributes: dict):
        self.trace, self.span = trace, Span(name=name, kind=kind,
                                            started_at=trace._clock(), attributes=attributes)

    def __enter__(self) -> Span:
        return self.span

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.span.ended_at = self.trace._clock()
        if exc is not None:
            self.span.error = f"{exc_type.__name__}: {exc}"
        self.trace.spans.append(self.span)
        return False
