"""The graph: plan -> gather -> draft -> review -> gate.

Every edge out of ``review`` is conditional, and the only path to an
irreversible action runs through ``gate``. That is the design point: you can
read this file and know what the agent is *incapable* of doing.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable

from langgraph.graph import END, StateGraph

from .budget import Budget, BudgetExceeded
from .providers import AllProvidersFailed, ProviderChain, StubProvider
from .state import AgentState
from .tools import IRREVERSIBLE, TOOLS, search
from .trace import Span, Trace


class Agent:
    """Wires budget, providers, tools and tracing into a compiled graph."""

    def __init__(
        self,
        chain: ProviderChain | None = None,
        budget: Budget | None = None,
        approve: Callable[[dict], bool] | None = None,
        run_id: str | None = None,
    ):
        self.chain = chain or ProviderChain([StubProvider()])
        self.budget = budget or Budget()
        # Default policy: never auto-approve. Explicit is the safe default.
        self.approve = approve or (lambda _gate: False)
        self.trace = Trace(run_id or uuid.uuid4().hex[:12])
        self.graph = self._build()

    # -- model access ------------------------------------------------------
    def _complete(self, prompt: str, max_tokens: int = 128) -> str:
        est_tokens, est_usd = self.chain.estimate(prompt, max_tokens)
        self.budget.check_call(est_tokens, est_usd)
        with self.trace.span("model", "model", chars=len(prompt)) as span:
            result = self.chain.complete(prompt, max_tokens)
            self.budget.spend(result.tokens, result.usd)
            span.attributes.update(provider=result.provider, tokens=result.tokens)
        return result.text

    def _call_tool(self, name: str, *args, **kwargs) -> Any:
        self.budget.tool()
        with self.trace.span(name, "tool", args=list(args)) as span:
            out = TOOLS[name](*args, **kwargs)
            span.attributes["ok"] = True
        return out

    # -- nodes -------------------------------------------------------------
    def _plan(self, state: AgentState) -> dict:
        self.budget.step()
        with self.trace.span("plan", "node"):
            question = state["question"]
            topics = search(question)
            return {"plan": topics or ["<no matching source>"]}

    def _gather(self, state: AgentState) -> dict:
        self.budget.step()
        with self.trace.span("gather", "node", planned=len(state.get("plan", []))):
            findings = []
            for doc_id in state.get("plan", []):
                if doc_id.startswith("<"):
                    continue
                doc = self._call_tool("read", doc_id)
                findings.append(doc.to_finding(state["question"]))
            return {"findings": findings}

    def _draft(self, state: AgentState) -> dict:
        self.budget.step()
        with self.trace.span("draft", "node", findings=len(state.get("findings", []))):
            sources = "\n".join(f"- [{f['doc_id']}] {f['text']}" for f in state.get("findings", []))
            prompt = (
                "Answer the question using only the sources. Cite doc ids in square "
                f"brackets.\n\nQuestion: {state['question']}\n\nSources:\n{sources}"
            )
            return {"draft": self._complete(prompt)}

    def _review(self, state: AgentState) -> dict:
        """Deterministic checks. A model does not get to mark its own homework."""
        self.budget.step()
        with self.trace.span("review", "node") as span:
            findings = state.get("findings", [])
            draft = state.get("draft", "")
            if not findings:
                span.attributes["reason"] = "no sources"
                return {"verdict": "blocked", "reason": "no sources were retrieved"}
            cited = [f["doc_id"] for f in findings if f"[{f['doc_id']}]" in draft]
            if not cited:
                span.attributes["reason"] = "uncited"
                return {"verdict": "needs_human", "reason": "draft cites none of its sources"}
            span.attributes["cited"] = cited
            return {"verdict": "approved", "reason": f"cites {', '.join(cited)}"}

    def _gate(self, state: AgentState) -> dict:
        """The only door to an irreversible action."""
        self.budget.step()
        request = {
            "action": "publish",
            "verdict": state.get("verdict"),
            "reason": state.get("reason"),
            "chars": len(state.get("draft", "")),
        }
        with self.trace.span("gate", "gate", **request) as span:
            allowed = bool(self.approve(request))
            span.attributes["approved"] = allowed
            if not allowed:
                return {"gate": {**request, "approved": False}, "halted": True}
            IRREVERSIBLE["publish"](state.get("draft", ""), destination="stdout")
            return {"gate": {**request, "approved": True}, "halted": False}

    # -- wiring ------------------------------------------------------------
    @staticmethod
    def _route(state: AgentState) -> str:
        return "gate" if state.get("verdict") == "approved" else "stop"

    def _build(self):
        g = StateGraph(AgentState)
        g.add_node("plan", self._plan)
        g.add_node("gather", self._gather)
        g.add_node("draft", self._draft)
        g.add_node("review", self._review)
        g.add_node("gate", self._gate)

        g.set_entry_point("plan")
        g.add_edge("plan", "gather")
        g.add_edge("gather", "draft")
        g.add_edge("draft", "review")
        g.add_conditional_edges("review", self._route, {"gate": "gate", "stop": END})
        g.add_edge("gate", END)
        return g.compile()

    # -- entry point -------------------------------------------------------
    def run(self, question: str) -> AgentState:
        try:
            result = self.graph.invoke({"question": question})
        except (BudgetExceeded, AllProvidersFailed) as exc:
            # A halt is part of the record, not an absence of one.
            self.trace.spans.append(
                Span(name="halt", kind="gate", started_at=0.0, ended_at=0.0,
                     error=f"{type(exc).__name__}: {exc}")
            )
            kind = "budget" if isinstance(exc, BudgetExceeded) else "providers"
            return {"question": question, "verdict": "blocked",
                    "reason": f"{kind}: {exc}", "halted": True}
        return result
