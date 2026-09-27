"""Run the agent from a terminal and print what it was allowed to do."""
from __future__ import annotations

import argparse
import sys

from .budget import Budget
from .graph import Agent
from .providers import ProviderChain, StubProvider


def _responder(prompt: str) -> str:
    """Offline stand-in that cites whatever source ids it was handed."""
    ids = [line.split("]")[0].lstrip("- [") for line in prompt.splitlines()
           if line.startswith("- [")]
    citations = " ".join(f"[{i}]" for i in ids)
    return f"Based on the retrieved sources: {citations}".strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="guardedagent")
    parser.add_argument("question")
    parser.add_argument("--approve", action="store_true",
                        help="permit the irreversible action if review approves")
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--max-usd", type=float, default=0.50)
    parser.add_argument("--trace", help="write the run trace to this path")
    args = parser.parse_args(argv)

    agent = Agent(
        chain=ProviderChain([StubProvider(responder=_responder)]),
        budget=Budget(max_steps=args.max_steps, max_usd=args.max_usd),
        approve=(lambda gate: True) if args.approve else None,
    )
    result = agent.run(args.question)

    print(f"verdict : {result.get('verdict')}")
    print(f"reason  : {result.get('reason')}")
    if "gate" in result:
        print(f"gate    : {'APPROVED' if result['gate']['approved'] else 'REFUSED'}")
    print(f"budget  : {agent.budget.snapshot()}")
    print(f"trace   : {agent.trace.summary()}")
    if args.trace:
        print(f"written : {agent.trace.save(args.trace)}")
    return 0 if result.get("verdict") != "blocked" else 1


if __name__ == "__main__":
    sys.exit(main())
