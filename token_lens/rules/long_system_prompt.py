from __future__ import annotations
import hashlib
from ._base import Rule, Finding, Severity


class LongSystemPromptRule(Rule):
    """TL005 — System prompt is very long → suggest compression or retrieval."""

    rule_id = "TL005"
    phase = "post"

    def __init__(self, threshold: int = 500) -> None:
        self._threshold = threshold
        self._fired_hashes: set[str] = set()

    def check(self, record, session) -> list[Finding]:
        from .._tokenizer import count_tokens

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

        token_count = count_tokens(text, record.model)
        if token_count <= self._threshold:
            return []

        self._fired_hashes.add(h)
        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.INFO,
            call_id=record.call_id,
            message=f"System prompt is ~{token_count} tokens.",
            suggestion=(
                "Large system prompts inflate every call's cost. Consider: "
                "(1) Moving static reference data to RAG/retrieval instead of inline context, "
                "(2) Prompt compression (LLMLingua, gzip-style rewriting), "
                "(3) Splitting into a smaller core prompt + dynamic context injected per call."
            ),
        )]
