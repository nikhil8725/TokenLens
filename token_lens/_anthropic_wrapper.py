from __future__ import annotations
import atexit
from typing import Any

from ._anthropic_messages import InstrumentedAnthropicMessages
from ._session import Session
from ._analyzer import Analyzer
from ._reporter import Reporter
from ._config import Config


class AnthropicTokenLens:
    """
    Transparent proxy around anthropic.Anthropic that intercepts messages.create()
    and emits token-efficiency findings to stderr during development.

    Usage:
        import anthropic
        from token_lens import AnthropicTokenLens

        client = AnthropicTokenLens(anthropic.Anthropic(api_key=...))
        response = client.messages.create(...)  # identical call site
    """

    def __init__(self, client: Any, config: Config | None = None) -> None:
        self._client = client
        self._config = config or Config()

        if not self._config.enabled:
            self._messages_instrument = None
            return

        self._session = Session()
        self._reporter = Reporter(self._config)
        self._analyzer = Analyzer(self._config)
        self._messages_instrument = InstrumentedAnthropicMessages(
            client.messages, self._session, self._analyzer, self._reporter
        )

        if self._config.auto_report_on_exit:
            atexit.register(self.session_report)

    @property
    def messages(self) -> Any:
        if self._messages_instrument is None:
            return self._client.messages
        return self._messages_instrument

    def session_report(self) -> None:
        if self._config.enabled and self._messages_instrument is not None:
            self._reporter.print_session_report(self._session)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
