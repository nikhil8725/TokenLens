from __future__ import annotations
from token_lens.rules.static_system_prompt import StaticSystemPromptRule
from token_lens._session import Session
from ..conftest import make_record

SYS = "You are a helpful assistant."


def _session_with_sys(n: int) -> Session:
    s = Session()
    for _ in range(n):
        r = make_record(messages=[
            {"role": "system", "content": SYS},
            {"role": "user", "content": "hello"},
        ])
        s.add_call(r)
    return s


def test_fires_after_threshold():
    rule = StaticSystemPromptRule(threshold=3)
    s = _session_with_sys(3)
    record = make_record(messages=[
        {"role": "system", "content": SYS},
        {"role": "user", "content": "hello"},
    ])
    s.add_call(record)
    findings = rule.check(record, s)
    assert len(findings) == 1
    assert findings[0].rule_id == "TL001"


def test_silent_below_threshold():
    rule = StaticSystemPromptRule(threshold=3)
    s = _session_with_sys(1)
    record = make_record(messages=[
        {"role": "system", "content": SYS},
        {"role": "user", "content": "hello"},
    ])
    s.add_call(record)
    findings = rule.check(record, s)
    assert findings == []


def test_does_not_fire_twice_for_same_hash():
    rule = StaticSystemPromptRule(threshold=3)
    s = _session_with_sys(3)
    record = make_record(messages=[
        {"role": "system", "content": SYS},
        {"role": "user", "content": "hello"},
    ])
    s.add_call(record)
    rule.check(record, s)  # first fire
    findings2 = rule.check(record, s)  # should not re-fire
    assert findings2 == []


def test_no_system_message_silent():
    rule = StaticSystemPromptRule(threshold=3)
    s = Session()
    record = make_record(messages=[{"role": "user", "content": "hello"}])
    findings = rule.check(record, s)
    assert findings == []
