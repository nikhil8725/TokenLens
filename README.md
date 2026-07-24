# token-lens

**Local LLM token efficiency middleware.**  
Wraps your existing LLM client with one line of code. Detects token waste patterns and prints actionable suggestions to your terminal — during development, with zero cloud dependency and zero data leaving your machine.

```
⚠ [token-lens TL006] No max_tokens set on call to 'openai/gpt-4o-mini'.
  → Without a cap, a misbehaving prompt can generate thousands of tokens and spike costs.

⚠ [token-lens TL001] System prompt is identical across 3+ consecutive calls (~120 tokens each).
  → Use prompt caching. Potential saving: ~80% of system prompt tokens.

── token-lens session summary ──
  calls:             3
  prompt tokens:     612
  completion tokens: 187
  total tokens:      799
  openai/gpt-4o-mini: 3 call(s), 799 tokens
```

---

## Why token-lens?

Existing tools — Helicone, AgentOps, LangSmith, PromptLayer — are observability platforms: they **count** tokens via a cloud service. token-lens is different in three ways:

| | token-lens | Cloud tools |
|---|---|---|
| **Data leaves your machine** | Never | Yes |
| **Setup** | One line of code | Account + API key + proxy/SDK |
| **What it does** | Detects *why* tokens are wasted | Counts tokens that were spent |
| **Works offline** | Yes | No |
| **Enterprise deployment** | `pip install` on your server | Vendor agreement required |

---

## Supported providers

token-lens works with **any SDK that exposes a `chat.completions.create()` interface**, plus a dedicated adapter for the native Anthropic SDK.

| Provider | SDK | Wrapper |
|---|---|---|
| OpenAI | `openai` | `TokenLens` |
| OpenRouter | `openai` (compat) | `TokenLens` |
| Groq | `groq` | `TokenLens` |
| Together AI | `openai` (compat) | `TokenLens` |
| Azure OpenAI | `openai` | `TokenLens` |
| Ollama | `openai` (compat) | `TokenLens` |
| Perplexity | `openai` (compat) | `TokenLens` |
| Mistral | `openai` (compat) | `TokenLens` |
| Anthropic | `anthropic` (native) | `AnthropicTokenLens` |
| LangGraph / LangChain | any via callbacks | `TokenLensCallbackHandler` |

---

## Installation

### From PyPI (recommended)

```bash
pip install llm-token-lens
```

For accurate token counting (highly recommended):

```bash
pip install "token-lens[accurate-counting]"
```

For LangGraph / LangChain callback support:

```bash
pip install "token-lens[langgraph]"
```

Install everything at once:

```bash
pip install "token-lens[accurate-counting,langgraph]"
```

### From source

```bash
git clone https://github.com/nikhilbahalkar/llm-token-lens.git
cd llm-token-lens
pip install -e ".[accurate-counting,dev]"
```

---

## Quick start

### OpenAI / OpenAI-compatible providers

Change one line — everything else stays identical:

```python
from openai import OpenAI
from token_lens import TokenLens       # ← add this import

# Before:
# client = OpenAI(api_key="...", base_url="...")

# After:
client = TokenLens(OpenAI(api_key="...", base_url="..."))  # ← wrap it

# All existing call sites are unchanged:
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=256,
)
```

Works identically for **Groq, OpenRouter, Together AI, Azure OpenAI, Ollama**, and any other provider with an OpenAI-compatible SDK — just wrap the client.

### Anthropic

```python
import anthropic
from token_lens import AnthropicTokenLens   # ← use the dedicated adapter

client = AnthropicTokenLens(anthropic.Anthropic(api_key="..."))

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=256,
    messages=[{"role": "user", "content": "Hello!"}],
)
```

### LangGraph / LangChain

If you use `ChatOpenAI` or `init_chat_model` (rather than the raw OpenAI SDK), use the callback handler:

```python
from token_lens import TokenLensCallbackHandler

handler = TokenLensCallbackHandler()

# Pass as a callback to any LangGraph or LangChain invocation:
result = app.invoke(state, config={"callbacks": [handler]})

# Print the session summary manually (or it fires automatically at process exit):
handler.session_report()
```

