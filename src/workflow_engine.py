"""Small explicit workflow policy helpers used by generation and validation."""

from __future__ import annotations

from datetime import date, timedelta

EMPLOYEE_TRANSITIONS = {
    "pending": {"active", "terminated"},
    "active": {"completed", "terminated"},
    "completed": set(),
    "terminated": set(),
}
CASE_TRANSITIONS = {
    "planned": {"in_progress", "blocked", "cancelled"},
    "in_progress": {"blocked", "completed", "cancelled"},
    "blocked": {"in_progress", "completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def can_transition(current: str, target: str, transitions: dict[str, set[str]]) -> bool:
    return target in transitions.get(current, set())


def can_provision_access(*, approved: bool, approval_required: bool, effective_date: date, start_date: date) -> bool:
    """Access is provisionable only after approvals and on/after the start date."""
    return (approved or not approval_required) and effective_date >= start_date


def urgent_exit_revocation_deadline(last_working_date: date, urgent: bool) -> date:
    """Urgent exits revoke on the exit date; normal exits revoke by the next day."""
    return last_working_date if urgent else last_working_date + timedelta(days=1)

