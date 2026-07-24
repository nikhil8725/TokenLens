# CLAUDE.md — AI Assistant Instructions for token-lens

This file is loaded automatically at the start of every Claude Code session. Read it fully before taking any action — including clarifying questions.

---

## Superpowers methodology

This project uses the [superpowers](https://github.com/obra/superpowers) development methodology.

**Install (Claude Code):**
```
/plugin install superpowers@claude-plugins-official
```

**What it adds to this workflow:**

| Skill | When it activates |
|---|---|
| `brainstorming` | Before any new feature or non-trivial change — produces a spec in `docs/superpowers/specs/` |
| `writing-plans` | After brainstorming is approved — produces a task plan in `docs/superpowers/plans/` |
| `test-driven-development` | During every implementation task — no production code before a failing test |
| `verification-before-completion` | Before claiming any task is done — run the command, read the output, then claim success |
| `subagent-driven-development` | For multi-task plans — each task runs in a fresh subagent |
| `requesting-code-review` / `receiving-code-review` | Between tasks and before branch merge |
| `finishing-a-development-branch` | Before creating a PR |
| `systematic-debugging` | When a test fails or unexpected behavior is observed |

**Hard gates enforced by superpowers:**
- No implementation before a spec is written and approved (`brainstorming` → `writing-plans` → code)
- No production code before a failing test (`test-driven-development`)
- No completion claim without fresh verification evidence (`verification-before-completion`)
- Specs go to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
- Plans go to `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`

---

## Mandatory: update CONTEXT.md after every change

`CONTEXT.md` is the living architecture record. **Update it in the same session as any code change.** Do not report a task complete until `CONTEXT.md` reflects the new state.

### What triggers an update and which sections to touch

| Change type | Sections to update in CONTEXT.md |
|---|---|
| New file added or deleted | File Reference table |
| New rule (TL00N) | Detection Rules table + File Reference + Changelog |
| Rule trigger or severity changed | Detection Rules table + Changelog |
| New Config field | Config Reference + Changelog |
| New provider supported | Supported Providers table + Changelog |
| Architecture change | Architecture section + Changelog |
| Known limitation fixed | Remove from Known Limitations + Changelog |
| New known limitation | Add to Known Limitations + Changelog |
| Version bump | Current Version table + Changelog |
| Bug fixed | Changelog only (unless architecture changes) |

### Changelog entry format

Add a new `###` block at the **top** of the Changelog section in `CONTEXT.md`:

```markdown
### vX.Y.Z — YYYY-MM-DD

**Added:**
- Description

**Changed:**
- Description

**Fixed:**
- Description
```

---

## Project identity

- **What it is:** Local Python middleware that wraps LLM SDK clients and coaches developers on token efficiency. Zero cloud, zero mandatory dependencies, zero data exfiltration.
- **Entry point:** `token_lens/__init__.py` — exports `TokenLens`, `AnthropicTokenLens`, `Config`, `TokenLensCallbackHandler`
- **Architecture doc:** [CONTEXT.md](CONTEXT.md) — read before exploring code
- **User doc:** [README.md](README.md)
- **Tests:** `pytest token_lens/tests/` — 54 tests, all must pass before any task is reported complete

---

## Enterprise & production-readiness standards

These are the non-negotiable standards for this project to be considered production-ready and enterprise-shippable.

### Code quality

- All new code is Python 3.12+ with `from __future__ import annotations`
- No imports inside functions or methods — all imports at module level
- Duck-typed (`Any`) — no hard imports of `openai` or `anthropic` in the core package
- All terminal output to `stderr` only — never `stdout`
- No network calls from within `token_lens/` — local-only by design
- Thread-safe state mutation — `Session` uses `threading.Lock`; any new shared state must too
- No mandatory dependencies — `[project.dependencies]` in `pyproject.toml` stays empty

### Testing standards

- Every new rule must have: at least one fire-case test + at least one no-fire-case test
- Every new public class must have: a passthrough test (returns the real SDK response unchanged)
- TDD: write the failing test first, verify it fails, then implement
- No mocking of internal modules — only mock at the SDK boundary (`MagicMock` on the client)
- Tests must not rely on network access or real API keys

### Typing

- All public functions and methods have complete type annotations
- `token_lens/py.typed` exists (PEP 561 marker — typed package)
- No `# type: ignore` without an inline explanation

### Packaging

- `pyproject.toml` uses `[project]` table with classifiers as a plain list (not under a `[project.classifiers]` subsection — that's invalid TOML for PyPI)
- `[project.urls]` uses real repository URLs, not placeholder `your-username`
- Optional extras: `accurate-counting` (tiktoken), `langgraph` (langchain-core), `dev` (test deps)
- Build backend: `hatchling`

### Security

- Never log or print prompt content, API keys, or response content — only metadata (token counts, model names, rule IDs)
- `raw_kwargs` on `CallRecord` is for rule inspection only — never serialized or transmitted
- Streaming calls bypass analysis entirely (can't consume without breaking the stream)

### Documentation

- `README.md` contains: installation, quick start per provider, config reference, privacy statement
- `CONTEXT.md` is always current (this file enforces that)
- New public APIs added to the Quick Usage Reference in `CONTEXT.md`

---

## How to add a new detection rule

Follow TDD strictly:

1. Write the test file first: `token_lens/tests/rules/test_tl00N_name.py`
   - At minimum: one fire-case and one no-fire-case
   - Run it, confirm it fails (no rule exists yet)
2. Create `token_lens/rules/tl00N_name.py` implementing the `Rule` ABC
   - All imports at module level
   - `_fired_hashes: set[str]` pattern for rules that should fire only once per trigger
3. Export from `token_lens/rules/__init__.py`
4. Instantiate in `_build_rules()` in `token_lens/_analyzer.py`
5. Add any config fields to `token_lens/_config.py`
6. Run tests — confirm fire-case passes, no-fire-case passes, all 54+ prior tests still pass
7. Update `CONTEXT.md`: rule table, file reference, changelog
8. Update `README.md`: detection rules table

---

## How to add a new provider

**If the provider uses an OpenAI-compatible `chat.completions.create()` interface:**
- No code change needed
- Add it to the Supported Providers table in `CONTEXT.md` and `README.md`

**If the provider has a unique SDK interface (like Anthropic's `messages.create()`):**
1. Create `token_lens/_<provider>_messages.py` — `Instrumented<Provider>Messages` + usage normalizer
2. Create `token_lens/_<provider>_wrapper.py` — `<Provider>TokenLens` (mirror `_anthropic_wrapper.py`)
3. Export the new wrapper from `token_lens/__init__.py`
4. Add tests in `token_lens/tests/test_<provider>_wrapper.py` (use `test_anthropic_wrapper.py` as template)
5. Update `CONTEXT.md` + `README.md` provider tables + changelog

---

## Running and verifying

```bash
# First time setup
python3 -m venv .venv
.venv/bin/pip install -e ".[accurate-counting,dev]"

# Every time before claiming a task is done
.venv/bin/pytest token_lens/tests/ -v

# Build the package (before shipping)
.venv/bin/pip install build
.venv/bin/python -m build
```

Expected: **54 passed** (or more if you added tests). Zero failures, zero warnings about missing stubs.

---

## What NOT to do

- Do not add mandatory dependencies to `[project.dependencies]`
- Do not write to `stdout` from within `token_lens/` — always `stderr`
- Do not make network calls from within `token_lens/`
- Do not put imports inside functions or methods
- Do not consume streaming responses — bypass `stream=True` calls entirely
- Do not update only `README.md` and forget `CONTEXT.md`, or vice versa
- Do not use `[project.classifiers]` as a TOML section header — it must be a key under `[project]`
- Do not claim a task is complete without running `pytest` and reading the output

---

## Production-readiness checklist

Before calling this project shippable, all of these must be true:

### Must-have (blocking)
- [ ] All 54+ tests pass with zero failures
- [ ] `py.typed` exists in `token_lens/`
- [ ] `pyproject.toml` classifiers are valid (under `[project]`, not a subsection)
- [ ] No `your-username` placeholders in `pyproject.toml` URLs
- [ ] Package builds cleanly: `python -m build` produces `.whl` and `.tar.gz`
- [ ] Package installs from wheel with zero errors: `pip install dist/*.whl`
- [ ] `AsyncOpenAI` and `AsyncAnthropic` are handled (or explicitly documented as unsupported in README)
- [ ] Streaming calls documented as a known limitation in README

### Should-have (non-blocking for alpha)
- [ ] CI workflow (GitHub Actions) running `pytest` on push
- [ ] `mypy` or `pyright` passes with no errors on `token_lens/`
- [ ] Changelog section in README or RELEASE-NOTES.md
- [ ] At least one real-world usage example (the `my-first-agent` migration)

### Nice-to-have (post-alpha)
- [ ] Async support: `AsyncTokenLens`, `AsyncAnthropicTokenLens`
- [ ] Streaming support: reconstruct usage from final chunk delta
- [ ] JSON output mode: `Config(output_format="json")` for CI pipelines
- [ ] `token-lens check` CLI command for scanning a Python file for patterns

---

## Current production-readiness status (as of v0.1.0 — 2026-07-23)

| Check | Status | Notes |
|---|---|---|
| Tests pass | ✅ 54/54 | |
| `py.typed` exists | ✅ | Added 2026-07-23 |
| `pyproject.toml` classifiers valid | ✅ | Fixed 2026-07-23 |
| Real repo URLs | ✅ | Updated 2026-07-23 |
| Package builds | ⚠️ Not verified | Run `python -m build` to confirm |
| Async support | ❌ Missing | Known limitation — blocking for enterprise |
| Streaming analysis | ❌ Bypassed | Known limitation — documented |
| CI pipeline | ❌ Missing | Needed before PyPI publish |
| `mypy` clean | ⚠️ Not verified | Run `mypy token_lens/` to check |
| LangGraph `NormalizedUsage` | ✅ Fixed | Was setting stale fields — corrected 2026-07-23 |
