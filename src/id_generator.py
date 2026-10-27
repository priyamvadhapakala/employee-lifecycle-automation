"""Deterministic ID formatting helpers.

These functions format IDs from sequence numbers. They do not keep mutable
counters; callers own and persist the sequence values so IDs remain reproducible.
"""

from __future__ import annotations

import re

_YEAR_RE = re.compile(r"^\d{4}$")


def _positive(number: int, field: str = "number") -> int:
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise ValueError(f"{field} must be a positive integer")
    return number


def _year(year: int | str) -> str:
    value = str(year)
    if not _YEAR_RE.fullmatch(value):
        raise ValueError("year must contain exactly four digits")
    return value


def employee_id(number: int) -> str:
    return f"EMP-{_positive(number):06d}"


def onboarding_case_id(year: int | str, number: int) -> str:
    return f"ONB-{_year(year)}-{_positive(number):06d}"


def task_id(onboarding_id: str, number: int) -> str:
    if not re.fullmatch(r"(?:ONB|OFF)-\d{4}-\d{6}", onboarding_id):
        raise ValueError("case_id must have format ONB-YYYY-NNNNNN or OFF-YYYY-NNNNNN")
    return f"TASK-{onboarding_id}-{_positive(number):03d}"


def access_grant_id(employee: str, number: int) -> str:
    if not re.fullmatch(r"EMP-\d{6}", employee):
        raise ValueError("employee_id must have format EMP-NNNNNN")
    return f"GRANT-{employee}-{_positive(number):03d}"


def asset_id(number: int) -> str:
    return f"AST-{_positive(number):06d}"


def offboarding_case_id(year: int | str, number: int) -> str:
    return f"OFF-{_year(year)}-{_positive(number):06d}"


def department_id(number: int) -> str:
    return f"DEPT-{_positive(number):03d}"


def role_id(number: int) -> str:
    return f"ROLE-{_positive(number):03d}"


def manager_id(number: int) -> str:
    return f"MGR-{_positive(number):03d}"


def dependency_id(number: int) -> str:
    return f"DEP-{_positive(number):06d}"


def access_role_id(number: int) -> str:
    return f"AROLE-{_positive(number):03d}"


def audit_event_id(number: int) -> str:
    return f"AUD-{_positive(number):09d}"
