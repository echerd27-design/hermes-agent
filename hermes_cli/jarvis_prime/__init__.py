"""JARVIS Prime presentation helpers.

This package wraps presentation logic for JARVIS Prime gate reports.
Runtime gate evaluation lives in a separate module that is intentionally
not imported here, so this package can be used (and tested) without any
dependency on the evaluator.
"""

from hermes_cli.jarvis_prime.gate_reports import (
    GATE_DISPLAY_NAMES,
    GATE_ORDER,
    STATUS_FAIL,
    STATUS_OWNER_APPROVAL,
    STATUS_PASS,
    STATUS_SKIPPED,
    VALID_STATUSES,
    GateResultDict,
    GateResultLike,
    ReportDict,
    ReportLike,
    as_dict,
    failure_summary,
    markdown_report,
    mobile_report,
    owner_approval_summary,
)

__all__ = (
    "as_dict",
    "failure_summary",
    "markdown_report",
    "mobile_report",
    "owner_approval_summary",
    "GATE_DISPLAY_NAMES",
    "GATE_ORDER",
    "STATUS_FAIL",
    "STATUS_OWNER_APPROVAL",
    "STATUS_PASS",
    "STATUS_SKIPPED",
    "VALID_STATUSES",
    "GateResultDict",
    "GateResultLike",
    "ReportDict",
    "ReportLike",
)
