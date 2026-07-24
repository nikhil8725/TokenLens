from __future__ import annotations
import hashlib
import json
from ._base import Rule, Finding, Severity


class DuplicatePromptRule(Rule):
    """TL003 — Exact same message list sent multiple times → suggest caching."""

    rule_id = "TL003"
    phase = "post"

    def __init__(self) -> None:
        self._fired_hashes: set[str] = set()

    def check(self, record, session) -> list[Finding]:
        h = hashlib.sha256(
            json.dumps(record.messages, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

        count = session._prompt_hashes.get(h, 0)
        if count < 2 or h in self._fired_hashes:
            return []

        self._fired_hashes.add(h)
        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            call_id=record.call_id,
            message=f"Identical message list sent {count} times.",
            suggestion=(
                "Cache the result keyed on a hash of the messages. "
                "Example: use functools.lru_cache on the function, or maintain a "
                "dict[str, str] mapping prompt_hash → response. "
                "If this is a retry loop, consider exponential backoff instead of re-sending."
            ),
        )]
