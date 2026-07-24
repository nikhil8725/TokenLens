from __future__ import annotations
from .rules._base import Rule, Finding
from .rules import (
    StaticSystemPromptRule,
    UnboundedHistoryRule,
    DuplicatePromptRule,
    ModelOverkillRule,
    LongSystemPromptRule,
    MissingMaxTokensRule,
    RedundantContextRule,
    PIIInPromptRule,
    SecretInPromptRule,
    UnversionedModelRule,
    ToolResultBloatRule,
    ExcessiveToolsRule,
    MissingResponseFormatRule,
    CostSpikeRule,
    NCompletionsRule,
)
from ._config import Config


def _build_rules(config: Config) -> list[Rule]:
    rules: list[Rule] = [
        # pre-phase rules (fire before the real API call)
        PIIInPromptRule(check_roles=config.pii_check_roles),
        SecretInPromptRule(),
        MissingMaxTokensRule(),
        ExcessiveToolsRule(threshold=config.max_tools_per_call),
        MissingResponseFormatRule(),
        NCompletionsRule(),
        # post-phase rules (fire after response is received)
        StaticSystemPromptRule(threshold=config.static_prompt_repeat_threshold),
        UnboundedHistoryRule(threshold=config.history_message_threshold),
        DuplicatePromptRule(),
        ModelOverkillRule(
            high_tier_models=config.high_tier_models,
            completion_threshold=config.simple_task_completion_token_threshold,
        ),
        LongSystemPromptRule(threshold=config.system_prompt_token_threshold),
        RedundantContextRule(
            threshold=config.redundant_context_jaccard_threshold,
            min_words=config.redundant_context_min_words,
        ),
        UnversionedModelRule(),
        ToolResultBloatRule(threshold=config.tool_result_token_threshold),
        CostSpikeRule(min_calls=config.spike_min_calls, multiplier=config.spike_multiplier),
    ]
    return [r for r in rules if r.rule_id not in config.disabled_rules]


class Analyzer:
    def __init__(self, config: Config) -> None:
        self._rules = _build_rules(config)

    def analyze_pre_call(self, record, session) -> list[Finding]:
        return [
            f
            for rule in self._rules
            if rule.phase == "pre"
            for f in rule.check(record, session)
        ]

    def analyze_post_call(self, record, session) -> list[Finding]:
        return [
            f
            for rule in self._rules
            if rule.phase == "post"
            for f in rule.check(record, session)
        ]
