# Implementation Plan — Enterprise Rules TL008–TL015
**Date:** 2026-07-24  
**Spec:** `docs/superpowers/specs/2026-07-24-enterprise-rules-design.md`  
**Goal:** Add 8 enterprise-grade detection rules. All follow TDD — test written first, verified failing, then implementation.

**Global constraints:** DRY. YAGNI. TDD. Each task has its own red-green-refactor cycle. No production code before a failing test.

---

## Task 1 — TL008: PII in prompt

### Files
- Write first: `token_lens/tests/rules/test_tl008_pii_in_prompt.py`
- Then: `token_lens/rules/pii_in_prompt.py`

### Test cases (write these first, verify they FAIL)
```python
# Fire cases
def test_fires_for_email_in_user_message()
def test_fires_for_phone_number_in_user_message()
def test_fires_for_credit_card_in_user_message()
def test_fires_for_ssn_in_user_message()
def test_fires_for_ip_address_in_system_message()
def test_fires_for_pii_in_tool_message()

# No-fire cases
def test_silent_for_clean_message()
def test_silent_for_assistant_role_by_default()
def test_finding_message_does_not_contain_matched_text()  # privacy invariant
```

### Implementation (after tests fail)
```python
# token_lens/rules/pii_in_prompt.py
import re
from ._base import Rule, Finding, Severity

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email address",   re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')),
    ("phone number",    re.compile(r'(\+?1?\s?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})')),
    ("credit card",     re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b')),
    ("SSN",             re.compile(r'\b(?!000|666|9\d{2})\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b')),
    ("IP address",      re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')),
]

class PIIInPromptRule(Rule):
    rule_id = "TL008"
    phase = "pre"   # fire before the call — block before sending

    def __init__(self, check_roles: set[str] | None = None) -> None:
        self._roles = check_roles or {"user", "system", "tool"}
        self._fired_call_ids: set = set()

    def check(self, record, session) -> list[Finding]:
        findings = []
        seen_types: set[str] = set()
        for msg in record.messages:
            role = msg.get("role", "")
            if role not in self._roles:
                continue
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue
            for pii_type, pattern in _PATTERNS:
                if pii_type in seen_types:
                    continue
                if pattern.search(content):
                    seen_types.add(pii_type)
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        severity=Severity.ERROR,
                        call_id=record.call_id,
                        message=f"Possible {pii_type} detected in role:{role} message.",
                        suggestion=(
                            f"Remove or anonymize {pii_type} before sending to the LLM provider. "
                            "Under GDPR/CCPA, personal data must not be sent to external processors "
                            "without explicit consent and a Data Processing Agreement. "
                            "Consider a PII scrubber (Presidio, AWS Comprehend) in your pipeline."
                        ),
                    ))
        return findings
```

### Verify
```bash
.venv/bin/pytest token_lens/tests/rules/test_tl008_pii_in_prompt.py -v
# Expected: all tests pass
.venv/bin/pytest token_lens/tests/ -q
# Expected: 54 + N new tests all pass
```

---

## Task 2 — TL009: Secret/key in prompt

### Files
- Write first: `token_lens/tests/rules/test_tl009_secret_in_prompt.py`
- Then: `token_lens/rules/secret_in_prompt.py`

### Test cases
```python
def test_fires_for_openai_key()          # "sk-" + "a"*48
def test_fires_for_anthropic_key()       # "sk-ant-" + "a"*90
def test_fires_for_aws_access_key()      # "AKIA" + "A"*16
def test_fires_for_github_pat()          # "ghp_" + "a"*36
def test_fires_for_bearer_token()        # "Bearer " + "a"*30
def test_fires_for_pem_header()
def test_silent_for_clean_message()
def test_finding_does_not_echo_secret()  # privacy invariant
```

### Implementation pattern (same structure as TL008)
```python
_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("OpenAI API key",     re.compile(r'sk-[A-Za-z0-9]{20,}')),
    ("Anthropic API key",  re.compile(r'sk-ant-[A-Za-z0-9\-]{20,}')),
    ("AWS access key",     re.compile(r'AKIA[0-9A-Z]{16}')),
    ("GitHub token",       re.compile(r'gh[pousr]_[A-Za-z0-9]{36,}')),
    ("Bearer token",       re.compile(r'Bearer\s+[A-Za-z0-9+/=._\-]{20,}')),
    ("PEM private key",    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
]
```
Phase: `pre`. Severity: ERROR.

---

## Task 3 — TL010: Unversioned model alias

### Files
- `token_lens/tests/rules/test_tl010_unversioned_model.py`
- `token_lens/rules/unversioned_model.py`

