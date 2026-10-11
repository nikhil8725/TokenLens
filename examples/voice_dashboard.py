"""Voice-enabled token-lens dashboard (demo).

Run from the repo root:

    pip install -e ".[demo]"
    streamlit run examples/voice_dashboard.py

No API key is needed. Each "call" is simulated and fed through the real
Analyzer, so the findings are the same objects the wrapper produces.
Read-aloud uses the browser's SpeechSynthesis API, so nothing leaves the machine.
"""
from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from token_lens import Config
from token_lens._analyzer import Analyzer
from token_lens._session import CallRecord, NormalizedUsage, Session
from token_lens.rules._base import Finding, Severity

MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "claude-3-5-sonnet-20241022",
    "openai/gpt-4o",
]

_SPEAK_TEMPLATE = """
<div style="display:flex;gap:8px;font-family:sans-serif">
  <button id="speak" style="padding:6px 14px;cursor:pointer">🔊 Read aloud</button>
  <button id="stop" style="padding:6px 14px;cursor:pointer">■ Stop</button>
</div>
<script>
  const text = __TEXT__;
  const rate = __RATE__;
  document.getElementById("speak").onclick = () => {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = rate;
    u.lang = "en-US";
    window.speechSynthesis.speak(u);
  };
  document.getElementById("stop").onclick = () => window.speechSynthesis.cancel();
</script>
"""


def simulate_call(
    analyzer: Analyzer,
    session: Session,
    model: str,
    messages: list[dict],
    max_tokens: int | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> list[Finding]:
    """Run one simulated call through pre- and post-call analysis."""
    kwargs: dict = {"model": model, "messages": messages}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    record = CallRecord(
        call_id=uuid4(),
        timestamp=datetime.now(),
        model=model,
        messages=messages,
        raw_kwargs=kwargs,
    )
    findings = list(analyzer.analyze_pre_call(record, session))

    record.usage = NormalizedUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    session.add_call(record)
    findings += analyzer.analyze_post_call(record, session)
    return findings


def build_speech(findings: list[Finding]) -> str:
    """Short spoken summary. Rule IDs are left out because they read badly aloud."""
    if not findings:
        return "No findings. This call looks efficient."
    count = len(findings)
    parts = [f"{count} finding{'' if count == 1 else 's'}."]
    for f in findings[:5]:
        message = f.message.rstrip(".")
        first_step = f.suggestion.split(". ")[0].rstrip(".")
        parts.append(f"{message}. Suggestion: {first_step}.")
    if count > 5:
        parts.append(f"And {count - 5} more.")
    return " ".join(parts)


def speak_controls(text: str, rate: float) -> None:
    html = (
        _SPEAK_TEMPLATE
        .replace("__TEXT__", json.dumps(text))
        .replace("__RATE__", json.dumps(rate))
    )
    components.html(html, height=50)


_SEVERITY_DISPLAY = {
    Severity.ERROR: st.error,
    Severity.WARNING: st.warning,
    Severity.INFO: st.info,
}


def main() -> None:
    st.set_page_config(page_title="token-lens voice dashboard", layout="wide")
    st.title("token-lens — voice dashboard")

    if "analyzer" not in st.session_state:
        st.session_state.analyzer = Analyzer(Config())
        st.session_state.session = Session()
        st.session_state.findings = []

    with st.sidebar:
        st.subheader("Simulated call")
        model = st.selectbox("Model", MODELS)
        system = st.text_area("System prompt", "You are a helpful assistant.", height=120)
        user = st.text_area("User message", "Hello!", height=120)
        max_tokens = st.number_input("max_tokens (0 = unset)", 0, 100_000, 256, step=64)
        prompt_tokens = st.number_input("Prompt tokens", 0, 1_000_000, 200)
        completion_tokens = st.number_input("Completion tokens", 0, 100_000, 40)
        rate = st.slider("Speech rate", 0.5, 2.0, 1.0, 0.1)
        run = st.button("Run call", type="primary")

    if run:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        st.session_state.findings = simulate_call(
            st.session_state.analyzer,
            st.session_state.session,
            model,
            messages,
            max_tokens or None,
            int(prompt_tokens),
            int(completion_tokens),
        )

    session: Session = st.session_state.session
    findings: list[Finding] = st.session_state.findings

    col1, col2, col3 = st.columns(3)
    col1.metric("Calls", len(session.calls))
    col2.metric("Total tokens", f"{session.total_tokens():,}")
    col3.metric("Findings (last call)", len(findings))

    st.subheader("Findings")
    if not findings:
        st.success("No findings for the last call.")
    for f in findings:
        show = _SEVERITY_DISPLAY[f.severity]
        show(f"**[{f.rule_id}]** {f.message}\n\n→ {f.suggestion}")

    st.subheader("Voice summary")
    speech = build_speech(findings)
    st.write(speech)
    speak_controls(speech, rate)


if __name__ == "__main__":
    main()
"""Voice-enabled token-lens dashboard (demo).

Run from the repo root:

    pip install -e ".[demo]"
    streamlit run examples/voice_dashboard.py

No API key is needed. Each "call" is simulated and fed through the real
Analyzer, so the findings are the same objects the wrapper produces.
Read-aloud uses the browser's SpeechSynthesis API, so nothing leaves the machine.
"""
from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from token_lens import Config
from token_lens._analyzer import Analyzer
from token_lens._session import CallRecord, NormalizedUsage, Session
from token_lens.rules._base import Finding, Severity

MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "claude-3-5-sonnet-20241022",
    "openai/gpt-4o",
]

