from __future__ import annotations
import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from collections import Counter


@dataclass
class NormalizedUsage:
    """Provider-agnostic token counts. Populated after every call regardless of SDK."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class CallRecord:
    call_id: UUID
    timestamp: datetime
    model: str
    messages: list[dict]
    raw_kwargs: dict
    response: object = None
    usage: NormalizedUsage | None = None


class Session:
    def __init__(self) -> None:
        self.calls: list[CallRecord] = []
        self._system_prompts: list[str] = []
        self._prompt_hashes: Counter[str] = Counter()
        self._lock = threading.Lock()

    def add_call(self, record: CallRecord) -> None:
        with self._lock:
            self.calls.append(record)
            sys_texts = [
                m["content"]
                for m in record.messages
                if m.get("role") == "system" and isinstance(m.get("content"), str)
            ]
            if sys_texts:
                self._system_prompts.append(sys_texts[0])
            fingerprint = _hash_messages(record.messages)
            self._prompt_hashes[fingerprint] += 1

    def total_tokens(self) -> int:
        with self._lock:
            return sum(r.usage.total_tokens for r in self.calls if r.usage)

    def calls_by_model(self) -> dict[str, list[CallRecord]]:
        with self._lock:
            result: dict[str, list[CallRecord]] = {}
            for r in self.calls:
                result.setdefault(r.model, []).append(r)
            return result


def _hash_messages(messages: list[dict]) -> str:
    normalized = json.dumps(messages, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode()).hexdigest()
