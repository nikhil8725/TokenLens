from __future__ import annotations
import atexit
from typing import Any

from ._chat import InstrumentedChat
from ._session import Session
from ._analyzer import Analyzer
from ._reporter import Reporter
from ._config import Config


class TokenLens:
    """
    Transparent proxy around openai.OpenAI that intercepts chat.completions.create()
    and emits token-efficiency findings to stderr during development.

    Usage:
        from openai import OpenAI
        from token_lens import TokenLens

        client = TokenLens(OpenAI(api_key=..., base_url=...))
        response = client.chat.completions.create(...)  # identical call site
    """

    def __init__(self, client: Any, config: Config | None = None) -> None:
        self._client = client
        self._config = config or Config()

        if not self._config.enabled:
            # Passthrough mode — no instrumentation at all
            self._chat_instrument = None
            return

        self._session = Session()
        self._reporter = Reporter(self._config)
        self._analyzer = Analyzer(self._config)
        self._chat_instrument = InstrumentedChat(
            client.chat, self._session, self._analyzer, self._reporter
        )

        if self._config.auto_report_on_exit:
            atexit.register(self.session_report)

    @property
    def chat(self) -> Any:
        if self._chat_instrument is None:
            return self._client.chat
        return self._chat_instrument

    def session_report(self) -> None:
        """Print a session-level token summary. Called automatically via atexit."""
        if self._config.enabled and self._chat_instrument is not None:
            self._reporter.print_session_report(self._session)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
