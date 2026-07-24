from __future__ import annotations
from token_lens._session import Session
from ..conftest import make_record


def _rule():
    from token_lens.rules.unversioned_model import UnversionedModelRule
    return UnversionedModelRule()


def test_fires_for_gpt4o_alias():
    rule = _rule()
    record = make_record(model="gpt-4o")
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL010" for f in findings)


def test_fires_for_claude_sonnet_alias():
    rule = _rule()
    record = make_record(model="claude-3-5-sonnet")
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL010" for f in findings)


def test_fires_for_openrouter_alias():
    rule = _rule()
    record = make_record(model="openai/gpt-4o")
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL010" for f in findings)


def test_silent_for_pinned_model():
    rule = _rule()
    record = make_record(model="gpt-4o-2024-11-20")
    findings = rule.check(record, Session())
    assert findings == []


def test_silent_for_pinned_claude():
    rule = _rule()
    record = make_record(model="claude-3-5-sonnet-20241022")
    findings = rule.check(record, Session())
    assert findings == []


def test_silent_for_mini_model():
    rule = _rule()
    record = make_record(model="gpt-4o-mini")
    findings = rule.check(record, Session())
    assert findings == []


def test_silent_for_unknown_model():
    rule = _rule()
    record = make_record(model="custom-finetuned-v1")
    findings = rule.check(record, Session())
    assert findings == []


def test_fires_only_once_per_alias():
    rule = _rule()
    s = Session()
    for _ in range(3):
        r = make_record(model="gpt-4o")
        s.add_call(r)
        rule.check(r, s)
    # Fourth call — should not fire again for same alias
    r = make_record(model="gpt-4o")
    findings = rule.check(r, s)
    assert findings == []
