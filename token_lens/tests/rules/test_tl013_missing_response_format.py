from __future__ import annotations
from token_lens._session import Session
from ..conftest import make_record


def _rule():
    from token_lens.rules.missing_response_format import MissingResponseFormatRule
    return MissingResponseFormatRule()


def test_fires_when_json_requested_no_format():
    rule = _rule()
    record = make_record(
        messages=[{"role": "system", "content": "You must output JSON with keys name and age."}],
        raw_kwargs={"model": "gpt-4o-mini", "messages": [], "max_tokens": 128},
    )
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL013" for f in findings)


def test_silent_when_response_format_set():
    rule = _rule()
    record = make_record(
        messages=[{"role": "system", "content": "Output JSON with keys name and age."}],
        raw_kwargs={"model": "gpt-4o-mini", "messages": [], "response_format": {"type": "json_object"}},
    )
    findings = rule.check(record, Session())
    assert findings == []


def test_silent_when_no_json_keywords():
    rule = _rule()
    record = make_record(
        messages=[{"role": "system", "content": "You are a helpful assistant."}],
        raw_kwargs={"model": "gpt-4o-mini", "messages": []},
    )
    findings = rule.check(record, Session())
    assert findings == []


def test_fires_for_various_json_keywords():
    rule = _rule()
    for phrase in ["return JSON", "valid JSON", "as a JSON object", "respond with JSON"]:
        r2 = _rule()   # fresh rule instance to avoid fired-hash dedup
        record = make_record(
            messages=[{"role": "system", "content": f"Please {phrase} response."}],
            raw_kwargs={"model": "gpt-4o-mini", "messages": []},
        )
        findings = r2.check(record, Session())
        assert any(f.rule_id == "TL013" for f in findings), f"Should fire for: {phrase!r}"


def test_fires_once_per_unique_system_prompt():
    rule = _rule()
    s = Session()
    msgs = [{"role": "system", "content": "output JSON please"}]
    r1 = make_record(messages=msgs, raw_kwargs={"model": "gpt-4o-mini", "messages": []})
    rule.check(r1, s)  # fires
    s.add_call(r1)
    r2 = make_record(messages=msgs, raw_kwargs={"model": "gpt-4o-mini", "messages": []})
    findings2 = rule.check(r2, s)  # same hash, should not re-fire
    assert findings2 == []
