from __future__ import annotations
from ._base import Rule, Finding, Severity


class ToolResultBloatRule(Rule):
    """TL011 — Tool/function result exceeds token threshold, likely unsummarized raw data."""

    rule_id = "TL011"
    phase = "post"

    def __init__(self, threshold: int = 500) -> None:
        self._threshold = threshold

    def check(self, record, session) -> list[Finding]:
        from .._tokenizer import count_tokens

        findings = []
        for i, msg in enumerate(record.messages):
            if msg.get("role") != "tool":
                continue
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue
            token_count = count_tokens(content, record.model)
            if token_count > self._threshold:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=Severity.WARNING,
                    call_id=record.call_id,
                    message=(
                        f"Tool result at message index {i} is ~{token_count} tokens "
                        f"(threshold: {self._threshold})."
                    ),
                    suggestion=(
                        "Large tool results are usually unsummarized raw API responses or file contents. "
                        "Before returning to the model: extract only the fields it needs, "
                        "truncate to relevant sections, or summarize with a cheap model call. "
                        "This is the most common cause of cost spikes in production agent pipelines."
                    ),
                ))
        return findings