---

## Configuration

Pass a `Config` object to tune or silence any rule:

```python
from token_lens import TokenLens, Config

client = TokenLens(
    OpenAI(...),
    Config(
        # Raise the system-prompt-repeat threshold from 3 to 5
        static_prompt_repeat_threshold=5,

        # Disable specific rules by ID
        disabled_rules={"TL007"},

        # Turn off ANSI colors (e.g. in CI)
        no_color=True,

        # Disable the automatic session summary at process exit
        auto_report_on_exit=False,

        # Turn off all analysis entirely (e.g. in production)
        enabled=False,
    ),
)
```

### Config reference

| Field | Default | Description |
|---|---|---|
| `enabled` | `True` | Master switch — set `False` in production |
| `no_color` | `False` | Disable ANSI colors in output |
| `auto_report_on_exit` | `True` | Print session summary when the process exits |
| `static_prompt_repeat_threshold` | `3` | Calls before TL001 fires |
| `history_message_threshold` | `20` | Non-system messages before TL002 fires |
| `high_tier_models` | (see below) | Model names considered "high tier" for TL004 |
| `simple_task_completion_token_threshold` | `80` | Completion tokens below which TL004 fires |
| `system_prompt_token_threshold` | `500` | Tokens above which TL005 fires |
| `redundant_context_jaccard_threshold` | `0.70` | Overlap ratio above which TL007 fires |
| `redundant_context_min_words` | `50` | Minimum message length for TL007 to apply |
| `pii_check_roles` | `{"user","system","tool"}` | Message roles to scan for PII (TL008) |
| `tool_result_token_threshold` | `500` | Token count above which TL011 fires |
| `max_tools_per_call` | `15` | Tool count above which TL012 fires |
| `spike_min_calls` | `5` | Minimum baseline calls before TL014 activates |
| `spike_multiplier` | `3.0` | Multiplier of session mean above which TL014 fires |
| `disabled_rules` | `set()` | Set of rule IDs to skip (e.g. `{"TL004", "TL007"}`) |

### Environment variables

| Variable | Effect |
|---|---|
| `NO_COLOR` | Disable ANSI colors (community standard) |
| `TOKEN_LENS_NO_COLOR` | Same as above, token-lens specific |

---

## Detection rules

| ID | Name | Phase | What triggers it | Suggestion |
|---|---|---|---|---|
| **TL001** | Static system prompt | post | Same system prompt ≥ N consecutive calls | Use prompt caching (OpenAI auto-caches >1024 tokens; Anthropic: `cache_control`) |
| **TL002** | Unbounded history | post | Non-system messages > 20 and growing | Use `trim_messages()` or add a summarization node |
| **TL003** | Duplicate prompt | post | Exact same message list sent ≥ 2 times | Add a result cache keyed on prompt hash |
| **TL004** | Model overkill | post | High-tier model, completion < 80 tokens, single message | Switch to a smaller/cheaper model for simple tasks |
| **TL005** | Long system prompt | post | System prompt > 500 tokens | Move static facts to retrieval; compress the prompt |
| **TL006** | Missing max_tokens | pre | Neither `max_tokens` nor `max_completion_tokens` set | Add `max_tokens=<expected upper bound>` |
| **TL007** | Redundant context | post | Two messages share >70% word overlap (>50 words each) | Deduplicate into the system prompt |
| **TL008** | PII in prompt | pre | Email, phone, credit card, SSN, or IP address in user/system/tool message | Remove or anonymize PII before sending to provider (GDPR/CCPA) |
| **TL009** | Secret in prompt | pre | API key, Bearer token, or PEM key detected in any message | Remove credential immediately; rotate any exposed key |
| **TL010** | Unversioned model | post | Unversioned model alias used (e.g. `gpt-4o`, `claude-3-5-sonnet`) | Pin to a dated version to prevent silent behavior changes |
| **TL011** | Tool result bloat | post | Tool/function result exceeds token threshold | Summarize or filter the result before returning to the model |
| **TL012** | Excessive tools | pre | More than N tools registered in one call | Filter tools to only those relevant to current context |
| **TL013** | Missing response_format | pre | System prompt requests JSON but `response_format` not set | Add `response_format={"type": "json_object"}` to guarantee valid JSON |
| **TL014** | Cost spike | post | Call tokens ≥ 3× session mean (after ≥5 baseline calls) | Investigate large tool results, unbounded history, or runaway prompts |
| **TL015** | n>1 completions | pre | `n > 1` passed in kwargs | Use `n=1`; vary temperature or prompt for diversity instead |

