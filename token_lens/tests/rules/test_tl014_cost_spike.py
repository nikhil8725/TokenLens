from __future__ import annotations
from token_lens._session import Session
from ..conftest import make_record, make_usage


def _rule(min_calls=5, multiplier=3.0):
    from token_lens.rules.cost_spike import CostSpikeRule
    return CostSpikeRule(min_calls=min_calls, multiplier=multiplier)


def _populate_session(n: int, total_tokens: int = 100) -> Session:
    s = Session()
    for _ in range(n):
        r = make_record(usage=make_usage(prompt=total_tokens // 2, completion=total_tokens // 2))
        s.add_call(r)
    return s


def test_fires_when_call_is_outlier():
    rule = _rule(min_calls=3, multiplier=3.0)
    s = _populate_session(5, total_tokens=100)   # mean = 100
    spike = make_record(usage=make_usage(prompt=200, completion=200))  # total=400 = 4× mean
    s.add_call(spike)
    findings = rule.check(spike, s)
    assert any(f.rule_id == "TL014" for f in findings)


def test_silent_below_min_calls():
    rule = _rule(min_calls=5, multiplier=3.0)
    s = _populate_session(3, total_tokens=100)
    spike = make_record(usage=make_usage(prompt=500, completion=500))
    s.add_call(spike)
    findings = rule.check(spike, s)
    assert findings == []


def test_silent_for_normal_variation():
    rule = _rule(min_calls=3, multiplier=3.0)
    s = _populate_session(5, total_tokens=100)
    normal = make_record(usage=make_usage(prompt=100, completion=100))  # 2× mean — below threshold
    s.add_call(normal)
    findings = rule.check(normal, s)
    assert findings == []


def test_fires_on_each_anomalous_call():
    rule = _rule(min_calls=3, multiplier=3.0)
    s = _populate_session(5, total_tokens=100)
    for _ in range(2):
        spike = make_record(usage=make_usage(prompt=250, completion=250))
        s.add_call(spike)
        findings = rule.check(spike, s)
        assert any(f.rule_id == "TL014" for f in findings)


def test_silent_when_no_usage():
    rule = _rule(min_calls=3, multiplier=3.0)
    s = _populate_session(5, total_tokens=100)
    r = make_record(usage=None)
    s.add_call(r)
    findings = rule.check(r, s)
    assert findings == []
