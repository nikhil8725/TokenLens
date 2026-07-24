from __future__ import annotations
from ._base import Rule, Finding, Severity


class NCompletionsRule(Rule):
    """TL015 — n>1 completions requested, multiplying token usage and cost."""

    rule_id = "TL015"
    phase = "pre"

    def check(self, record, session) -> list[Finding]:
        n = record.raw_kwargs.get("n", 1)
        if n is None or n <= 1:
            return []
        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            call_id=record.call_id,
            message=f"n={n} completions requested — token cost multiplied by {n}.",
            suggestion=(
                f"n={n} sends the same prompt {n} times and bills you for all completions. "
                "This is rarely needed in production; it was designed for offline evaluation. "
                "If you need output diversity, vary the prompt or temperature instead. "
                "If you are doing evals, generate one at a time so you can inspect/filter early."
            ),
        )]
