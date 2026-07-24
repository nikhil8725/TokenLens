from __future__ import annotations

_TIKTOKEN_AVAILABLE: bool | None = None
_WARNED = False


def _check_tiktoken() -> bool:
    global _TIKTOKEN_AVAILABLE, _WARNED
    if _TIKTOKEN_AVAILABLE is None:
        try:
            import tiktoken  # noqa: F401
            _TIKTOKEN_AVAILABLE = True
        except ImportError:
            _TIKTOKEN_AVAILABLE = False
            if not _WARNED:
                import sys
                print(
                    "[token-lens] tiktoken not found — using ~4 chars/token estimate. "
                    "Install tiktoken for accurate counts: pip install tiktoken",
                    file=sys.stderr,
                )
                _WARNED = True
    return _TIKTOKEN_AVAILABLE


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    if _check_tiktoken():
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    return max(1, len(text) // 4)


def count_messages_tokens(messages: list[dict], model: str = "gpt-4o") -> int:
    """Token count using OpenAI's message overhead formula (~4 tokens/message + content)."""
    total = 3
    for msg in messages:
        total += 4
        content = msg.get("content", "")
        if isinstance(content, str):
            total += count_tokens(content, model)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += count_tokens(part["text"], model)
    return total