All rules fire to **stderr** only — your `stdout` pipeline is never interrupted.

---

## Privacy & data handling

**token-lens never sends any data anywhere.**

- All analysis runs in-process, in memory.
- No network connections are made by token-lens itself.
- No logs are written to disk.
- No telemetry, no analytics, no callbacks to external services.
- Your prompts, completions, and API keys are never touched by token-lens — they pass through to your SDK untouched.

This makes token-lens safe to deploy on enterprise servers and air-gapped environments.

---

## Enterprise / server deployment

For teams who want to enforce token efficiency standards across all services:

1. Add `token-lens` to your shared `requirements.txt` or `pyproject.toml`
2. Wrap your shared LLM client factory with `TokenLens`
3. Configure via `Config(enabled=os.getenv("TOKEN_LENS_ENABLED", "true") == "true")` to disable in production while keeping it active in staging/dev

```python
# shared_llm.py — your team's central LLM client module
import os
from openai import OpenAI
from token_lens import TokenLens, Config

_base_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

client = TokenLens(
    _base_client,
    Config(enabled=os.getenv("ENV", "dev") != "prod"),
)
```

Every service that imports `client` from this module gets token-lens monitoring automatically — no per-service changes needed.

---

## Running the tests

```bash
# Install dev dependencies
pip install -e ".[accurate-counting,dev]"

# Run the full test suite
pytest

# With coverage
pytest --cov=token_lens --cov-report=term-missing
```

---

## Project structure

```
token_lens/
├── __init__.py                  # Public API: TokenLens, AnthropicTokenLens, Config, TokenLensCallbackHandler
├── _wrapper.py                  # TokenLens — OpenAI-compatible SDK wrapper
├── _anthropic_wrapper.py        # AnthropicTokenLens — native Anthropic SDK wrapper
├── _chat.py                     # Intercepts chat.completions.create()
├── _anthropic_messages.py       # Intercepts messages.create()
├── _session.py                  # Session state, CallRecord, NormalizedUsage
├── _analyzer.py                 # Runs detection rules pre- and post-call
├── _reporter.py                 # ANSI terminal output and session summary
├── _tokenizer.py                # Token counting (tiktoken or 4-char fallback)
├── _config.py                   # Config dataclass
├── langgraph_integration.py     # TokenLensCallbackHandler for LangGraph/LangChain
└── rules/
    ├── _base.py                 # Rule ABC, Finding dataclass, Severity enum
    ├── static_system_prompt.py  # TL001
    ├── unbounded_history.py     # TL002
    ├── duplicate_prompt.py      # TL003
    ├── model_overkill.py        # TL004
    ├── long_system_prompt.py    # TL005
    ├── missing_max_tokens.py    # TL006
    ├── redundant_context.py     # TL007
    ├── pii_in_prompt.py         # TL008
    ├── secret_in_prompt.py      # TL009
    ├── unversioned_model.py     # TL010
    ├── tool_result_bloat.py     # TL011
    ├── excessive_tools.py       # TL012
    ├── missing_response_format.py  # TL013
    ├── cost_spike.py            # TL014
    └── n_completions.py         # TL015
```

---

## Contributing

Contributions welcome. To add a new rule:

1. Create `token_lens/rules/tl00N_your_rule_name.py` implementing the `Rule` ABC
2. Add it to `token_lens/rules/__init__.py`
3. Register it in `_analyzer.py` `_build_rules()`
4. Add tests in `token_lens/tests/rules/test_tl00N_your_rule_name.py`

---

## License

MIT — see [LICENSE](LICENSE).