_SPEAK_TEMPLATE = """
<div style="display:flex;gap:8px;font-family:sans-serif">
  <button id="speak" style="padding:6px 14px;cursor:pointer">🔊 Read aloud</button>
  <button id="stop" style="padding:6px 14px;cursor:pointer">■ Stop</button>
</div>
<script>
  const text = __TEXT__;
  const rate = __RATE__;
  document.getElementById("speak").onclick = () => {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = rate;
    u.lang = "en-US";
    window.speechSynthesis.speak(u);
  };
  document.getElementById("stop").onclick = () => window.speechSynthesis.cancel();
</script>
"""


def simulate_call(
    analyzer: Analyzer,
    session: Session,
    model: str,
    messages: list[dict],
    max_tokens: int | None,
    prompt_tokens: int,
    completion_tokens: int,
) -> list[Finding]:
    """Run one simulated call through pre- and post-call analysis."""
    kwargs: dict = {"model": model, "messages": messages}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    record = CallRecord(
        call_id=uuid4(),
        timestamp=datetime.now(),
        model=model,
        messages=messages,
        raw_kwargs=kwargs,
    )
    findings = list(analyzer.analyze_pre_call(record, session))

    record.usage = NormalizedUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    session.add_call(record)
    findings += analyzer.analyze_post_call(record, session)
    return findings


def build_speech(findings: list[Finding]) -> str:
    """Short spoken summary. Rule IDs are left out because they read badly aloud."""
    if not findings:
        return "No findings. This call looks efficient."
    count = len(findings)
    parts = [f"{count} finding{'' if count == 1 else 's'}."]
    for f in findings[:5]:
        message = f.message.rstrip(".")
        first_step = f.suggestion.split(". ")[0].rstrip(".")
        parts.append(f"{message}. Suggestion: {first_step}.")
    if count > 5:
        parts.append(f"And {count - 5} more.")
    return " ".join(parts)


def speak_controls(text: str, rate: float) -> None:
    html = (
        _SPEAK_TEMPLATE
        .replace("__TEXT__", json.dumps(text))
        .replace("__RATE__", json.dumps(rate))
    )
    components.html(html, height=50)


_SEVERITY_DISPLAY = {
    Severity.ERROR: st.error,
    Severity.WARNING: st.warning,
    Severity.INFO: st.info,
}


def main() -> None:
    st.set_page_config(page_title="token-lens voice dashboard", layout="wide")
    st.title("token-lens — voice dashboard")

    if "analyzer" not in st.session_state:
        st.session_state.analyzer = Analyzer(Config())
        st.session_state.session = Session()
        st.session_state.findings = []

    with st.sidebar:
        st.subheader("Simulated call")
        model = st.selectbox("Model", MODELS)
        system = st.text_area("System prompt", "You are a helpful assistant.", height=120)
        user = st.text_area("User message", "Hello!", height=120)
        max_tokens = st.number_input("max_tokens (0 = unset)", 0, 100_000, 256, step=64)
        prompt_tokens = st.number_input("Prompt tokens", 0, 1_000_000, 200)
        completion_tokens = st.number_input("Completion tokens", 0, 100_000, 40)
        rate = st.slider("Speech rate", 0.5, 2.0, 1.0, 0.1)
        run = st.button("Run call", type="primary")

    if run:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        st.session_state.findings = simulate_call(
            st.session_state.analyzer,
            st.session_state.session,
            model,
            messages,
            max_tokens or None,
            int(prompt_tokens),
            int(completion_tokens),
        )

    session: Session = st.session_state.session
    findings: list[Finding] = st.session_state.findings

    col1, col2, col3 = st.columns(3)
    col1.metric("Calls", len(session.calls))
    col2.metric("Total tokens", f"{session.total_tokens():,}")
    col3.metric("Findings (last call)", len(findings))

    st.subheader("Findings")
    if not findings:
        st.success("No findings for the last call.")
    for f in findings:
        show = _SEVERITY_DISPLAY[f.severity]
        show(f"**[{f.rule_id}]** {f.message}\n\n→ {f.suggestion}")

    st.subheader("Voice summary")
    speech = build_speech(findings)
    st.write(speech)
    speak_controls(speech, rate)


if __name__ == "__main__":
    main()
