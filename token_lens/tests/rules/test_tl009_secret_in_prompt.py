from __future__ import annotations
from token_lens._session import Session
from ..conftest import make_record


def _rule():
    from token_lens.rules.secret_in_prompt import SecretInPromptRule
    return SecretInPromptRule()


def test_fires_for_openai_key():
    rule = _rule()
    fake_key = "sk-" + "a" * 48
    record = make_record(messages=[{"role": "user", "content": f"Use key {fake_key} for auth"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL009" for f in findings)


def test_fires_for_anthropic_key():
    rule = _rule()
    fake_key = "sk-ant-" + "a" * 90
    record = make_record(messages=[{"role": "system", "content": f"api_key={fake_key}"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL009" for f in findings)


def test_fires_for_aws_key():
    rule = _rule()
    record = make_record(messages=[{"role": "tool", "content": "access_key: AKIAIOSFODNN7EXAMPLE"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL009" for f in findings)


def test_fires_for_github_pat():
    rule = _rule()
    fake_token = "ghp_" + "a" * 36
    record = make_record(messages=[{"role": "user", "content": f"token={fake_token}"}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL009" for f in findings)


def test_fires_for_bearer_token():
    rule = _rule()
    record = make_record(messages=[{"role": "user", "content": "Authorization: Bearer " + "x" * 40}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL009" for f in findings)


def test_fires_for_pem_header():
    rule = _rule()
    record = make_record(messages=[{"role": "user", "content": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIB..."}])
    findings = rule.check(record, Session())
    assert any(f.rule_id == "TL009" for f in findings)


def test_silent_for_clean_message():
    rule = _rule()
    record = make_record(messages=[{"role": "user", "content": "What is the capital of France?"}])
    findings = rule.check(record, Session())
    assert findings == []


def test_finding_does_not_echo_secret():
    rule = _rule()
    fake_key = "sk-" + "s" * 48
    record = make_record(messages=[{"role": "user", "content": f"key={fake_key}"}])
    findings = rule.check(record, Session())
    assert findings
    for f in findings:
        assert fake_key not in f.message
        assert fake_key not in f.suggestion


def test_severity_is_error():
    rule = _rule()
    from token_lens.rules._base import Severity
    fake_key = "sk-" + "a" * 48
    record = make_record(messages=[{"role": "user", "content": fake_key}])
    findings = rule.check(record, Session())
    assert findings
    assert all(f.severity == Severity.ERROR for f in findings)


def test_fires_at_pre_phase():
    from token_lens.rules.secret_in_prompt import SecretInPromptRule
    assert SecretInPromptRule().phase == "pre"
