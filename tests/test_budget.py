import pytest

from guardedagent.budget import Budget, BudgetExceeded


def test_cost_is_checked_before_spending_not_after():
    budget = Budget(max_usd=0.10)
    with pytest.raises(BudgetExceeded, match="cost budget would be exceeded"):
        budget.check_call(est_tokens=10, est_usd=0.50)
    assert budget.usd == 0.0, "a rejected call must not be charged"


def test_token_ceiling():
    budget = Budget(max_tokens=100)
    budget.spend(90, 0.0)
    with pytest.raises(BudgetExceeded, match="token budget"):
        budget.check_call(est_tokens=20, est_usd=0.0)
    assert budget.remaining_tokens == 10


def test_step_limit_stops_a_non_converging_graph():
    budget = Budget(max_steps=2)
    budget.step()
    budget.step()
    with pytest.raises(BudgetExceeded, match="not converging"):
        budget.step()


def test_tool_call_limit():
    budget = Budget(max_tool_calls=1)
    budget.tool()
    with pytest.raises(BudgetExceeded, match="tool-call limit"):
        budget.tool()


def test_snapshot_shape():
    budget = Budget()
    budget.spend(10, 0.001)
    budget.step()
    assert budget.snapshot() == {"tokens": 10, "usd": 0.001, "steps": 1, "tool_calls": 0}
