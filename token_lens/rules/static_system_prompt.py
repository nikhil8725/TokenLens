from __future__ import annotations
import hashlib
from ._base import Rule, Finding, Severity


class StaticSystemPromptRule(Rule):
    """TL001 — Same system prompt repeated N or more times → suggest caching."""

    rule_id = "TL001"
    phase = "post"

    def __init__(self, threshold: int = 3) -> None:
        self._threshold = threshold
        self._fired_hashes: set[str] = set()

    def check(self, record, session) -> list[Finding]:
        sys_texts = [
            m["content"]
            for m in record.messages
            if m.get("role") == "system" and isinstance(m.get("content"), str)
        ]
        if not sys_texts:
            return []

        text = sys_texts[0]
        h = hashlib.sha256(text.encode()).hexdigest()

        if h in self._fired_hashes:
            return []

        count = sum(1 for p in session._system_prompts if p == text)
        if count < self._threshold:
            return []

        self._fired_hashes.add(h)
        token_estimate = max(1, len(text) // 4)
        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            call_id=record.call_id,
            message=(
                f"System prompt is identical across {count}+ consecutive calls "
                f"(~{token_estimate} tokens each)."
            ),
            suggestion=(
                "Use prompt caching to avoid re-tokenizing it every call. "
                "For OpenAI: the API caches automatically for prompts >1024 tokens. "
                "For Anthropic: add cache_control to the system block. "
                "Potential saving: ~80% of system prompt tokens."
            ),
        )]
