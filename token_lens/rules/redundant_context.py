from __future__ import annotations
from ._base import Rule, Finding, Severity


def _word_set(text: str) -> set[str]:
    return set(text.lower().split())


def _jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


class RedundantContextRule(Rule):
    """TL007 — Two or more messages share high content overlap → flag redundancy."""

    rule_id = "TL007"
    phase = "post"

    def __init__(self, threshold: float = 0.70, min_words: int = 50) -> None:
        self._threshold = threshold
        self._min_words = min_words

    def check(self, record, session) -> list[Finding]:
        contents: list[tuple[str, str]] = []  # (role, text)
        for m in record.messages:
            content = m.get("content", "")
            if isinstance(content, str) and len(content.split()) >= self._min_words:
                contents.append((m.get("role", "unknown"), content))

        findings = []
        seen_pairs: set[tuple[int, int]] = set()
        for i, (role_a, text_a) in enumerate(contents):
            words_a = _word_set(text_a)
            for j, (role_b, text_b) in enumerate(contents):
                if j <= i or (i, j) in seen_pairs:
                    continue
                seen_pairs.add((i, j))
                words_b = _word_set(text_b)
                score = _jaccard(words_a, words_b)
                if score >= self._threshold:
                    pct = int(score * 100)
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        severity=Severity.INFO,
                        call_id=record.call_id,
                        message=(
                            f"Message [role:{role_a}] and [role:{role_b}] share ~{pct}% "
                            f"word overlap."
                        ),
                        suggestion=(
                            "Duplicate context wastes prompt tokens. Extract the shared content "
                            "into the system prompt (sent once) or deduplicate before building "
                            "the messages list."
                        ),
                    ))
        return findings
