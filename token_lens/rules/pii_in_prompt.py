from __future__ import annotations
import re
from ._base import Rule, Finding, Severity

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("email address",  re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')),
    ("phone number",   re.compile(r'(\+?1?\s?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})')),
    ("credit card",    re.compile(
        r'\b(?:4[0-9]{12}(?:[0-9]{3})?'   # Visa
        r'|5[1-5][0-9]{14}'                # Mastercard
        r'|3[47][0-9]{13}'                 # Amex
        r'|6(?:011|5[0-9]{2})[0-9]{12})\b'  # Discover
    )),
    ("SSN",            re.compile(r'\b(?!000|666|9\d{2})\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}\b')),
    ("IP address",     re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')),
]


class PIIInPromptRule(Rule):
    """TL008 — PII detected in prompt content before sending to LLM provider."""

    rule_id = "TL008"
    phase = "pre"

    def __init__(self, check_roles: set[str] | None = None) -> None:
        self._roles = check_roles if check_roles is not None else {"user", "system", "tool"}

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
                        message=(
                            f"Possible {pii_type} detected in role:{role} message."
                        ),
                        suggestion=(
                            f"Remove or anonymize {pii_type} before sending to the LLM provider. "
                            "Under GDPR/CCPA, personal data must not be sent to external processors "
                            "without explicit consent and a Data Processing Agreement. "
                            "Consider a PII scrubber (Presidio, AWS Comprehend Detect PII) in your pipeline."
                        ),
                    ))
        return findings
