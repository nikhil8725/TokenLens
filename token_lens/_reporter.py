from __future__ import annotations
import os
import sys
from ._config import Config
from .rules._base import Finding, Severity

_YELLOW = "\033[33m"
_RED    = "\033[31m"
_CYAN   = "\033[36m"
_GREEN  = "\033[32m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_RESET  = "\033[0m"

_SEVERITY_COLOR = {
    Severity.ERROR:   _RED,
    Severity.WARNING: _YELLOW,
    Severity.INFO:    _CYAN,
}
_SEVERITY_ICON = {
    Severity.ERROR:   "✖",
    Severity.WARNING: "⚠",
    Severity.INFO:    "ℹ",
}


class Reporter:
    def __init__(self, config: Config) -> None:
        self._color = (
            sys.stderr.isatty()
            and not config.no_color
            and os.environ.get("NO_COLOR") is None
            and os.environ.get("TOKEN_LENS_NO_COLOR") is None
        )

    def _c(self, code: str, text: str) -> str:
        return f"{code}{text}{_RESET}" if self._color else text

    def emit_findings(self, findings: list[Finding]) -> None:
        for f in findings:
            color = _SEVERITY_COLOR[f.severity]
            icon = _SEVERITY_ICON[f.severity]
            header = self._c(color + _BOLD, f"{icon} [token-lens {f.rule_id}]")
            print(f"{header} {f.message}", file=sys.stderr)
            print(f"  {self._c(_DIM, '→')} {f.suggestion}", file=sys.stderr)

    def print_session_report(self, session) -> None:
        if not session.calls:
            return

        header = self._c(_BOLD + _GREEN, "── token-lens session summary ──")
        print(f"\n{header}", file=sys.stderr)

        total = session.total_tokens()
        prompt_total = sum(
            (r.usage.prompt_tokens if r.usage else 0) for r in session.calls
        )
        completion_total = sum(
            (r.usage.completion_tokens if r.usage else 0) for r in session.calls
        )

        print(f"  calls:             {len(session.calls)}", file=sys.stderr)
        print(f"  prompt tokens:     {prompt_total:,}", file=sys.stderr)
        print(f"  completion tokens: {completion_total:,}", file=sys.stderr)
        print(f"  total tokens:      {total:,}", file=sys.stderr)

        for model, calls in session.calls_by_model().items():
            model_tokens = sum((r.usage.total_tokens if r.usage else 0) for r in calls)
            print(
                f"  {model}: {len(calls)} call(s), {model_tokens:,} tokens",
                file=sys.stderr,
            )

        print(file=sys.stderr)
