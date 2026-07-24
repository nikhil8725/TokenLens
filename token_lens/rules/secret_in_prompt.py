from __future__ import annotations
import re
from ._base import Rule, Finding, Severity

_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("OpenAI API key",    re.compile(r'sk-[A-Za-z0-9]{20,}')),
    ("Anthropic API key", re.compile(r'sk-ant-[A-Za-z0-9\-]{20,}')),
    ("AWS access key",    re.compile(r'AKIA[0-9A-Z]{16}')),
    ("GitHub token",      re.compile(r'gh[pousr]_[A-Za-z0-9]{36,}')),
    ("Bearer token",      re.compile(r'Bearer\s+[A-Za-z0-9+/=._\-]{20,}')),
    ("PEM private key",   re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
]


class SecretInPromptRule(Rule):
    """TL009 — Credential or API key detected in prompt content."""

    rule_id = "TL009"
    phase = "pre"

    def check(self, record, session) -> list[Finding]:
        findings = []
        seen_types: set[str] = set()
        for msg in record.messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue
            for secret_type, pattern in _SECRET_PATTERNS:
                if secret_type in seen_types:
                    continue
                if pattern.search(content):
                    seen_types.add(secret_type)
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        severity=Severity.ERROR,
                        call_id=record.call_id,
                        message=(
                            f"Possible {secret_type} detected in role:{role} message."
                        ),
                        suggestion=(
                            f"Remove {secret_type} from prompt content immediately. "
                            "Secrets sent to LLM providers are logged and visible to the provider. "
                            "Pass credentials via environment variables and inject only what the model "
                            "actually needs — never raw keys. Rotate any exposed credential now."
                        ),
                    ))
        return findings
