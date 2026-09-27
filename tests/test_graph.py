import pytest

from guardedagent.budget import Budget
from guardedagent.graph import Agent
from guardedagent.providers import ProviderChain, StubProvider


def citing_agent(**kwargs):
    """A stub that behaves itself: it cites the source it was given."""
    chain = ProviderChain([StubProvider(responder=lambda p: "Tides come from the Moon. [tides]")])
    return Agent(chain=chain, **kwargs)


def test_happy_path_reaches_the_gate_only_with_approval():
    agent = citing_agent(approve=lambda gate: True)
    out = agent.run("What causes tides?")
    assert out["verdict"] == "approved"
    assert out["gate"]["approved"] is True
    assert out["halted"] is False


def test_default_policy_refuses_the_irreversible_action():
    agent = citing_agent()  # no approve callback -> never auto-approve
    out = agent.run("What causes tides?")
    assert out["verdict"] == "approved", "the draft itself is fine"
    assert out["gate"]["approved"] is False
    assert out["halted"] is True, "but nothing was published"


def test_uncited_draft_is_routed_to_a_human_and_never_reaches_the_gate():
    chain = ProviderChain([StubProvider(responder=lambda p: "Trust me, it is the Moon.")])
    agent = Agent(chain=chain, approve=lambda gate: True)
    out = agent.run("What causes tides?")
    assert out["verdict"] == "needs_human"
    assert "gate" not in out, "the gate must be unreachable without an approved verdict"


def test_no_sources_is_blocked():
    agent = citing_agent(approve=lambda gate: True)
    out = agent.run("What is the airspeed of an unladen swallow?")
    assert out["verdict"] == "blocked"
    assert out["reason"] == "no sources were retrieved"


def test_budget_halt_is_recorded_in_the_trace():
    agent = citing_agent(budget=Budget(max_steps=2))
    out = agent.run("What causes tides?")
    assert out["verdict"] == "blocked"
    assert "step limit" in out["reason"]
    assert any(s.name == "halt" and s.error for s in agent.trace.spans)


def test_trace_captures_every_stage():
    agent = citing_agent(approve=lambda gate: True)
    agent.run("What causes tides?")
    kinds = {s.kind for s in agent.trace.spans}
    assert {"node", "model", "tool", "gate"} <= kinds


def test_budget_is_actually_spent():
    agent = citing_agent(approve=lambda gate: True)
    agent.run("What causes tides?")
    snap = agent.budget.snapshot()
    assert snap["tokens"] > 0 and snap["steps"] >= 4 and snap["tool_calls"] >= 1
