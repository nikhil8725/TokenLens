from __future__ import annotations
from token_lens.rules.missing_max_tokens import MissingMaxTokensRule
from token_lens._session import Session
from ..conftest import make_record


def test_fires_when_no_max_tokens():
    rule = MissingMaxTokensRule()
    s = Session()
    record = make_record(raw_kwargs={"model": "gpt-4o-mini", "messages": []})
    findings = rule.check(record, s)
    assert len(findings) == 1
    assert findings[0].rule_id == "TL006"


def test_silent_when_max_tokens_set():
    rule = MissingMaxTokensRule()
    s = Session()
    record = make_record(raw_kwargs={
        "model": "gpt-4o-mini", "messages": [], "max_tokens": 256
    })
    findings = rule.check(record, s)
    assert findings == []


def test_silent_when_max_completion_tokens_set():
    rule = MissingMaxTokensRule()
    s = Session()
    record = make_record(raw_kwargs={
        "model": "gpt-4o-mini", "messages": [], "max_completion_tokens": 512
    })
    findings = rule.check(record, s)
    assert findings == []


def test_fires_when_max_tokens_explicitly_none():
    rule = MissingMaxTokensRule()
    s = Session()
    record = make_record(raw_kwargs={
        "model": "gpt-4o-mini", "messages": [], "max_tokens": None
    })
    findings = rule.check(record, s)
    assert len(findings) == 1
