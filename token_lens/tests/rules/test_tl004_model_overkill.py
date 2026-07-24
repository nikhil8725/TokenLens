from __future__ import annotations
from token_lens.rules.model_overkill import ModelOverkillRule
from token_lens._session import Session
from ..conftest import make_record, make_usage

HIGH_TIER = frozenset({"gpt-4o", "openai/gpt-4o"})


def test_fires_for_high_tier_short_output():
    rule = ModelOverkillRule(high_tier_models=HIGH_TIER, completion_threshold=80)
    s = Session()
    record = make_record(
        model="gpt-4o",
        messages=[{"role": "user", "content": "What is 2+2?"}],
        usage=make_usage(prompt=20, completion=5),
    )
    findings = rule.check(record, s)
    assert len(findings) == 1
    assert findings[0].rule_id == "TL004"


def test_silent_for_mini_model():
    rule = ModelOverkillRule(high_tier_models=HIGH_TIER, completion_threshold=80)
    s = Session()
    record = make_record(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "What is 2+2?"}],
        usage=make_usage(prompt=20, completion=5),
    )
    findings = rule.check(record, s)
    assert findings == []


def test_silent_for_long_output():
    rule = ModelOverkillRule(high_tier_models=HIGH_TIER, completion_threshold=80)
    s = Session()
    record = make_record(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Write a long essay."}],
        usage=make_usage(prompt=20, completion=500),
    )
    findings = rule.check(record, s)
    assert findings == []


def test_silent_for_multi_turn_conversation():
    rule = ModelOverkillRule(high_tier_models=HIGH_TIER, completion_threshold=80)
    s = Session()
    record = make_record(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
        ],
        usage=make_usage(prompt=30, completion=10),
    )
    findings = rule.check(record, s)
    assert findings == []


def test_silent_when_no_usage():
    rule = ModelOverkillRule(high_tier_models=HIGH_TIER, completion_threshold=80)
    s = Session()
    record = make_record(model="gpt-4o", usage=None)
    findings = rule.check(record, s)
    assert findings == []
