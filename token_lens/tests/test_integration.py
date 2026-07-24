from __future__ import annotations
import io
import sys
from unittest.mock import MagicMock
from token_lens import TokenLens, Config
from .conftest import make_response


def _wrap_client(prompt_tokens=50, completion_tokens=20, model="gpt-4o-mini"):
    client = MagicMock()
    client.chat.completions.create.return_value = make_response(
        model=model, prompt=prompt_tokens, completion=completion_tokens
    )
    return client


def _capture_stderr(fn):
    buf = io.StringIO()
    old = sys.stderr
    sys.stderr = buf
    try:
        fn()
    finally:
        sys.stderr = old
    return buf.getvalue()


SYS = "You are an expert chef with decades of experience in Michelin-starred restaurants."


def test_tl006_fires_for_missing_max_tokens():
    client = TokenLens(_wrap_client(), Config(auto_report_on_exit=False))
    out = _capture_stderr(lambda: client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hello"}],
    ))
    assert "TL006" in out


def test_tl001_fires_after_three_identical_system_prompts():
    mock = _wrap_client()
    client = TokenLens(mock, Config(auto_report_on_exit=False))

    def run_three():
        for _ in range(3):
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYS},
                    {"role": "user", "content": "What should I cook?"},
                ],
                max_tokens=128,
            )

    out = _capture_stderr(run_three)
    assert "TL001" in out


def test_session_summary_shows_total_tokens():
    mock = _wrap_client(prompt_tokens=100, completion_tokens=40)
    client = TokenLens(mock, Config(auto_report_on_exit=False))

    def run():
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=64,
        )
        client.session_report()

    out = _capture_stderr(run)
    assert "140" in out  # 100 + 40
