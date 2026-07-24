from __future__ import annotations
from unittest.mock import MagicMock
from token_lens import TokenLens, Config
from .conftest import make_response


def test_chat_completions_create_returns_response(mock_client):
    expected = make_response()
    mock_client.chat.completions.create.return_value = expected
    client = TokenLens(mock_client, Config(auto_report_on_exit=False))
    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=64,
    )
    assert result is expected


def test_non_chat_attributes_delegate_to_underlying(mock_client):
    client = TokenLens(mock_client, Config(auto_report_on_exit=False))
    _ = client.models
    mock_client.models  # just accessing should not raise


def test_embeddings_delegated(mock_client):
    client = TokenLens(mock_client, Config(auto_report_on_exit=False))
    client.embeddings.create(input="hello", model="text-embedding-ada-002")
    mock_client.embeddings.create.assert_called_once()


def test_streaming_passthrough(mock_client):
    stream_val = MagicMock()
    mock_client.chat.completions.create.return_value = stream_val
    client = TokenLens(mock_client, Config(auto_report_on_exit=False))
    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "stream me"}],
        stream=True,
    )
    assert result is stream_val


def test_disabled_config_bypasses_instrumentation(mock_client):
    expected = make_response()
    mock_client.chat.completions.create.return_value = expected
    client = TokenLens(mock_client, Config(enabled=False, auto_report_on_exit=False))
    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert result is expected
