from __future__ import annotations
from ._base import Rule, Finding, Severity

_SUGGESTIONS: dict[str, str] = {
    "gpt-4o":                       "gpt-4o-mini (~10x cheaper, similar quality for simple tasks)",
    "openai/gpt-4o":                "openai/gpt-4o-mini (~10x cheaper)",
    "gpt-4-turbo":                  "gpt-4o-mini",
    "openai/gpt-4-turbo":           "openai/gpt-4o-mini",
    "gpt-4":                        "gpt-4o-mini",
    "gpt-4-32k":                    "gpt-4o-mini",
    "claude-3-5-sonnet-20241022":   "claude-3-haiku-20240307 (~15x cheaper for simple tasks)",
    "anthropic/claude-3.5-sonnet":  "anthropic/claude-3-haiku",
    "claude-3-opus-20240229":       "claude-3-haiku-20240307 (~60x cheaper)",
}


class ModelOverkillRule(Rule):
    """TL004 — High-tier model used for a simple, short-output task."""

    rule_id = "TL004"
    phase = "post"

    def __init__(self, high_tier_models: frozenset[str], completion_threshold: int = 80) -> None:
        self._high_tier = high_tier_models
        self._threshold = completion_threshold

    def check(self, record, session) -> list[Finding]:
        if record.model not in self._high_tier:
            return []

        if record.usage is None:
            return []

        completion_tokens = record.usage.completion_tokens
        if completion_tokens >= self._threshold:
            return []

        # Only flag if it's a single non-system user message (clearly simple task)
        non_system = [m for m in record.messages if m.get("role") != "system"]
        if len(non_system) != 1:
            return []

        suggestion_model = _SUGGESTIONS.get(record.model, "a smaller/cheaper model")
        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.INFO,
            call_id=record.call_id,
            message=(
                f"High-tier model '{record.model}' generated only {completion_tokens} tokens "
                f"for a single-message call."
            ),
            suggestion=(
                f"Consider {suggestion_model} for short, simple tasks. "
                "Benchmark first to confirm quality is acceptable for your use case."
            ),
        )]
