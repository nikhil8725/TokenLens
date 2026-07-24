from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime
from token_lens._session import NormalizedUsage


def make_usage(prompt=50, completion=20) -> NormalizedUsage:
    return NormalizedUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
    )


def make_openai_raw_usage(prompt=50, completion=20):
    """Mock the raw openai SDK usage object (before normalization)."""
    u = MagicMock()
    u.prompt_tokens = prompt
    u.completion_tokens = completion
    u.total_tokens = prompt + completion
    return u


def make_response(model="gpt-4o-mini", prompt=50, completion=20, content="Test response"):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    resp.model = model
    resp.usage = make_openai_raw_usage(prompt, completion)
    return resp


def make_anthropic_response(model="claude-3-haiku-20240307", prompt=50, completion=20, content="Test"):
    raw_usage = MagicMock()
    raw_usage.input_tokens = prompt
    raw_usage.output_tokens = completion
    resp = MagicMock()
    resp.model = model
    resp.usage = raw_usage
    block = MagicMock()
    block.text = content
    resp.content = [block]
    return resp


def make_record(
    messages=None,
    model="gpt-4o-mini",
    raw_kwargs=None,
    usage=None,
):
    from token_lens._session import CallRecord
    if messages is None:
        messages = [{"role": "user", "content": "hello"}]
    if raw_kwargs is None:
        raw_kwargs = {"model": model, "messages": messages}
    return CallRecord(
        call_id=uuid4(),
        timestamp=datetime.now(),
        model=model,
        messages=messages,
        raw_kwargs=raw_kwargs,
        usage=usage,
    )


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.chat.completions.create.return_value = make_response()
    return client


@pytest.fixture
def empty_session():
    from token_lens._session import Session
    return Session()
