from datetime import date

from src.workflow_engine import can_provision_access, can_transition, EMPLOYEE_TRANSITIONS


def test_access_requires_approval_and_start_date():
    start = date(2026, 3, 10)
    assert not can_provision_access(approved=False, approval_required=True, effective_date=start, start_date=start)
    assert not can_provision_access(approved=True, approval_required=True, effective_date=date(2026, 3, 9), start_date=start)
    assert can_provision_access(approved=True, approval_required=True, effective_date=start, start_date=start)
    assert can_provision_access(approved=False, approval_required=False, effective_date=start, start_date=start)


def test_employment_transitions_are_explicit():
    assert can_transition("pending", "active", EMPLOYEE_TRANSITIONS)
    assert can_transition("active", "terminated", EMPLOYEE_TRANSITIONS)
    assert not can_transition("terminated", "active", EMPLOYEE_TRANSITIONS)
