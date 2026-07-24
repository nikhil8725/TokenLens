from __future__ import annotations
from token_lens._session import Session
from ..conftest import make_record


def _rule():
    from token_lens.rules.n_completions import NCompletionsRule
    return NCompletionsRule()


def test_fires_when_n_is_2():
    rule = _rule()
    record = make_record(raw_kwargs={"model": "gpt-4o-mini", "messages": [], "n": 2})
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL015" for f in findings)


def test_fires_when_n_is_5():
    rule = _rule()
    record = make_record(raw_kwargs={"model": "gpt-4o-mini", "messages": [], "n": 5})
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL015" for f in findings)


def test_silent_when_n_is_1():
    rule = _rule()
    record = make_record(raw_kwargs={"model": "gpt-4o-mini", "messages": [], "n": 1})
    findings = rule.check(record, Session())
    assert findings == []


def test_silent_when_n_is_absent():
    rule = _rule()
    record = make_record(raw_kwargs={"model": "gpt-4o-mini", "messages": []})
    findings = rule.check(record, Session())
    assert findings == []


def test_fires_at_pre_phase():
    from token_lens.rules.n_completions import NCompletionsRule
    assert NCompletionsRule().phase == "pre"
