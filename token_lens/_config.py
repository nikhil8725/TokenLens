from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Config:
    enabled: bool = True

    no_color: bool = False
    auto_report_on_exit: bool = True

    # TL001 — static system prompt
    static_prompt_repeat_threshold: int = 3

    # TL002 — unbounded history
    history_message_threshold: int = 20

    # TL004 — model overkill
    high_tier_models: frozenset[str] = field(
        default_factory=lambda: frozenset({
            "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-4-32k",
            "claude-3-5-sonnet-20241022", "claude-3-opus-20240229",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "openai/gpt-4-turbo",
        })
    )
    simple_task_completion_token_threshold: int = 80

    # TL005 — long system prompt
    system_prompt_token_threshold: int = 500

    # TL007 — redundant context
    redundant_context_jaccard_threshold: float = 0.70
    redundant_context_min_words: int = 50

    # TL008 — PII in prompt
    pii_check_roles: set[str] = field(default_factory=lambda: {"user", "system", "tool"})

    # TL011 — tool result bloat
    tool_result_token_threshold: int = 500

    # TL012 — excessive tools
    max_tools_per_call: int = 15

    # TL014 — cost spike
    spike_min_calls: int = 5
    spike_multiplier: float = 3.0

    disabled_rules: set[str] = field(default_factory=set)
