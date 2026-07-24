from __future__ import annotations
from token_lens._session import Session
from ..conftest import make_record


def _rule():
    from token_lens.rules.pii_in_prompt import PIIInPromptRule
    return PIIInPromptRule()


def test_fires_for_email_in_user_message():
    rule = _rule()
    record = make_record(messages=[{"role": "user", "content": "My email is test@example.com please help"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL008" for f in findings)


def test_fires_for_phone_in_user_message():
    rule = _rule()
    record = make_record(messages=[{"role": "user", "content": "Call me at 415-555-0123 anytime"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL008" for f in findings)


def test_fires_for_credit_card_in_user_message():
    rule = _rule()
    record = make_record(messages=[{"role": "user", "content": "My card is 4111111111111111"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL008" for f in findings)


def test_fires_for_ssn_in_user_message():
    rule = _rule()
    record = make_record(messages=[{"role": "user", "content": "SSN: 123-45-6789"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL008" for f in findings)


def test_fires_for_ip_in_system_message():
    rule = _rule()
    record = make_record(messages=[{"role": "system", "content": "User IP is 192.168.1.100"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL008" for f in findings)


def test_fires_for_pii_in_tool_message():
    rule = _rule()
    record = make_record(messages=[{"role": "tool", "content": "User record: email=user@corp.com"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL008" for f in findings)


def test_silent_for_clean_message():
    rule = _rule()
    record = make_record(messages=[{"role": "user", "content": "What is the weather today?"}])
    findings = rule.check(record, Session())
    assert findings == []


def test_silent_for_assistant_role_by_default():
    rule = _rule()
    record = make_record(messages=[{"role": "assistant", "content": "Your email test@example.com was received."}])
    findings = rule.check(record, Session())
    assert findings == []


def test_finding_message_does_not_contain_matched_text():
    rule = _rule()
    record = make_record(messages=[{"role": "user", "content": "email: secret@private.com"}])
    findings = rule.check(record, Session())
    assert findings
    for f in findings:
        assert "secret@private.com" not in f.message
        assert "secret@private.com" not in f.suggestion


def test_severity_is_error():
    rule = _rule()
    from token_lens.rules._base import Severity
    record = make_record(messages=[{"role": "user", "content": "test@example.com"}])
    findings = rule.check(record, Session())
    assert findings
    assert all(f.severity == Severity.ERROR for f in findings)


def test_fires_at_pre_phase():
    from token_lens.rules.pii_in_prompt import PIIInPromptRule
    assert PIIInPromptRule().phase == "pre"
