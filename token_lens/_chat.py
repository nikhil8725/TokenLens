from __future__ import annotations
from datetime import datetime
from typing import Any
from uuid import uuid4

from ._session import Session, CallRecord, NormalizedUsage
from ._analyzer import Analyzer
from ._reporter import Reporter


class InstrumentedCompletions:
    def __init__(
        self,
        completions: Any,
        session: Session,
        analyzer: Analyzer,
        reporter: Reporter,
    ) -> None:
        self._completions = completions
        self._session = session
        self._analyzer = analyzer
        self._reporter = reporter

    def create(self, **kwargs: Any) -> Any:
        # Streaming: bypass analysis — can't inspect a generator without consuming it
        if kwargs.get("stream"):
            return self._completions.create(**kwargs)

        messages = list(kwargs.get("messages", []))
        record = CallRecord(
            call_id=uuid4(),
            timestamp=datetime.now(),
            model=str(kwargs.get("model", "unknown")),
            messages=messages,
            raw_kwargs=kwargs,
        )

        pre_findings = self._analyzer.analyze_pre_call(record, self._session)
        self._reporter.emit_findings(pre_findings)

        response = self._completions.create(**kwargs)

        record.response = response
        record.usage = _normalize_usage(response)
        self._session.add_call(record)

        post_findings = self._analyzer.analyze_post_call(record, self._session)
        self._reporter.emit_findings(post_findings)

        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._completions, name)


def _normalize_usage(response: Any) -> NormalizedUsage | None:
    """Extract token counts from any OpenAI-compatible response object."""
    raw = getattr(response, "usage", None)
    if raw is None:
        return None
    # OpenAI SDK: prompt_tokens / completion_tokens
    prompt = getattr(raw, "prompt_tokens", None)
    completion = getattr(raw, "completion_tokens", None)
    total = getattr(raw, "total_tokens", None)
    if prompt is None or completion is None:
        return None
    if total is None:
        total = prompt + completion
    return NormalizedUsage(
        prompt_tokens=int(prompt),
        completion_tokens=int(completion),
        total_tokens=int(total),
    )


class InstrumentedChat:
    def __init__(
        self,
        chat: Any,
        session: Session,
        analyzer: Analyzer,
        reporter: Reporter,
    ) -> None:
        self._chat = chat
        self.completions = InstrumentedCompletions(
            chat.completions, session, analyzer, reporter
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)
