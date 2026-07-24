from __future__ import annotations
import io
import sys
from unittest.mock import MagicMock
from token_lens import AnthropicTokenLens, Config
from .conftest import make_anthropic_response


def _wrap_anthropic(model="claude-3-haiku-20240307", prompt=50, completion=20):
    client = MagicMock()
    client.messages.create.return_value = make_anthropic_response(
        model=model, prompt=prompt, completion=completion
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


def test_messages_create_returns_response():
    mock = _wrap_anthropic()
    expected = mock.messages.create.return_value
    client = AnthropicTokenLens(mock, Config(auto_report_on_exit=False))
    result = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=256,
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert result is expected


def test_tl006_fires_for_missing_max_tokens():
    mock = _wrap_anthropic()
    client = AnthropicTokenLens(mock, Config(auto_report_on_exit=False))
    out = _capture_stderr(lambda: client.messages.create(
        model="claude-3-haiku-20240307",
        messages=[{"role": "user", "content": "Hello"}],
        # max_tokens intentionally omitted
    ))
    assert "TL006" in out


def test_usage_normalized_from_anthropic_format():
    mock = _wrap_anthropic(prompt=100, completion=40)
    client = AnthropicTokenLens(mock, Config(auto_report_on_exit=False))

    def run():
        client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=256,
            messages=[{"role": "user", "content": "Hello"}],
        )
        client.session_report()

    out = _capture_stderr(run)
    assert "140" in out  # 100 + 40


def test_system_prompt_extracted_from_anthropic_kwargs():
    """Anthropic passes system as a top-level kwarg, not inside messages."""
    mock = _wrap_anthropic()
    client = AnthropicTokenLens(mock, Config(auto_report_on_exit=False))

    def run_three():
        for _ in range(3):
            client.messages.create(
                model="claude-3-haiku-20240307",
                system="You are a helpful assistant for testing purposes only.",
                max_tokens=128,
                messages=[{"role": "user", "content": "Hi"}],
            )

    out = _capture_stderr(run_three)
    assert "TL001" in out


def test_non_messages_attributes_delegate():
    mock = _wrap_anthropic()
    client = AnthropicTokenLens(mock, Config(auto_report_on_exit=False))
    _ = client.models     # should delegate to underlying mock, not raise
    mock.models           # access the mock property to confirm no AttributeError


def test_streaming_passthrough():
    mock = _wrap_anthropic()
    stream_val = MagicMock()
    mock.messages.create.return_value = stream_val
    client = AnthropicTokenLens(mock, Config(auto_report_on_exit=False))
    result = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=256,
        messages=[{"role": "user", "content": "stream"}],
        stream=True,
    )
    assert result is stream_val
