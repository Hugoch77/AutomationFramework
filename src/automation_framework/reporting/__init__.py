"""Evidence collection and report publishing.

`evidence` and `capture` are reporter-agnostic: they gather what a failing test left behind.
`allure_adapter` is the only piece that knows which report is being written, so changing
reporter touches one file.
"""

from automation_framework.reporting.capture import (
    LogCapture,
    TeeLogger,
    capturing_logger_factory,
)
from automation_framework.reporting.evidence import (
    Evidence,
    collect_evidence,
    describe,
)

__all__ = [
    "Evidence",
    "LogCapture",
    "TeeLogger",
    "capturing_logger_factory",
    "collect_evidence",
    "describe",
]
