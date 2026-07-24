from __future__ import annotations
from token_lens.rules.unbounded_history import UnboundedHistoryRule
from token_lens._session import Session
from ..conftest import make_record


def _msgs(n: int) -> list[dict]:
    return [{"role": "user", "content": f"msg {i}"} for i in range(n)]


def test_fires_when_over_threshold_and_growing():
    rule = UnboundedHistoryRule(threshold=5)
    s = Session()

    # Add prior calls with growing history
    for size in [3, 4, 5]:
        s.add_call(make_record(messages=_msgs(size)))

    record = make_record(messages=_msgs(7))
    s.add_call(record)
    findings = rule.check(record, s)
    assert len(findings) == 1
    assert findings[0].rule_id == "TL002"


def test_silent_below_threshold():
    rule = UnboundedHistoryRule(threshold=20)
    s = Session()
    record = make_record(messages=_msgs(5))
    findings = rule.check(record, s)
    assert findings == []


def test_silent_when_history_not_growing():
    rule = UnboundedHistoryRule(threshold=5)
    s = Session()
    # History shrinks (e.g. after a reset)
    for size in [10, 8, 6]:
        s.add_call(make_record(messages=_msgs(size)))
    record = make_record(messages=_msgs(6))
    s.add_call(record)
    findings = rule.check(record, s)
    assert findings == []
