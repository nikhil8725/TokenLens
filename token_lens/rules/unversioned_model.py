from __future__ import annotations
from ._base import Rule, Finding, Severity

_UNVERSIONED_ALIASES: frozenset[str] = frozenset({
    # OpenAI bare aliases (excluding mini — users pick mini for cost, pinning matters less)
    "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
    # Anthropic bare aliases
    "claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku",
    "claude-3-5-haiku", "claude-sonnet-4", "claude-opus-4", "claude-haiku-4",
    # OpenRouter bare aliases
    "openai/gpt-4o", "openai/gpt-4-turbo",
    "anthropic/claude-3.5-sonnet", "anthropic/claude-3-haiku",
    "anthropic/claude-3-opus",
})


class UnversionedModelRule(Rule):
    """TL010 — Unversioned model alias used — provider can silently update behavior."""

    rule_id = "TL010"
    phase = "post"

    def __init__(self) -> None:
        self._fired_aliases: set[str] = set()

    def check(self, record, session) -> list[Finding]:
        model = record.model
        if model not in _UNVERSIONED_ALIASES:
            return []
        if model in self._fired_aliases:
            return []
        self._fired_aliases.add(model)
        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            call_id=record.call_id,
            message=f"Model '{model}' is an unversioned alias.",
            suggestion=(
                f"Pin to a specific model version (e.g. 'gpt-4o-2024-11-20' instead of 'gpt-4o'). "
                "Unversioned aliases are updated by providers without notice — your prompts and "
                "evaluations may break silently between deployments. "
                "Check the provider's model versioning docs for the current pinned version."
            ),
        )]
