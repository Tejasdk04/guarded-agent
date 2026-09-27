# guarded-agent

[![ci](https://github.com/Tejasdk04/guarded-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Tejasdk04/guarded-agent/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)](#tests)
[![tests](https://img.shields.io/badge/tests-26%20passing-brightgreen)](#tests)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![langgraph](https://img.shields.io/badge/built%20on-LangGraph-orange)](https://github.com/langchain-ai/langgraph)

**A LangGraph agent that cannot overspend, cannot loop forever, and cannot take
an irreversible action without passing a gate.**

Most agent guardrails live in the prompt. That makes them suggestions — the
model is free to ignore them, and eventually it will. The guardrails here are
enforced in the runtime, so the only way past one is a code change that shows up
in review.

```bash
pip install -e ".[dev]"

guardedagent "What causes tides?"
# verdict : approved
# reason  : cites tides
# gate    : REFUSED        <-- the draft was fine; publishing still needs a human
```

Runs offline with no API key — the provider is pluggable and ships with a
deterministic stub, so the tests and the demo work in CI with no network.

---

## The four guarantees

| Guarantee | Enforced by | What it prevents |
|---|---|---|
| **Cannot overspend** | `Budget.check_call` runs *before* the call, on an estimate | A single expensive call blowing the budget and being noticed afterwards |
| **Cannot loop forever** | Step and tool-call ceilings | A non-converging graph burning money until someone notices |
| **Cannot silently degrade** | `ProviderChain` records every failure | A run that quietly fell back to a weaker model looking like a clean run |
| **Cannot act unilaterally** | `gate` node, reachable only from an `approved` verdict | The agent publishing something nobody agreed to |

## The graph

```
plan ──> gather ──> draft ──> review ──┬── approved ──> gate ──> END
                                       │
                                       └── needs_human / blocked ──> END
```

`review` is **deterministic code, not a model call**. A model does not get to
mark its own homework: the check is "does the draft actually cite the sources it
was given", and it either does or it does not.

The gate is the only path to an irreversible action, and its default policy is
to refuse:

```python
Agent()                            # never publishes
Agent(approve=lambda gate: True)   # publishes when review approves
Agent(approve=my_human_in_the_loop)
```

Because the gate is a graph node rather than an `if` buried in a tool, an
uncited draft does not merely fail to publish — it never reaches the gate at
all. There is a test asserting exactly that.

## Budgets are checked before the spend, not after

```python
budget = Budget(max_usd=0.10)
budget.check_call(est_tokens=10, est_usd=0.50)   # raises BudgetExceeded
assert budget.usd == 0.0                          # and nothing was charged
```

Checking afterwards means you always overshoot by one call. On a graph that
loops, one call can be many.

## Traces are for the incident, not the demo

Every node, model call, tool call and gate decision becomes a span with timings,
attributes and errors:

```python
agent.trace.save("traces/run.json")
agent.trace.summary()
# run 21f5be5f483b: gate=1, model=1, node=4, tool=1, errors=0
```

A halt is recorded as a span too. A run that stopped on budget leaves evidence
that it stopped on budget, rather than an absence of evidence.

## Swapping in a real model

`StubProvider` exists so the repo is runnable. Any object with a `complete`
method and a `usd_per_1k` works:

```python
class MyProvider:
    name, usd_per_1k = "gpt-4o-mini", 0.15

    def complete(self, prompt: str, max_tokens: int) -> Completion:
        ...  # your SDK call here

Agent(chain=ProviderChain([MyProvider(), StubProvider()]))  # with a fallback
```

## Tests

```bash
pytest --cov=guardedagent
# 26 passed, 99% coverage
```

The tests assert the *negative* cases, which are the ones that matter: that an
uncited draft cannot reach the gate, that a rejected call is not charged, that a
provider fallback is recorded rather than swallowed.

## Licence

MIT
