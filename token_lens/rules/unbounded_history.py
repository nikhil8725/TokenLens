from __future__ import annotations
from ._base import Rule, Finding, Severity


class UnboundedHistoryRule(Rule):
    """TL002 — Conversation history grows without bound → suggest summarization."""

    rule_id = "TL002"
    phase = "post"

    def __init__(self, threshold: int = 20) -> None:
        self._threshold = threshold

    def check(self, record, session) -> list[Finding]:
        non_system = [m for m in record.messages if m.get("role") != "system"]
        count = len(non_system)
        if count <= self._threshold:
            return []

        # Only fire if history is growing (last 3 calls had fewer messages)
        recent_counts = []
        for r in session.calls[-3:]:
            recent_counts.append(
                len([m for m in r.messages if m.get("role") != "system"])
            )

        if len(recent_counts) >= 2 and recent_counts[-1] <= recent_counts[0]:
            return []

        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            call_id=record.call_id,
            message=f"Conversation history has {count} non-system messages and is growing.",
            suggestion=(
                "Long histories waste prompt tokens on stale context. "
                "Consider: (1) LangGraph's trim_messages() to keep only the last N turns, "
                "(2) a summarization node that compresses older turns into a single summary message, "
                "or (3) setting a max_history_length in your state management."
            ),
        )]
