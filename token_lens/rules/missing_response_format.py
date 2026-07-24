from __future__ import annotations
import hashlib
import re
from ._base import Rule, Finding, Severity

_JSON_KEYWORDS = re.compile(
    r'\b(json|JSON)\b|'
    r'output json|return json|respond with json|valid json|as a json object|'
    r'in json format|json response|json object',
    re.IGNORECASE,
)


class MissingResponseFormatRule(Rule):
    """TL013 — JSON output requested in system prompt but response_format not set."""

    rule_id = "TL013"
    phase = "pre"

    def __init__(self) -> None:
        self._fired_hashes: set[str] = set()

    def check(self, record, session) -> list[Finding]:
        if record.raw_kwargs.get("response_format"):
            return []

        system_text = ""
        for msg in record.messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if isinstance(content, str):
                    system_text += content

        if not system_text or not _JSON_KEYWORDS.search(system_text):
            return []

        prompt_hash = hashlib.sha256(system_text.encode()).hexdigest()
        if prompt_hash in self._fired_hashes:
            return []
        self._fired_hashes.add(prompt_hash)

        return [Finding(
            rule_id=self.rule_id,
            severity=Severity.WARNING,
            call_id=record.call_id,
            message="System prompt requests JSON output but response_format is not set.",
            suggestion=(
                "Add response_format={\"type\": \"json_object\"} (OpenAI) or equivalent to guarantee "
                "valid JSON output and skip post-processing. Without it the model can emit markdown "
                "code fences, prose, or partial JSON — all of which break JSON parsers silently. "
                "For structured schemas, use response_format={\"type\": \"json_schema\", \"json_schema\": ...} "
                "or Pydantic-based structured outputs."
            ),
        )]
