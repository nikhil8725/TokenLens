from __future__ import annotations
from token_lens.rules.long_system_prompt import LongSystemPromptRule
from token_lens._session import Session
from ..conftest import make_record


def test_fires_for_long_system_prompt():
    rule = LongSystemPromptRule(threshold=10)
    s = Session()
    long_text = "word " * 200   # ~200 tokens (rough)
    record = make_record(messages=[
        {"role": "system", "content": long_text},
        {"role": "user", "content": "hi"},
    ])
    findings = rule.check(record, s)
    assert len(findings) == 1
    assert findings[0].rule_id == "TL005"


def test_silent_for_short_system_prompt():
    rule = LongSystemPromptRule(threshold=500)
    s = Session()
    record = make_record(messages=[
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "hi"},
    ])
    findings = rule.check(record, s)
    assert findings == []


def test_does_not_fire_twice_for_same_prompt():
    rule = LongSystemPromptRule(threshold=10)
    s = Session()
    long_text = "word " * 200
    record = make_record(messages=[
        {"role": "system", "content": long_text},
        {"role": "user", "content": "hi"},
    ])
    rule.check(record, s)   # first fire
    findings = rule.check(record, s)  # same prompt hash — silent
    assert findings == []


def test_silent_when_no_system_message():
    rule = LongSystemPromptRule(threshold=10)
    s = Session()
    record = make_record(messages=[{"role": "user", "content": "hi"}])
    findings = rule.check(record, s)
    assert findings == []
