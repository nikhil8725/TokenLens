from __future__ import annotations
from token_lens.rules.duplicate_prompt import DuplicatePromptRule
from token_lens._session import Session
from ..conftest import make_record

MSGS = [{"role": "user", "content": "What is the capital of France?"}]


def test_fires_on_second_identical_call():
    rule = DuplicatePromptRule()
    s = Session()
    r1 = make_record(messages=MSGS)
    s.add_call(r1)
    r2 = make_record(messages=MSGS)
    s.add_call(r2)
    findings = rule.check(r2, s)
    assert len(findings) == 1
    assert findings[0].rule_id == "TL003"


def test_silent_on_first_call():
    rule = DuplicatePromptRule()
    s = Session()
    r = make_record(messages=MSGS)
    s.add_call(r)
    findings = rule.check(r, s)
    assert findings == []


def test_silent_for_different_prompts():
    rule = DuplicatePromptRule()
    s = Session()
    r1 = make_record(messages=[{"role": "user", "content": "Question A"}])
    r2 = make_record(messages=[{"role": "user", "content": "Question B"}])
    s.add_call(r1)
    s.add_call(r2)
    findings = rule.check(r2, s)
    assert findings == []


def test_does_not_fire_again_after_first_alert():
    rule = DuplicatePromptRule()
    s = Session()
    for _ in range(3):
        r = make_record(messages=MSGS)
        s.add_call(r)
    r_last = make_record(messages=MSGS)
    s.add_call(r_last)
    rule.check(make_record(messages=MSGS), s)   # triggers first fire
    findings = rule.check(r_last, s)             # should not re-fire
    assert findings == []
