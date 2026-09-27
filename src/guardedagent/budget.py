"""Hard limits an agent cannot talk its way past.

Guardrails enforced inside the prompt are suggestions -- the model can ignore
them. These are enforced in the runtime, so the only way past them is a code
change that shows up in review.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    """The run hit a hard limit and was stopped."""


@dataclass
class Budget:
    """Tracks spend for a single run.

    ``max_usd`` is checked *before* a call is made, using an estimate, so a run
    cannot overshoot by one expensive call and then notice.
    """

    max_tokens: int = 20_000
    max_usd: float = 0.50
    max_steps: int = 12
    max_tool_calls: int = 20

    tokens: int = field(default=0, init=False)
    usd: float = field(default=0.0, init=False)
    steps: int = field(default=0, init=False)
    tool_calls: int = field(default=0, init=False)

    # -- checks ------------------------------------------------------------
    def check_step(self) -> None:
        if self.steps >= self.max_steps:
            raise BudgetExceeded(
                f"step limit reached ({self.max_steps}); the graph is not converging"
            )

    def check_call(self, est_tokens: int, est_usd: float) -> None:
        if self.tokens + est_tokens > self.max_tokens:
            raise BudgetExceeded(
                f"token budget would be exceeded: {self.tokens}+{est_tokens} > {self.max_tokens}"
            )
        if self.usd + est_usd > self.max_usd:
            raise BudgetExceeded(
                f"cost budget would be exceeded: ${self.usd:.4f}+${est_usd:.4f} > ${self.max_usd:.2f}"
            )

    def check_tool(self) -> None:
        if self.tool_calls >= self.max_tool_calls:
            raise BudgetExceeded(f"tool-call limit reached ({self.max_tool_calls})")

    # -- accounting --------------------------------------------------------
    def spend(self, tokens: int, usd: float) -> None:
        self.tokens += tokens
        self.usd += usd

    def step(self) -> None:
        self.check_step()
        self.steps += 1

    def tool(self) -> None:
        self.check_tool()
        self.tool_calls += 1

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.max_tokens - self.tokens)

    def snapshot(self) -> dict:
        return {
            "tokens": self.tokens,
            "usd": round(self.usd, 6),
            "steps": self.steps,
            "tool_calls": self.tool_calls,
        }
