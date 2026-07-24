from __future__ import annotations
from token_lens.rules.redundant_context import RedundantContextRule
from token_lens._session import Session
from ..conftest import make_record

_LONG = "apple banana cherry date elderberry fig grape honeydew " * 10  # 80 words * 8 = long


def test_fires_for_high_overlap():
    rule = RedundantContextRule(threshold=0.70, min_words=10)
    s = Session()
    record = make_record(messages=[
        {"role": "system", "content": _LONG},
        {"role": "user", "content": _LONG},
    ])
    findings = rule.check(record, s)
    assert len(findings) >= 1
    assert findings[0].rule_id == "TL007"


def test_silent_for_low_overlap():
    rule = RedundantContextRule(threshold=0.70, min_words=5)
    s = Session()
    record = make_record(messages=[
        {"role": "system", "content": "cats dogs birds fish " * 10},
        {"role": "user", "content": "sky rain cloud thunder " * 10},
    ])
    findings = rule.check(record, s)
    assert findings == []


def test_silent_when_messages_too_short():
    rule = RedundantContextRule(threshold=0.70, min_words=50)
    s = Session()
    record = make_record(messages=[
        {"role": "system", "content": "hello world"},
        {"role": "user", "content": "hello world"},
    ])
    findings = rule.check(record, s)
    assert findings == []
