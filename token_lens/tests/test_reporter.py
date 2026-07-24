from __future__ import annotations
import sys
import io
from token_lens._reporter import Reporter
from token_lens._config import Config
from token_lens.rules._base import Finding, Severity


def _capture_stderr(fn):
    buf = io.StringIO()
    old = sys.stderr
    sys.stderr = buf
    try:
        fn()
    finally:
        sys.stderr = old
    return buf.getvalue()


def test_emit_finding_writes_to_stderr():
    reporter = Reporter(Config(no_color=True, auto_report_on_exit=False))
    findings = [Finding(
        rule_id="TL006",
        severity=Severity.WARNING,
        message="No max_tokens set.",
        suggestion="Add max_tokens=512.",
    )]
    out = _capture_stderr(lambda: reporter.emit_findings(findings))
    assert "TL006" in out
    assert "max_tokens" in out


def test_emit_finding_no_output_for_empty():
    reporter = Reporter(Config(no_color=True, auto_report_on_exit=False))
    out = _capture_stderr(lambda: reporter.emit_findings([]))
    assert out == ""


def test_session_report_empty_session():
    from token_lens._session import Session
    reporter = Reporter(Config(no_color=True, auto_report_on_exit=False))
    s = Session()
    out = _capture_stderr(lambda: reporter.print_session_report(s))
    assert out == ""


def test_session_report_shows_totals():
    from token_lens._session import Session
    from .conftest import make_record, make_usage
    reporter = Reporter(Config(no_color=True, auto_report_on_exit=False))
    s = Session()
    s.add_call(make_record(usage=make_usage(prompt=100, completion=40)))
    out = _capture_stderr(lambda: reporter.print_session_report(s))
    assert "140" in out
