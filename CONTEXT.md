# token-lens — Project Context

> **Maintainance rule:** Every time code is changed in this project, `CONTEXT.md` must be updated in the same session. The sections that change most often are: [Current Version](#current-version), [File Reference](#file-reference), [Detection Rules](#detection-rules), [Changelog](#changelog), and [Known Limitations](#known-limitations). See [CLAUDE.md](CLAUDE.md) for the update protocol.

---

## Current Version

| Field | Value |
|---|---|
| Version | `0.2.0` |
| Python | `>=3.12` |
| Mandatory deps | **none** |
| Test count | 106 passing |
| Last updated | 2026-07-24 |

---

## What This Project Is

`token-lens` is a **local, zero-cloud Python middleware** that wraps your existing LLM SDK client, intercepts every `chat.completions.create()` or `messages.create()` call, and prints actionable token-efficiency coaching to `stderr` during development.

**The gap it fills:** Observability tools (Helicone, AgentOps, LangSmith) count tokens via cloud services. token-lens detects *why* tokens are wasted and gives code-level suggestions — locally, with no data leaving the machine.

**Design principle:** One-line migration. No accounts. No network calls. No mandatory dependencies.

---

## Architecture

### Interception model: SDK wrapper (not proxy)

```
user code:  client.chat.completions.create(**kwargs)
                     ↓
TokenLens.chat  →  InstrumentedChat.completions  →  InstrumentedCompletions.create(**kwargs)
                                                          ↓  pre-call rules (e.g. TL006)
                                                          ↓  self._completions.create(**kwargs)  ← real SDK call, kwargs untouched
                                                          ↓  post-call rules (e.g. TL001, TL004)
                                                          →  return response unchanged
```

For the native Anthropic SDK the interception point is `client.messages.create()` instead:

```
AnthropicTokenLens.messages  →  InstrumentedAnthropicMessages.create(**kwargs)
```

### Data flow per call

```
create(**kwargs)
  │
  ├── build CallRecord (call_id, timestamp, model, messages, raw_kwargs)
  │
  ├── Analyzer.analyze_pre_call()
  │     └── run phase="pre" rules → list[Finding]
  │
  ├── Reporter.emit_findings()   ← writes to stderr, never stdout
  │
  ├── real SDK call → response
  │
  ├── _normalize_usage(response) → NormalizedUsage (provider-agnostic)
  │
  ├── Session.add_call(record)   ← thread-safe, updates indexes
  │
  ├── Analyzer.analyze_post_call()
  │     └── run phase="post" rules → list[Finding]
  │
  ├── Reporter.emit_findings()
  │
  └── return response            ← exact object from real SDK, unmodified
```

### Key design decisions

| Decision | Reason |
|---|---|
| Wrapper over proxy | Zero HTTP overhead; full Python kwargs access; LangGraph-compatible; single language |
| `__getattr__` delegation | All non-instrumented endpoints (`.embeddings`, `.models`, `.files`) pass through transparently |
| `chat` as `@property` (not `@cached_property`) | Stores `InstrumentedChat` as `self._chat_instrument`; Python resolves it before `__getattr__` fallback |
| `NormalizedUsage` dataclass | Unifies `prompt_tokens`/`completion_tokens` (OpenAI) and `input_tokens`/`output_tokens` (Anthropic) so all rules and the reporter work identically |
| `stderr` only | Never interrupts `stdout` pipelines |
| `atexit` for session summary | Fires automatically at process exit; can be disabled with `Config(auto_report_on_exit=False)` |
| Thread-safe `Session` | `threading.Lock` on `add_call()` — LangGraph can run nodes concurrently |
| Stream bypass | `stream=True` calls are forwarded directly; can't inspect a generator without consuming it |
| Zero mandatory deps | Package installs on any machine with Python ≥3.12 without requiring openai/anthropic SDK |

---

## File Reference

### Root

| File | Purpose |
|---|---|
| [pyproject.toml](pyproject.toml) | Build config, zero mandatory deps, optional extras |
| [README.md](README.md) | User-facing documentation (setup, usage, config reference, privacy statement) |
| [CONTEXT.md](CONTEXT.md) | This file — architecture record for developers and AI assistants |
| [CLAUDE.md](CLAUDE.md) | AI assistant instructions: superpowers methodology, update protocol, enterprise standards, production-readiness checklist |
| [LICENSE](LICENSE) | MIT |
| [.gitignore](.gitignore) | Standard Python + venv + IDE ignores |
| `docs/superpowers/specs/` | Spec files output by the `brainstorming` superpowers skill (`YYYY-MM-DD-<topic>-design.md`) |
| `docs/superpowers/plans/` | Plan files output by the `writing-plans` superpowers skill (`YYYY-MM-DD-<feature>.md`) |

### `token_lens/` package

| File | Exports / Role |
|---|---|
| [`__init__.py`](token_lens/__init__.py) | Public API: `TokenLens`, `AnthropicTokenLens`, `Config`, `TokenLensCallbackHandler` |
| [`_config.py`](token_lens/_config.py) | `Config` dataclass — all thresholds and toggles |
| [`_session.py`](token_lens/_session.py) | `NormalizedUsage`, `CallRecord`, `Session` (thread-safe call log + indexes) |
| [`_wrapper.py`](token_lens/_wrapper.py) | `TokenLens` — proxy for OpenAI-compatible SDKs |
| [`_chat.py`](token_lens/_chat.py) | `InstrumentedChat`, `InstrumentedCompletions`, `_normalize_usage()` |
| [`_anthropic_wrapper.py`](token_lens/_anthropic_wrapper.py) | `AnthropicTokenLens` — proxy for native `anthropic` SDK |
| [`_anthropic_messages.py`](token_lens/_anthropic_messages.py) | `InstrumentedAnthropicMessages`, `_normalize_anthropic_usage()`, `_anthropic_to_messages()` |
| [`_analyzer.py`](token_lens/_analyzer.py) | `Analyzer` — instantiates and runs all rules pre/post call |
| [`_reporter.py`](token_lens/_reporter.py) | `Reporter` — ANSI color terminal output + session summary |
| [`_tokenizer.py`](token_lens/_tokenizer.py) | `count_tokens()`, `count_messages_tokens()` — tiktoken or 4-char fallback |
| [`langgraph_integration.py`](token_lens/langgraph_integration.py) | `TokenLensCallbackHandler` — LangChain `BaseCallbackHandler` subclass |
| [`py.typed`](token_lens/py.typed) | PEP 561 marker — declares this a typed package |

### `token_lens/rules/`

| File | Rule ID | Phase | What it detects |
|---|---|---|---|
| [`_base.py`](token_lens/rules/_base.py) | — | — | `Rule` ABC, `Finding` dataclass, `Severity` enum |
| [`static_system_prompt.py`](token_lens/rules/static_system_prompt.py) | TL001 | post | Same system prompt ≥ N consecutive calls |
| [`unbounded_history.py`](token_lens/rules/unbounded_history.py) | TL002 | post | History growing past threshold |
| [`duplicate_prompt.py`](token_lens/rules/duplicate_prompt.py) | TL003 | post | Identical message list sent ≥ 2 times |
| [`model_overkill.py`](token_lens/rules/model_overkill.py) | TL004 | post | High-tier model, short output, single message |
| [`long_system_prompt.py`](token_lens/rules/long_system_prompt.py) | TL005 | post | System prompt > token threshold |
| [`missing_max_tokens.py`](token_lens/rules/missing_max_tokens.py) | TL006 | **pre** | No `max_tokens` / `max_completion_tokens` in kwargs |
| [`redundant_context.py`](token_lens/rules/redundant_context.py) | TL007 | post | High Jaccard overlap between two long messages |
| [`pii_in_prompt.py`](token_lens/rules/pii_in_prompt.py) | TL008 | **pre** | PII (email, phone, CC, SSN, IP) in user/system/tool messages |
| [`secret_in_prompt.py`](token_lens/rules/secret_in_prompt.py) | TL009 | **pre** | Credentials / API keys in any message role |
| [`unversioned_model.py`](token_lens/rules/unversioned_model.py) | TL010 | post | Model is an unversioned alias (fires once per alias per session) |
| [`tool_result_bloat.py`](token_lens/rules/tool_result_bloat.py) | TL011 | post | Tool/function result exceeds token threshold |
| [`excessive_tools.py`](token_lens/rules/excessive_tools.py) | TL012 | **pre** | More than N tools registered in a single call |
| [`missing_response_format.py`](token_lens/rules/missing_response_format.py) | TL013 | **pre** | JSON output requested in system prompt but `response_format` not set |
| [`cost_spike.py`](token_lens/rules/cost_spike.py) | TL014 | post | Call token count is ≥ N× the session mean (after enough baseline calls) |
| [`n_completions.py`](token_lens/rules/n_completions.py) | TL015 | **pre** | `n > 1` completions requested |

### `token_lens/tests/`

| File | What it tests |
|---|---|
| [`conftest.py`](token_lens/tests/conftest.py) | Shared fixtures: `make_usage()` → `NormalizedUsage`, `make_response()`, `make_anthropic_response()`, `make_record()` |
| [`test_wrapper.py`](token_lens/tests/test_wrapper.py) | `TokenLens` passthrough, delegation, streaming bypass, `enabled=False` |
| [`test_anthropic_wrapper.py`](token_lens/tests/test_anthropic_wrapper.py) | `AnthropicTokenLens` passthrough, TL001/TL006 via Anthropic kwargs, usage normalization |
| [`test_session.py`](token_lens/tests/test_session.py) | `Session` add/total/by_model, hash tracking |
| [`test_analyzer.py`](token_lens/tests/test_analyzer.py) | Analyzer pre/post routing |
| [`test_reporter.py`](token_lens/tests/test_reporter.py) | Stderr output, empty session, totals |
| [`test_tokenizer.py`](token_lens/tests/test_tokenizer.py) | Token counting, message overhead formula |
| [`test_integration.py`](token_lens/tests/test_integration.py) | End-to-end: TL006 fires, TL001 fires after 3 calls, session summary |
| `tests/rules/test_tl00{1..7}_*.py` | Per-rule fire / no-fire cases (TL001–TL007) |
| `tests/rules/test_tl008_pii_in_prompt.py` | PII detection + privacy invariant (never echo matched text) |
| `tests/rules/test_tl009_secret_in_prompt.py` | Secret/credential detection + privacy invariant |
| `tests/rules/test_tl010_unversioned_model.py` | Unversioned alias detection, fire-once per alias |
| `tests/rules/test_tl011_tool_result_bloat.py` | Tool result size threshold |
| `tests/rules/test_tl012_excessive_tools.py` | tools/functions count threshold |
| `tests/rules/test_tl013_missing_response_format.py` | JSON keyword detection, fire-once per system prompt hash |
| `tests/rules/test_tl014_cost_spike.py` | Outlier detection vs session mean, fires on each anomalous call |
| `tests/rules/test_tl015_n_completions.py` | n>1 completions detection |

---

## Detection Rules

### Rule anatomy

Every rule implements the `Rule` ABC:

```python
class Rule(ABC):
    rule_id: str       # e.g. "TL006"
    phase: str         # "pre" (before the SDK call) or "post" (after)
    def check(self, record: CallRecord, session: Session) -> list[Finding]: ...
```

`Finding` is a frozen dataclass: `(rule_id, severity, message, suggestion, call_id)`.

Rules that should only fire **once per unique trigger** maintain an internal `_fired_hashes: set[str]` to prevent repeat noise.

### Rule table

| ID | Severity | Phase | Default trigger | Key config field |
|---|---|---|---|---|
| TL001 | WARNING | post | System prompt text identical across ≥ 3 calls | `static_prompt_repeat_threshold` |
| TL002 | WARNING | post | Non-system messages > 20 AND history growing across last 3 calls | `history_message_threshold` |
| TL003 | WARNING | post | `sha256(messages)` seen ≥ 2 times | — (fires on second occurrence) |
| TL004 | INFO | post | Model in `high_tier_models` AND completion_tokens < 80 AND single non-system message | `high_tier_models`, `simple_task_completion_token_threshold` |
| TL005 | INFO | post | System prompt token count > 500 | `system_prompt_token_threshold` |
| TL006 | WARNING | **pre** | `max_tokens` and `max_completion_tokens` both absent or `None` | — |
| TL007 | INFO | post | Jaccard(word sets of two messages) > 0.70, both messages ≥ 50 words | `redundant_context_jaccard_threshold`, `redundant_context_min_words` |
| TL008 | ERROR | **pre** | PII pattern (email/phone/CC/SSN/IP) in role=user/system/tool | `pii_check_roles` |
| TL009 | ERROR | **pre** | Credential pattern (API key, Bearer token, PEM key) in any role | — (all roles) |
| TL010 | WARNING | post | Model string is a known unversioned alias; fires once per alias per session | — |
| TL011 | WARNING | post | `role=tool` message content exceeds token threshold | `tool_result_token_threshold` |
| TL012 | WARNING | **pre** | Count of `tools` or `functions` in kwargs exceeds threshold | `max_tools_per_call` |
| TL013 | WARNING | **pre** | System prompt contains JSON keywords but `response_format` not set; fires once per unique system prompt | — |
| TL014 | WARNING | post | Call's total tokens ≥ `spike_multiplier × session_mean`, after ≥ `spike_min_calls` baseline calls; fires per anomalous call | `spike_min_calls`, `spike_multiplier` |
| TL015 | WARNING | **pre** | `n > 1` in kwargs | — |

### To add a new rule

1. Create `token_lens/rules/tl00N_name.py` implementing the `Rule` ABC
2. Export it from `token_lens/rules/__init__.py`
3. Instantiate it in `_analyzer.py` `_build_rules()`
4. Add any new config fields to `_config.py`
5. Write tests in `token_lens/tests/rules/test_tl00N_name.py`
6. Update the rule tables in this file and in `README.md`

---

## Supported Providers

| Provider | SDK | Wrapper class | Interception point |
|---|---|---|---|
| OpenAI | `openai` | `TokenLens` | `client.chat.completions.create()` |
| OpenRouter | `openai` (compat) | `TokenLens` | same |
| Groq | `groq` | `TokenLens` | same |
| Together AI | `openai` (compat) | `TokenLens` | same |
| Azure OpenAI | `openai` | `TokenLens` | same |
| Ollama | `openai` (compat) | `TokenLens` | same |
| Perplexity | `openai` (compat) | `TokenLens` | same |
| Mistral | `openai` (compat) | `TokenLens` | same |
| Anthropic | `anthropic` (native) | `AnthropicTokenLens` | `client.messages.create()` |
| LangGraph/LangChain | any | `TokenLensCallbackHandler` | `on_chat_model_start` / `on_llm_end` |

**Usage normalization:**
- OpenAI-compat: `response.usage.prompt_tokens` / `response.usage.completion_tokens`
- Anthropic native: `response.usage.input_tokens` / `response.usage.output_tokens`
- Both normalize to `NormalizedUsage(prompt_tokens, completion_tokens, total_tokens)`

---

## Config Reference

All fields live in `token_lens/_config.py` as a `@dataclass`.

```python
@dataclass
class Config:
    enabled: bool = True
    no_color: bool = False
    auto_report_on_exit: bool = True
    static_prompt_repeat_threshold: int = 3
    history_message_threshold: int = 20
    high_tier_models: frozenset[str] = ...   # gpt-4o, claude-3.5-sonnet, etc.
    simple_task_completion_token_threshold: int = 80
    system_prompt_token_threshold: int = 500
    redundant_context_jaccard_threshold: float = 0.70
    redundant_context_min_words: int = 50
    pii_check_roles: set[str] = {"user", "system", "tool"}  # TL008
    tool_result_token_threshold: int = 500                   # TL011
    max_tools_per_call: int = 15                             # TL012
    spike_min_calls: int = 5                                 # TL014
    spike_multiplier: float = 3.0                            # TL014
    disabled_rules: set[str] = field(default_factory=set)
```

Environment variables: `NO_COLOR`, `TOKEN_LENS_NO_COLOR` — both disable ANSI output.

---

## Known Limitations

| Limitation | Impact | Planned fix |
|---|---|---|
| Streaming calls (`stream=True`) bypass all analysis | Rules don't fire on streamed responses | v0.2: consume chunks, reconstruct usage from final delta |
| `TokenLensCallbackHandler` does not populate `NormalizedUsage` on `CallRecord` | Session summary shows 0 tokens for LangGraph calls | v0.2: parse `usage_metadata` from LLMResult |
| TL004 only fires for single-message calls | Multi-turn overkill not detected | Future rule variant |
| No async support (`AsyncOpenAI`, `AsyncAnthropic`) | Async clients not instrumented | v0.2: `AsyncTokenLens` and `AsyncAnthropicTokenLens` |
| tiktoken fallback (4 chars ≈ 1 token) is imprecise | TL005 token count off by ±20% without tiktoken installed | Always install `token-lens[accurate-counting]` |

---

## Dependency Graph

```
token_lens
├── _wrapper.py           → _chat.py, _session.py, _analyzer.py, _reporter.py, _config.py
├── _anthropic_wrapper.py → _anthropic_messages.py, _session.py, _analyzer.py, _reporter.py, _config.py
├── _chat.py              → _session.py (NormalizedUsage, CallRecord, Session)
├── _anthropic_messages.py→ _session.py
├── _analyzer.py          → rules/*, _config.py
├── _reporter.py          → _config.py, rules/_base.py (Finding, Severity)
├── _tokenizer.py         → (optional) tiktoken
├── langgraph_integration.py → _session.py, _analyzer.py, _reporter.py, _config.py
└── rules/
    ├── _base.py          → (stdlib only)
    ├── static_system_prompt.py  → _base.py
    ├── unbounded_history.py     → _base.py
    ├── duplicate_prompt.py      → _base.py
    ├── model_overkill.py        → _base.py
    ├── long_system_prompt.py    → _base.py, _tokenizer.py
    ├── missing_max_tokens.py    → _base.py
    ├── redundant_context.py     → _base.py
    ├── pii_in_prompt.py         → _base.py
    ├── secret_in_prompt.py      → _base.py
    ├── unversioned_model.py     → _base.py
    ├── tool_result_bloat.py     → _base.py, _tokenizer.py
    ├── excessive_tools.py       → _base.py
    ├── missing_response_format.py → _base.py
    ├── cost_spike.py            → _base.py
    └── n_completions.py         → _base.py
```

---

## Changelog

### v0.2.0 — 2026-07-24

**Added: Enterprise rules (TL008–TL015)**
- `TL008` `PIIInPromptRule` — pre-call, detects email/phone/credit card/SSN/IP in user, system, and tool messages. Privacy invariant: finding message never echoes matched text.
- `TL009` `SecretInPromptRule` — pre-call, detects OpenAI/Anthropic/AWS/GitHub keys, Bearer tokens, PEM headers in any message role. Same privacy invariant.
- `TL010` `UnversionedModelRule` — post-call, warns when an unversioned model alias (e.g. `gpt-4o`, `claude-3-5-sonnet`) is used; fires once per alias per session.
- `TL011` `ToolResultBloatRule` — post-call, flags `role=tool` message content exceeding `tool_result_token_threshold` (default 500 tokens).
- `TL012` `ExcessiveToolsRule` — pre-call, fires when `tools` or `functions` count exceeds `max_tools_per_call` (default 15).
- `TL013` `MissingResponseFormatRule` — pre-call, detects JSON-output keywords in system prompt without `response_format` kwarg; fires once per unique system prompt hash.
- `TL014` `CostSpikeRule` — post-call, fires when a call's total tokens ≥ `spike_multiplier × prior_mean` after ≥ `spike_min_calls` baseline calls; fires on every anomalous call (not deduplicated).
- `TL015` `NCompletionsRule` — pre-call, fires when `n > 1` is requested.
- `_config.py`: 5 new fields: `pii_check_roles`, `tool_result_token_threshold`, `max_tools_per_call`, `spike_min_calls`, `spike_multiplier`
- 52 new tests across 8 new test files — all passing (106 total)

### v0.1.1 — 2026-07-23

**Added:**
- `token_lens/py.typed` — PEP 561 marker, declares this a typed package
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — directory structure expected by the superpowers methodology for spec and plan files
- Superpowers methodology section in `CLAUDE.md` — install command, skill table, hard gates
- Enterprise production-readiness checklist in `CLAUDE.md` — must-have / should-have / nice-to-have tiers
- Current production-readiness status table in `CLAUDE.md`

**Fixed:**
- `pyproject.toml`: classifiers were under an invalid `[project.classifiers]` TOML section — moved to a plain list key under `[project]` (was silently ignored by hatchling, would fail PyPI validation)
- `pyproject.toml`: placeholder `your-username` in project URLs replaced with real repo path
- `token_lens/rules/static_system_prompt.py`: `import hashlib` was inside the `check()` method body — moved to module level
- `token_lens/langgraph_integration.py`: `on_llm_end` was setting stale `_prompt_token_count` / `_completion_token_count` fields that no longer exist on `CallRecord` — now correctly constructs and assigns a `NormalizedUsage` instance

**Changed:**
- `CLAUDE.md` fully rewritten: now includes superpowers methodology integration, enterprise coding standards, TDD-first rule-addition workflow, production-readiness checklist, and explicit DO NOT list

### v0.1.0 — 2026-07-23 (initial build)

**Implemented:**
- `TokenLens` wrapper for all OpenAI-compatible SDKs
- `AnthropicTokenLens` wrapper for native `anthropic` SDK
- `TokenLensCallbackHandler` for LangGraph / LangChain
- `NormalizedUsage` dataclass — provider-agnostic usage normalization
- 7 detection rules (TL001–TL007) with per-rule fire-once deduplication
- `Session` with thread-safe `add_call()`, system prompt index, prompt hash counter
- `Reporter` with ANSI color output to stderr; respects `NO_COLOR`
- `_tokenizer.py` with tiktoken integration and 4-char fallback
- `Config` dataclass with all thresholds configurable
- `pyproject.toml` with zero mandatory dependencies
- `README.md` with setup guide, config reference, privacy statement, enterprise pattern
- 54 tests passing (unit + integration)

---

## Quick Usage Reference

```python
# OpenAI / any OpenAI-compatible SDK (Groq, Together, OpenRouter, Azure, Ollama...)
from openai import OpenAI
from token_lens import TokenLens
client = TokenLens(OpenAI(api_key="...", base_url="..."))

# Native Anthropic SDK
import anthropic
from token_lens import AnthropicTokenLens
client = AnthropicTokenLens(anthropic.Anthropic(api_key="..."))

# LangGraph / LangChain
from token_lens import TokenLensCallbackHandler
handler = TokenLensCallbackHandler()
result = app.invoke(state, config={"callbacks": [handler]})
handler.session_report()

# Tune or silence rules
from token_lens import Config
client = TokenLens(OpenAI(...), Config(
    disabled_rules={"TL007"},
    static_prompt_repeat_threshold=5,
    enabled=False,   # production kill-switch
))
```
