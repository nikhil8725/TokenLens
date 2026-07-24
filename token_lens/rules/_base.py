from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    message: str
    suggestion: str
    call_id: UUID | None = None


class Rule(ABC):
    @property
    @abstractmethod
    def rule_id(self) -> str: ...

    @property
    def phase(self) -> str:
        return "post"

    @abstractmethod
    def check(self, record: object, session: object) -> list[Finding]: ...
