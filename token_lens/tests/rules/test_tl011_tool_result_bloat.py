from __future__ import annotations
from token_lens._session import Session
from ..conftest import make_record


def _rule(threshold=50):
    from token_lens.rules.tool_result_bloat import ToolResultBloatRule
    return ToolResultBloatRule(threshold=threshold)


def test_fires_for_large_tool_result():
    rule = _rule(threshold=10)
    big_content = "word " * 200   # ~200 tokens
    record = make_record(messages=[
        {"role": "user", "content": "search"},
        {"role": "tool", "content": big_content},
    ])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL011" for f in findings)


def test_silent_for_small_tool_result():
    rule = _rule(threshold=500)
    record = make_record(messages=[
        {"role": "tool", "content": '{"status": "ok", "count": 3}'},
    ])
    findings = rule.check(record, Session())
    assert findings == []


def test_silent_for_non_tool_message():
    rule = _rule(threshold=10)
    big_content = "word " * 200
    record = make_record(messages=[{"role": "user", "content": big_content}])
    findings = rule.check(record, Session())
    assert findings == []


def test_uses_config_threshold():
    rule = _rule(threshold=5)
    record = make_record(messages=[{"role": "tool", "content": "hello world foo bar baz qux quux"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL011" for f in findings)
