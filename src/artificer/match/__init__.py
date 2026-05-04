"""Audit module — compares unit logic JSON against views to surface gaps.

Per D-015, the views file is the authoritative source for unit
abilities/passives; this module's pattern detectors are no-ops, retained
for legacy import shape only. The audit (``audit_unit``, ``write_audit``)
is the live functionality here.
"""

from artificer.match.audit import AuditReport, UnitAudit, audit_unit, write_audit
from artificer.match.patterns import PATTERN_DETECTORS, Match, run_detectors

__all__ = [
    "AuditReport",
    "Match",
    "PATTERN_DETECTORS",
    "UnitAudit",
    "audit_unit",
    "run_detectors",
    "write_audit",
]
