"""Pluggable model providers with an explicit fallback chain.

Nothing here talks to a real API. A provider is any callable with a ``complete``
method; the offline ``StubProvider`` makes the whole graph runnable -- and
testable in CI -- with no key and no network.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence


class ProviderError(RuntimeError):
    """A provider failed and the chain should try the next one."""


class AllProvidersFailed(RuntimeError):
    """Every provider in the chain failed."""


@dataclass
class Completion:
    text: str
    tokens: int
    usd: float
    provider: str


class Provider(Protocol):
    name: str
    usd_per_1k: float

    def complete(self, prompt: str, max_tokens: int) -> Completion: ...


@dataclass
class StubProvider:
    """Deterministic offline provider.

    ``responder`` maps a prompt to text. Defaults to echoing a summary so the
    graph produces something structured without a network call.
    """

    name: str = "stub"
    usd_per_1k: float = 0.0
    responder: Callable[[str], str] | None = None
    fail: bool = False

    def complete(self, prompt: str, max_tokens: int) -> Completion:
        if self.fail:
            raise ProviderError(f"{self.name} is configured to fail")
        text = self.responder(prompt) if self.responder else f"[{self.name}] {prompt[:120]}"
        # Rough token proxy; a real provider returns exact usage.
        tokens = max(1, len(prompt.split()) + len(text.split()))
        return Completion(text=text, tokens=tokens, usd=tokens / 1000 * self.usd_per_1k,
                          provider=self.name)


class ProviderChain:
    """Try each provider in order; the first success wins.

    Failures are recorded rather than swallowed, so a run that silently
    degraded to a cheaper model is visible in the trace afterwards.
    """

    def __init__(self, providers: Sequence[Provider]):
        if not providers:
            raise ValueError("a chain needs at least one provider")
        self.providers = list(providers)
        self.failures: list[tuple[str, str]] = []

    def estimate(self, prompt: str, max_tokens: int) -> tuple[int, float]:
        """Pre-call estimate, used to enforce the budget before spending it."""
        primary = self.providers[0]
        tokens = len(prompt.split()) + max_tokens
        return tokens, tokens / 1000 * primary.usd_per_1k

    def complete(self, prompt: str, max_tokens: int = 256) -> Completion:
        for provider in self.providers:
            try:
                return provider.complete(prompt, max_tokens)
            except ProviderError as exc:
                self.failures.append((provider.name, str(exc)))
        raise AllProvidersFailed(
            "all providers failed: "
            + "; ".join(f"{name}: {err}" for name, err in self.failures)
        )
