"""A LangGraph agent with guardrails the model cannot talk its way past.

Budgets, provider fallback, deterministic review and an approval gate in front
of every irreversible action -- all enforced in the runtime rather than asked
for in a prompt.
"""
from .budget import Budget, BudgetExceeded
from .graph import Agent
from .providers import AllProvidersFailed, Completion, ProviderChain, StubProvider
from .trace import Span, Trace

__version__ = "0.1.0"
__all__ = [
    "Agent", "Budget", "BudgetExceeded", "ProviderChain", "StubProvider",
    "Completion", "AllProvidersFailed", "Trace", "Span",
]
