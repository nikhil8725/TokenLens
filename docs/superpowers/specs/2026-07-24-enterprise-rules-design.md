# Enterprise Rule Coverage — Design Spec
**Date:** 2026-07-24  
**Status:** Approved for implementation  
**Target:** Customer-facing LLM products (GDPR/CCPA, public-facing chatbots, copilots, support agents)

---

## Problem

The current 7 rules (TL001–TL007) cover individual-call hygiene for a single developer. They catch ~30% of real enterprise failure modes. For production enterprise deployment, 8 additional failure patterns are undetected:

1. PII in prompt content (GDPR/CCPA compliance risk)
2. Secrets/API keys in prompt content (security incident risk)
3. Unversioned model alias in production (silent behavior change risk)
4. Tool result bloat (cost escalation in agent pipelines)
5. Excessive tool definitions per call (hidden per-call overhead)
6. Missing `response_format` for structured output (parsing failures + silent retries)
7. Anomalous cost spike detection (runaway context injection)
8. `n > 1` completions without being consumed (cost multiplier)

---

## Design decisions

### PII detection (TL008)
- **Regex-only, no ML/heuristics.** Regex gives zero false positives for well-defined formats. ML introduces probabilistic firing that would make the tool untrustworthy in CI pipelines.
- **Patterns to include (GDPR/CCPA scope — customer-facing):**
  - Email addresses
  - Phone numbers (E.164 and common regional formats)
  - Credit card numbers (Luhn-valid, major card prefixes)
  - Social Security Numbers / National ID formats (US SSN, generic 9-digit)
  - IP addresses (private + public, since they're PII under GDPR)
  - Passport number patterns
- **Scope:** Check all message content fields (system, user, assistant, tool). Not just user messages — RAG chunks injected into system prompts are a common vector.
- **Severity:** ERROR (not WARNING) — this is a compliance issue, not a best-practice suggestion.
- **Fire-once-per-type-per-call:** Report each PII type found once per call. Do not enumerate every occurrence — that would log the PII itself to stderr.
- **Privacy invariant:** The finding message must NEVER include the matched text. Only report: the type found, the role of the message it was found in, and the approximate position (first 50 chars of context with match redacted).

### Secret detection (TL009)
- **Patterns to include:**
  - OpenAI keys: `sk-[A-Za-z0-9]{48}`
  - Anthropic keys: `sk-ant-[A-Za-z0-9-]{90,}`
  - AWS access keys: `AKIA[0-9A-Z]{16}`
  - GitHub tokens: `ghp_[A-Za-z0-9]{36}`, `gho_`, `ghs_`, `github_pat_`
  - Generic Bearer tokens: `Bearer [A-Za-z0-9+/]{20,}`
  - PEM private key headers: `-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----`
  - Generic high-entropy strings: 40+ character hex or base64 sequences adjacent to key-like keywords (`api_key`, `secret`, `token`, `password`, `credential`)
- **Severity:** ERROR — always blocks if found.
- **Privacy invariant:** Same as TL008 — never echo the matched secret. Report: key type, role, redacted location only.

### Unversioned model alias (TL010)
- **Detection:** Model string is a known unversioned alias (e.g., `"gpt-4o"`, `"claude-3-5-sonnet"`, `"gpt-4-turbo"`) with no date suffix.
- **Date suffix patterns:** `-YYYYMMDD`, `-YYYY-MM-DD`, `-preview`, `-latest` count as versioned (though `-latest` is itself unstable — warn about that too).
- **Severity:** WARNING.
- **Fire-once-per-model-name** per session.

### Tool result bloat (TL011)
- **Detection:** Any message with `role == "tool"` whose content exceeds `Config.tool_result_token_threshold` (default: 500 tokens).
- **Why 500:** Tool results over 500 tokens almost always contain unsummarized raw data. The median useful tool result (a structured API response with the relevant fields) is 50–150 tokens.
- **Severity:** WARNING.

### Excessive tool definitions (TL012)
- **Detection:** `len(raw_kwargs.get("tools") or raw_kwargs.get("functions") or [])` exceeds `Config.max_tools_per_call` (default: 15).
- **Token cost reality:** Each OpenAI function definition costs ~50–100 tokens in the prompt. 20 tools = ~1500 additional tokens per call.
- **Severity:** WARNING. Fire once per unique tool count crossing the threshold.

### Missing response_format (TL013)
- **Detection:** System prompt contains structured-output keywords ("output JSON", "return JSON", "JSON format", "as a JSON object", "valid JSON", "respond with JSON") AND `response_format` is absent from `raw_kwargs`.
- **Severity:** INFO.
- **Fire-once per unique system prompt hash.**

### Cost spike detection (TL014)
- **Detection:** After at least `Config.spike_min_calls` (default: 5) calls in the session, if the current call's `total_tokens` exceeds `session_mean_tokens * Config.spike_multiplier` (default: 3.0×), fire.
- **Severity:** WARNING.
- **Fires on every anomalous call** (not once-per-session) — each spike is independent.

### n > 1 completions (TL015)
- **Detection:** `raw_kwargs.get("n", 1) > 1`.
- **Severity:** INFO. Simple, no session state needed.

---

## Config additions

```python
# TL008 / TL009 — PII and secret detection
pii_check_roles: set[str] = field(default_factory=lambda: {"user", "system", "tool"})
# Roles to scan. Exclude "assistant" by default — we don't control model output.

# TL011 — tool result bloat
tool_result_token_threshold: int = 500

# TL012 — excessive tools
max_tools_per_call: int = 15

# TL014 — cost spike
spike_min_calls: int = 5
spike_multiplier: float = 3.0
```

---

## Privacy invariants (non-negotiable)

These apply to TL008 and TL009 and cannot be relaxed:

1. **Zero data in Finding messages.** The `message` and `suggestion` fields of a `Finding` must never contain the matched PII or secret string, or any substring of it.
2. **Redacted context only.** If showing location is useful, show: `"...role:user, ~char 45..."` — never the surrounding text.
3. **No logging to files.** token-lens writes only to stderr in the current process. PII rules must not write to any file, even temp files.
4. **test_tl008 and test_tl009 must not contain real PII in test fixtures.** Use format-valid but semantically fake values (e.g., `"test@example.com"`, `"sk-" + "a" * 48`).

---

## File plan

| New file | Rule |
|---|---|
| `token_lens/rules/pii_in_prompt.py` | TL008 |
| `token_lens/rules/secret_in_prompt.py` | TL009 |
| `token_lens/rules/unversioned_model.py` | TL010 |
| `token_lens/rules/tool_result_bloat.py` | TL011 |
| `token_lens/rules/excessive_tools.py` | TL012 |
| `token_lens/rules/missing_response_format.py` | TL013 |
| `token_lens/rules/cost_spike.py` | TL014 |
| `token_lens/rules/n_completions.py` | TL015 |
| `token_lens/tests/rules/test_tl008_pii_in_prompt.py` | TL008 |
| `token_lens/tests/rules/test_tl009_secret_in_prompt.py` | TL009 |
| `token_lens/tests/rules/test_tl010_unversioned_model.py` | TL010 |
| `token_lens/tests/rules/test_tl011_tool_result_bloat.py` | TL011 |
| `token_lens/tests/rules/test_tl012_excessive_tools.py` | TL012 |
| `token_lens/tests/rules/test_tl013_missing_response_format.py` | TL013 |
| `token_lens/tests/rules/test_tl014_cost_spike.py` | TL014 |
| `token_lens/tests/rules/test_tl015_n_completions.py` | TL015 |

Modified files:
- `token_lens/rules/__init__.py` — export 8 new classes
- `token_lens/_analyzer.py` — register 8 new rules in `_build_rules()`
- `token_lens/_config.py` — add 5 new config fields
- `CONTEXT.md` — rule table, file reference, changelog
- `README.md` — detection rules table
