from __future__ import annotations

from astra.types import Usage

# Approximate cost per token (Claude Sonnet pricing)
INPUT_COST_PER_TOKEN = 3.0 / 1_000_000
OUTPUT_COST_PER_TOKEN = 15.0 / 1_000_000
CACHE_WRITE_COST_PER_TOKEN = 3.75 / 1_000_000
CACHE_READ_COST_PER_TOKEN = 0.30 / 1_000_000


class UsageTracker:
    def __init__(self, total: Usage | None = None) -> None:
        self.total = total or Usage()
        self.turn_count = 0

    def add(self, usage: Usage) -> None:
        self.total = self.total + usage
        self.turn_count += 1

    @property
    def estimated_cost_usd(self) -> float:
        return (
            self.total.input_tokens * INPUT_COST_PER_TOKEN
            + self.total.output_tokens * OUTPUT_COST_PER_TOKEN
            + self.total.cache_creation_input_tokens * CACHE_WRITE_COST_PER_TOKEN
            + self.total.cache_read_input_tokens * CACHE_READ_COST_PER_TOKEN
        )

    def summary(self) -> str:
        return (
            f"Tokens: {self.total.input_tokens:,} in / "
            f"{self.total.output_tokens:,} out | "
            f"Cost: ${self.estimated_cost_usd:.4f} | "
            f"Turns: {self.turn_count}"
        )