### Test cases
```python
def test_fires_for_gpt4o_alias()           # model="gpt-4o"
def test_fires_for_claude_sonnet_alias()   # model="claude-3-5-sonnet"
def test_silent_for_pinned_model()         # model="gpt-4o-2024-11-20"
def test_fires_once_per_model_name()       # same alias × 3 calls → fires once
def test_silent_for_unknown_model()        # unknown names not flagged
```

### Implementation
```python
_UNVERSIONED_ALIASES = frozenset({
    "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
    "claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku",
    "claude-3-5-haiku", "claude-sonnet-4", "claude-opus-4",
    "openai/gpt-4o", "openai/gpt-4-turbo",
    "anthropic/claude-3.5-sonnet", "anthropic/claude-3-haiku",
})
```
Phase: `post`. Severity: WARNING. Fire-once per alias.

---

## Task 4 — TL011: Tool result bloat

### Files
- `token_lens/tests/rules/test_tl011_tool_result_bloat.py`
- `token_lens/rules/tool_result_bloat.py`

### Test cases
```python
def test_fires_for_large_tool_result()     # role=tool, content > threshold
def test_silent_for_small_tool_result()
def test_silent_for_non_tool_message()
def test_uses_config_threshold()
```

### Implementation
Count tokens in `role="tool"` messages using `_tokenizer.count_tokens()`. Phase: `post`.

---

## Task 5 — TL012: Excessive tool definitions

### Files
- `token_lens/tests/rules/test_tl012_excessive_tools.py`
- `token_lens/rules/excessive_tools.py`

### Test cases
```python
def test_fires_for_too_many_tools()        # raw_kwargs["tools"] has 20 items
def test_silent_for_acceptable_count()     # 10 tools
def test_checks_functions_key_too()        # legacy "functions" kwarg
def test_silent_when_no_tools()
def test_uses_config_threshold()
```

Phase: `pre`. Severity: WARNING.

---

## Task 6 — TL013: Missing response_format

### Files
- `token_lens/tests/rules/test_tl013_missing_response_format.py`
- `token_lens/rules/missing_response_format.py`

### Test cases
```python
def test_fires_when_json_requested_without_format()
def test_silent_when_response_format_set()
def test_silent_when_no_json_keywords()
def test_fires_once_per_unique_system_prompt()
```

Keywords to detect: `"output JSON"`, `"return JSON"`, `"JSON format"`, `"as a JSON"`, `"valid JSON"`, `"respond with JSON"`, `"in JSON"`.
Phase: `pre`. Severity: INFO.

---

## Task 7 — TL014: Cost spike detection

### Files
- `token_lens/tests/rules/test_tl014_cost_spike.py`
- `token_lens/rules/cost_spike.py`

### Test cases
```python
def test_fires_when_call_is_outlier()         # session mean=100, call=400
def test_silent_below_min_calls()             # < 5 calls in session
def test_silent_for_normal_variation()        # 2× mean is fine
def test_fires_on_each_anomalous_call()       # two spikes → two findings
def test_uses_config_thresholds()
```

Phase: `post`. Severity: WARNING.

---

## Task 8 — TL015: n > 1 completions

### Files
- `token_lens/tests/rules/test_tl015_n_completions.py`
- `token_lens/rules/n_completions.py`

### Test cases
```python
def test_fires_when_n_is_2()
def test_fires_when_n_is_5()
def test_silent_when_n_is_1()
def test_silent_when_n_is_absent()
```

Phase: `pre`. Severity: INFO. Stateless — no session needed.

---

## Task 9 — Wire everything up

### Files to modify
- `token_lens/rules/__init__.py` — export 8 new classes
- `token_lens/_analyzer.py` — register in `_build_rules()`
- `token_lens/_config.py` — add 5 new fields

```python
# _config.py additions
pii_check_roles: set[str] = field(default_factory=lambda: {"user", "system", "tool"})
tool_result_token_threshold: int = 500
max_tools_per_call: int = 15
spike_min_calls: int = 5
spike_multiplier: float = 3.0
```

### Verify
```bash
.venv/bin/pytest token_lens/tests/ -v
# Expected: 54 + ~40 new tests, all pass
```

---

## Task 10 — Update docs

- `CONTEXT.md`: version → 0.2.0, rule table (+8 rows), file reference (+16 files), known limitations (update), changelog entry
- `README.md`: detection rules table (+8 rows)

---

## Final verification
```bash
.venv/bin/pytest token_lens/tests/ -v --tb=short
# Must show: all tests passed, 0 failures
```
