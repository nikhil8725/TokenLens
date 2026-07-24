from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4

from ._session import Session, CallRecord, NormalizedUsage
from ._analyzer import Analyzer
from ._reporter import Reporter
from ._config import Config


def _lc_role(msg: object) -> str:
    cls_name = type(msg).__name__
    if cls_name == "SystemMessage":
        return "system"
    if cls_name == "AIMessage":
        return "assistant"
    if cls_name == "ToolMessage":
        return "tool"
    return "user"


class TokenLensCallbackHandler:
    """
    LangGraph / LangChain callback handler for projects using ChatOpenAI or init_chat_model.

    Usage:
        from token_lens import TokenLensCallbackHandler

        handler = TokenLensCallbackHandler()
        result = app.invoke(state, config={"callbacks": [handler]})
        handler.session_report()
    """

    raise_error = False

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()
        self.session = Session()
        self._analyzer = Analyzer(self._config)
        self._reporter = Reporter(self._config)
        self._pending: dict[str, CallRecord] = {}

    def on_chat_model_start(
        self,
        serialized: dict,
        messages: list[list],
        *,
        run_id: UUID,
        **kwargs: object,
    ) -> None:
        flat = []
        for batch in messages:
            for msg in batch:
                content = getattr(msg, "content", "")
                flat.append({"role": _lc_role(msg), "content": content})

        model_name = ((serialized or {}).get("kwargs") or {}).get("model_name", "unknown")
        record = CallRecord(
            call_id=uuid4(),
            timestamp=datetime.now(),
            model=str(model_name),
            messages=flat,
            raw_kwargs={},
        )
        self._pending[str(run_id)] = record

        findings = self._analyzer.analyze_pre_call(record, self.session)
        self._reporter.emit_findings(findings)

    def on_llm_end(self, response: object, *, run_id: UUID, **kwargs: object) -> None:
        record = self._pending.pop(str(run_id), None)
        if record is None:
            return

        for generation_list in getattr(response, "generations", []):
            for gen in generation_list:
                msg = getattr(gen, "message", None)
                if msg is None:
                    continue
                meta = getattr(msg, "usage_metadata", None) or {}
                if meta:
                    prompt = meta.get("input_tokens")
                    completion = meta.get("output_tokens")
                    if prompt is not None and completion is not None:
                        record.usage = NormalizedUsage(
                            prompt_tokens=int(prompt),
                            completion_tokens=int(completion),
                            total_tokens=int(prompt) + int(completion),
                        )
                break

        self.session.add_call(record)
        findings = self._analyzer.analyze_post_call(record, self.session)
        self._reporter.emit_findings(findings)

    def on_llm_error(self, error: Exception, *, run_id: UUID, **kwargs: object) -> None:
        self._pending.pop(str(run_id), None)

    def session_report(self) -> None:
        self._reporter.print_session_report(self.session)
