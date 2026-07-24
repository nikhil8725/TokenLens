from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import uuid4

from ._session import Session, CallRecord, NormalizedUsage
from ._analyzer import Analyzer
from ._reporter import Reporter


def _normalize_anthropic_usage(response: Any) -> NormalizedUsage | None:
    """Extract token counts from a native anthropic.Message response."""
    raw = getattr(response, "usage", None)
    if raw is None:
        return None
    # Anthropic SDK: input_tokens / output_tokens
    prompt = getattr(raw, "input_tokens", None)
    completion = getattr(raw, "output_tokens", None)
    if prompt is None or completion is None:
        return None
    return NormalizedUsage(
        prompt_tokens=int(prompt),
        completion_tokens=int(completion),
        total_tokens=int(prompt) + int(completion),
    )


def _anthropic_to_messages(kwargs: dict) -> list[dict]:
    """Convert Anthropic messages.create kwargs into normalized messages list."""
    msgs: list[dict] = []
    system_text = kwargs.get("system")
    if system_text:
        if isinstance(system_text, str):
            msgs.append({"role": "system", "content": system_text})
        elif isinstance(system_text, list):
            # Anthropic allows system as a list of blocks
            text = " ".join(
                b.get("text", "") if isinstance(b, dict) else ""
                for b in system_text
            )
            msgs.append({"role": "system", "content": text})
    for m in kwargs.get("messages", []):
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                b.get("text", "") if isinstance(b, dict) else ""
                for b in content
            )
        msgs.append({"role": role, "content": content})
    return msgs


class InstrumentedAnthropicMessages:
    def __init__(
        self,
        messages: Any,
        session: Session,
        analyzer: Analyzer,
        reporter: Reporter,
    ) -> None:
        self._messages = messages
        self._session = session
        self._analyzer = analyzer
        self._reporter = reporter

    def create(self, **kwargs: Any) -> Any:
        if kwargs.get("stream"):
            return self._messages.create(**kwargs)

        normalized_messages = _anthropic_to_messages(kwargs)
        record = CallRecord(
            call_id=uuid4(),
            timestamp=datetime.now(),
            model=str(kwargs.get("model", "unknown")),
            messages=normalized_messages,
            raw_kwargs=kwargs,
        )

        pre_findings = self._analyzer.analyze_pre_call(record, self._session)
        self._reporter.emit_findings(pre_findings)

        response = self._messages.create(**kwargs)

        record.response = response
        record.usage = _normalize_anthropic_usage(response)
        self._session.add_call(record)

        post_findings = self._analyzer.analyze_post_call(record, self._session)
        self._reporter.emit_findings(post_findings)

        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._messages, name)
