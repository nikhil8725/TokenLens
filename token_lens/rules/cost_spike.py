from __future__ import annotations
from ._base import Rule, Finding, Severity


class CostSpikeRule(Rule):
    """TL014 — Single call token count is an outlier vs session mean."""

    rule_id = "TL014"
    phase = "post"

    def __init__(self, min_calls: int = 5, multiplier: float = 3.0) -> None:
        self._min_calls = min_calls
        self._multiplier = multiplier

    def check(self, record, session) -> list[Finding]:
        if record.usage is None:
            return []

        prior_calls = [c for c in session.calls if c.usage is not None and c.call_id != record.call_id]
        if len(prior_calls) < self._min_calls:
            return []

        mean = sum(c.usage.total_tokens for c in prior_calls) / len(prior_calls)
        call_total = record.usage.total_tokens
        threshold = mean * self._multiplier

        if call_total < threshold:
            return []

        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            call_id=record.call_id,
            message=(
                f"This call used {call_total} tokens — "
                f"{call_total / mean:.1f}× the session mean of {mean:.0f}."
            ),
            suggestion=(
                "Investigate what caused this spike: large tool results, unbounded history, "
                "or a prompt that grew unexpectedly. "
                "Set max_tokens to cap worst-case costs. "
                "If this is an agentic loop, check that context is being trimmed between steps."
            ),
        )]
