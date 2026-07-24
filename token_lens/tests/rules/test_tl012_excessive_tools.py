from __future__ import annotations
from token_lens._session import Session
from ..conftest import make_record


def _rule(threshold=15):
    from token_lens.rules.excessive_tools import ExcessiveToolsRule
    return ExcessiveToolsRule(threshold=threshold)


def _tools(n: int) -> list[dict]:
    return [{"type": "function", "function": {"name": f"tool_{i}", "description": "desc"}} for i in range(n)]


def test_fires_for_too_many_tools():
    rule = _rule(threshold=5)
    record = make_record(raw_kwargs={"model": "gpt-4o-mini", "messages": [], "tools": _tools(10)})
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL012" for f in findings)


def test_silent_for_acceptable_count():
    rule = _rule(threshold=15)
    record = make_record(raw_kwargs={"model": "gpt-4o-mini", "messages": [], "tools": _tools(10)})
    findings = rule.check(record, Session())
    assert findings == []


def test_checks_functions_key_too():
    rule = _rule(threshold=5)
    fns = [{"name": f"fn_{i}"} for i in range(10)]
    record = make_record(raw_kwargs={"model": "gpt-4o-mini", "messages": [], "functions": fns})
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL012" for f in findings)


def test_silent_when_no_tools():
    rule = _rule(threshold=5)
    record = make_record(raw_kwargs={"model": "gpt-4o-mini", "messages": []})
    findings = rule.check(record, Session())
    assert findings == []
