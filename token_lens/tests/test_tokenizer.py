from __future__ import annotations
from token_lens._tokenizer import count_tokens, count_messages_tokens


def test_count_tokens_nonempty():
    n = count_tokens("Hello, world!")
    assert n > 0


def test_count_tokens_empty_string():
    # fallback: max(1, 0 // 4) = 1; tiktoken may return 0 — either is fine
    n = count_tokens("")
    assert n >= 0


def test_count_messages_tokens_basic():
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "What is 2+2?"},
    ]
    total = count_messages_tokens(messages)
    assert total > 10  # sanity: some overhead + content


def test_count_messages_tokens_grows_with_content():
    short = [{"role": "user", "content": "hi"}]
    long = [{"role": "user", "content": "hi " * 200}]
    assert count_messages_tokens(long) > count_messages_tokens(short)
