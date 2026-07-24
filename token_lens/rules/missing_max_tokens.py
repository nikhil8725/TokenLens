from __future__ import annotations
from ._base import Rule, Finding, Severity


class MissingMaxTokensRule(Rule):
    """TL006 — No max_tokens set on the call → warn about runaway completions."""

    rule_id = "TL006"
    phase = "pre"

    def check(self, record, session) -> list[Finding]:
        kwargs = record.raw_kwargs
        has_max = (
            kwargs.get("max_tokens") is not None
            or kwargs.get("max_completion_tokens") is not None
        )
        if has_max:
            return []

        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            call_id=record.call_id,
            message=f"No max_tokens set on call to '{record.model}'.",
            suggestion=(
                "Without a cap, a misbehaving prompt can generate thousands of tokens and "
                "spike your costs unexpectedly. Add max_tokens=<your expected upper bound> "
                "(e.g. max_tokens=512 for short responses, max_tokens=2048 for longer ones)."
            ),
        )]
