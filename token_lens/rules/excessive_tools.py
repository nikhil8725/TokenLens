from __future__ import annotations
from ._base import Rule, Finding, Severity


class ExcessiveToolsRule(Rule):
    """TL012 — Too many tools registered in a single call slows routing and inflates the system prompt."""

    rule_id = "TL012"
    phase = "pre"

    def __init__(self, threshold: int = 15) -> None:
        self._threshold = threshold

    def check(self, record, session) -> list[Finding]:
        tools = record.raw_kwargs.get("tools") or record.raw_kwargs.get("functions") or []
        count = len(tools)
        if count <= self._threshold:
            return []
        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            call_id=record.call_id,
            message=f"{count} tools registered in this call (threshold: {self._threshold}).",
            suggestion=(
                "Large tool catalogs increase system-prompt tokens and make model tool-selection less reliable. "
                "Filter tools to only those relevant to the current task context, or split into specialized "
                "agents each with a focused toolset. Aim for ≤10 tools per call."
            ),
        )]
