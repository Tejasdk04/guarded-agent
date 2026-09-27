import pytest

from guardedagent.providers import (
    AllProvidersFailed, ProviderChain, StubProvider,
)


def test_falls_through_to_the_next_provider():
    chain = ProviderChain([StubProvider(name="primary", fail=True), StubProvider(name="backup")])
    result = chain.complete("hello")
    assert result.provider == "backup"
    assert chain.failures == [("primary", "primary is configured to fail")]


def test_degradation_is_recorded_not_swallowed():
    chain = ProviderChain([StubProvider(name="a", fail=True), StubProvider(name="b")])
    chain.complete("x")
    assert len(chain.failures) == 1, "a silent fallback would hide a degraded run"


def test_all_failing_raises_with_every_reason():
    chain = ProviderChain([StubProvider(name="a", fail=True), StubProvider(name="b", fail=True)])
    with pytest.raises(AllProvidersFailed) as err:
        chain.complete("x")
    assert "a:" in str(err.value) and "b:" in str(err.value)


def test_empty_chain_rejected():
    with pytest.raises(ValueError):
        ProviderChain([])


def test_estimate_uses_the_primary_price():
    chain = ProviderChain([StubProvider(name="pricey", usd_per_1k=2.0)])
    tokens, usd = chain.estimate("a b c", max_tokens=97)
    assert tokens == 100
    assert usd == pytest.approx(0.2)
