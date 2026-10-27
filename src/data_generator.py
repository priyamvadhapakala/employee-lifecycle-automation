"""Deterministic generation of valid synthetic employee lifecycle records."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import random
from typing import Any

import numpy as np
import pandas as pd

from .id_generator import (
    access_grant_id, access_role_id, asset_id, audit_event_id, department_id,
    dependency_id, employee_id, manager_id, offboarding_case_id,
    onboarding_case_id, role_id, task_id,
)

DEPARTMENTS = ["People Operations", "Engineering", "Finance", "Customer Operations", "Facilities"]
ROLE_NAMES = ["People Partner", "Software Engineer", "Financial Analyst", "Support Specialist", "Facilities Coordinator"]
LOCATIONS = ["New York", "London", "Bengaluru", "Remote"]
ACCESS = [
    ("email_standard", "Standard company email and calendar", 0),
    ("source_control", "Source code repository access", 1),
    ("finance_system", "Finance system access", 1),
    ("support_console", "Customer support console access", 1),
]
TS = lambda d: f"{d.isoformat()}T09:00:00Z"


def generate_dataset(config: dict[str, Any] | None = None, mode: str | None = None, seed: int | None = None) -> dict[str, pd.DataFrame]:
    """Generate every baseline entity in parent-before-child order."""
    if config is None:
        from .config import load_config
        config = load_config()
    mode = mode or config["mode"]
    seed = config["seed"] if seed is None else int(seed)
    if mode not in ("starter", "full"):
        raise ValueError("mode must be starter or full")
    sizes = config["dataset_sizes"][mode]
    n = sizes["employees"]
    task_count = sizes["tasks"]
    grant_count = sizes["access_grants"]
    asset_count = sizes["assets"]
    py_rng = random.Random(seed)
    rng = np.random.default_rng(seed)
    departments = pd.DataFrame([{
        "department_id": department_id(i + 1), "department_name": name,
        "cost_center": f"CC-{(i + 1) * 100:03d}", "created_at": "2026-01-01T00:00:00Z"
    } for i, name in enumerate(DEPARTMENTS)])
    roles = pd.DataFrame([{
        "role_id": role_id(i + 1), "role_name": name, "role_family": DEPARTMENTS[i],
        "employment_type_default": "contractor" if i == 3 else "full_time", "created_at": "2026-01-01T00:00:00Z"
    } for i, name in enumerate(ROLE_NAMES)])
    access_roles = pd.DataFrame([{
        "access_role_id": access_role_id(i + 1), "role_name": row[0], "description": row[1],
        "approval_required": row[2], "created_at": "2026-01-01T00:00:00Z"
    } for i, row in enumerate(ACCESS)])

    dates = [date(2026, 1, 1) + timedelta(days=int(x)) for x in rng.integers(0, 300, size=n)]
    employees_rows = []
    for i in range(n):
        eid = employee_id(i + 1)
        planned = dates[i]
        delayed = (i % 9 == 0)
        actual = planned + timedelta(days=int(rng.integers(1, 9))) if delayed else planned
        terminated = (i % 10 == 0)
        status = "terminated" if terminated else ("pending" if i % 13 == 0 else "active")
        hire = planned - timedelta(days=14)
        employees_rows.append({
            "employee_id": eid, "first_name": f"Employee{i + 1:04d}", "last_name": f"Synthetic{i % 97:02d}",
            "email": f"employee{i + 1:04d}@example.test", "department_id": department_id(i % len(DEPARTMENTS) + 1),
            "role_id": role_id(i % len(ROLE_NAMES) + 1), "manager_id": None,
            "employment_type": "contractor" if i % 6 == 0 else "full_time", "employment_status": status,
            "hire_date": hire.isoformat(), "planned_start_date": planned.isoformat(),
            "actual_start_date": actual.isoformat() if status != "pending" else None,
            "termination_date": (actual + timedelta(days=90)).isoformat() if terminated else None,
            "location": LOCATIONS[i % len(LOCATIONS)], "created_at": TS(hire),
        })
    employees = pd.DataFrame(employees_rows)
    managers = pd.DataFrame([{
        "manager_id": manager_id(i + 1), "employee_id": employee_id(i + 1),
        "active_from": "2025-01-01", "active_to": None
    } for i in range(max(1, min(20, n // 8)))])
    for i, row in employees.iterrows():
        employees.at[i, "manager_id"] = manager_id((i % len(managers)) + 1) if n > len(managers) else None

    onb_rows, off_rows, task_rows, dep_rows = [], [], [], []
    task_specs = [
        ("welcome_packet", "HR", False), ("manager_approval", "Manager", True),
        ("account_setup", "IT", True), ("security_training", "IT", False),
        ("equipment_prepare", "Facilities", False), ("equipment_delivery", "Facilities", False),
        ("policy_acknowledgement", "HR", False), ("first_week_checkin", "HR", False),
    ]
    # Enforce exact configured task total while retaining the familiar eight-task case shape.
    tasks_per_employee = task_count // max(n, 1)
    extra_tasks = task_count % max(n, 1)
    task_by_case: dict[str, list[str]] = {}
    off_seq = 0
    for i, erow in employees.iterrows():
        eid = erow.employee_id
        year = int(erow.planned_start_date[:4])
        onb = onboarding_case_id(year, i + 1)
        start = date.fromisoformat(erow.planned_start_date)
        opened = start - timedelta(days=14)
        completed = erow.employment_status in ("active", "terminated")
        onb_rows.append({"onboarding_case_id": onb, "employee_id": eid, "opened_at": TS(opened),
                         "planned_start_date": start.isoformat(), "actual_start_date": erow.actual_start_date,
                         "status": "completed" if completed else "in_progress",
                         "completed_at": TS(date.fromisoformat(erow.actual_start_date)) if completed else None})
        is_exit = erow.employment_status == "terminated"
        off = None
        if is_exit:
            off_seq += 1
            off = offboarding_case_id(year, off_seq)
            last_day = date.fromisoformat(erow.termination_date)
            urgent_exit = i % 20 == 0
            exit_completed = last_day if urgent_exit else last_day + timedelta(days=1)
            off_rows.append({"offboarding_case_id": off, "employee_id": eid,
                             "opened_at": TS(last_day - timedelta(days=2)), "last_working_date": last_day.isoformat(),
                             "exit_type": "termination" if urgent_exit else "contract_end",
                             "urgency": "urgent" if urgent_exit else "normal",
                             "status": "completed", "completed_at": TS(exit_completed)})
        count = tasks_per_employee + (1 if i < extra_tasks else 0)
        case_task_ids = []
        for j in range(count):
            spec = task_specs[j % len(task_specs)]
            is_off_task = bool(is_exit and j >= max(1, count - 2))
            task_case = off if is_off_task else onb
            prefix_case = task_case
            local_number = (j - max(1, count - 2) + 1) if is_off_task else (j + 1)
            tid = task_id(prefix_case, local_number)
            case_task_ids.append(tid)
            is_complete = completed or is_off_task
            created = opened if not is_off_task else date.fromisoformat(erow.termination_date) - timedelta(days=2)
            task_completed = (date.fromisoformat(erow.termination_date) + timedelta(days=0 if i % 20 == 0 else 1)) if is_off_task else created + timedelta(days=2)
            task_rows.append({"task_id": tid, "onboarding_case_id": None if is_off_task else onb,
                              "offboarding_case_id": off if is_off_task else None,
                              "task_type": ("revoke_access" if j % 2 == 0 else "recover_assets") if is_off_task else spec[0],
                              "owner_team": "IT" if is_off_task and j % 2 == 0 else ("Facilities" if is_off_task else spec[1]),
                              "status": "completed" if is_complete else "pending",
                              "priority": "urgent" if is_off_task and off and next(x for x in off_rows if x["offboarding_case_id"] == off)["urgency"] == "urgent" else "normal",
                              "created_at": TS(created), "due_at": TS(created + timedelta(days=5)),
                              "completed_at": TS(task_completed) if is_complete else None,
                              "approval_required": int(spec[2]), "approved_by": "manager.synthetic" if spec[2] and is_complete else None,
                              "approved_at": TS(created + timedelta(days=1)) if spec[2] and is_complete else None})
        task_by_case[onb] = case_task_ids
        # A linear, acyclic prerequisite chain for each onboarding case.
        for j in range(1, len(case_task_ids)):
            if task_rows[-count + j]["onboarding_case_id"] == onb and task_rows[-count + j - 1]["onboarding_case_id"] == onb:
                dep_rows.append({"dependency_id": dependency_id(len(dep_rows) + 1),
                                 "task_id": case_task_ids[j], "prerequisite_task_id": case_task_ids[j - 1],
                                 "created_at": TS(opened)})

    onboardings, offboardings = pd.DataFrame(onb_rows), pd.DataFrame(off_rows)
    tasks = pd.DataFrame(task_rows)
    dependencies = pd.DataFrame(dep_rows, columns=["dependency_id", "task_id", "prerequisite_task_id", "created_at"])

    # Grants are distributed across employees and access roles. Baseline termination grants are revoked.
    grants_rows = []
    for i in range(grant_count):
        emp_index = i % max(n, 1)
        erow = employees.iloc[emp_index]
        started = date.fromisoformat(erow.actual_start_date if pd.notna(erow.actual_start_date) else erow.planned_start_date)
        requested = started - timedelta(days=5)
        approval_needed = ACCESS[i % len(ACCESS)][2]
        approved = requested + timedelta(days=1) if approval_needed else requested
        active = erow.employment_status != "pending"
        revoked = erow.employment_status == "terminated"
        revoke_date = date.fromisoformat(erow.termination_date) + timedelta(days=0 if emp_index % 20 == 0 else 1) if revoked else None
        grants_rows.append({"access_grant_id": access_grant_id(erow.employee_id, 1 + i // max(n, 1)),
                            "employee_id": erow.employee_id, "access_role_id": access_role_id(i % len(ACCESS) + 1),
                            "requested_at": TS(requested), "approved_by": "manager.synthetic" if approval_needed else "system",
                            "approved_at": TS(approved) if approval_needed or active else None,
                            "effective_from": TS(started), "effective_to": TS(revoke_date) if revoked else None,
                            "status": "revoked" if revoked else ("active" if active else "pending"),
                            "revoked_at": TS(revoke_date) if revoked else None,
                            "source_task_id": None})
    grants = pd.DataFrame(grants_rows)

    assets_rows, assignments_rows = [], []
    assigned_n = min(asset_count, max(0, int(n * 0.9)))
    for i in range(asset_count):
        assigned = i < assigned_n
        erow = employees.iloc[i % max(n, 1)] if assigned else None
        assigned_at = TS(date.fromisoformat(erow.planned_start_date) - timedelta(days=2)) if assigned else None
        delivered = TS(date.fromisoformat(erow.planned_start_date)) if assigned else None
        acked = TS(date.fromisoformat(erow.planned_start_date) + timedelta(days=1)) if assigned else None
        recovered = TS(date.fromisoformat(erow.termination_date)) if assigned and erow.employment_status == "terminated" else None
        status = "recovered" if recovered else ("assigned" if assigned else "available")
        current_assignment = assigned and not recovered
        aid = asset_id(i + 1)
        assets_rows.append({"asset_id": aid, "asset_type": ["laptop", "phone", "badge", "monitor"][i % 4],
                            "serial_number": f"SYN-{i + 1:07d}", "asset_status": status,
                            "assigned_employee_id": erow.employee_id if current_assignment else None,
                            "assigned_at": assigned_at if current_assignment else None,
                            "delivered_at": delivered if current_assignment else None,
                            "acknowledged_at": acked if current_assignment else None,
                            "recovered_at": recovered})
        if assigned:
            assignments_rows.append({"asset_assignment_id": f"ASG-{i + 1:06d}", "asset_id": aid,
                                     "employee_id": erow.employee_id,
                                     "assignment_status": "returned" if recovered else "assigned",
                                     "assigned_at": assigned_at, "delivered_at": delivered,
                                     "acknowledged_at": acked, "recovered_at": recovered})
    assets, asset_assignments = pd.DataFrame(assets_rows), pd.DataFrame(assignments_rows)
    if asset_assignments.empty:
        asset_assignments = pd.DataFrame(columns=["asset_assignment_id", "asset_id", "employee_id", "assignment_status", "assigned_at", "delivered_at", "acknowledged_at", "recovered_at"])

    # Build append-only audit trail for baseline state transitions.
    audit_rows = []
    def audit(entity_type: str, entity_id: str, event: str, timestamp: str, old: str | None, new: str, reason: str):
        audit_rows.append({"audit_event_id": audit_event_id(len(audit_rows) + 1), "entity_type": entity_type,
                           "entity_id": entity_id, "event_type": event, "event_at": timestamp,
                           "actor": "workflow.synthetic", "old_value": old, "new_value": new, "reason": reason})
    for r in onboardings.to_dict("records"):
        audit("OnboardingCase", r["onboarding_case_id"], "case_created", r["opened_at"], None, r["status"], "Synthetic onboarding case created")
    for r in tasks.to_dict("records"):
        if r["status"] == "completed":
            audit("Task", r["task_id"], "task_completed", r["completed_at"], "pending", "completed", "Prerequisites and workflow action completed")
    for r in grants.to_dict("records"):
        if r["status"] in ("active", "revoked"):
            audit("AccessGrant", r["access_grant_id"], "grant_activated", r["effective_from"], "pending", "active", "Approval and effective date satisfied")
        if r["status"] == "revoked":
            audit("AccessGrant", r["access_grant_id"], "grant_revoked", r["revoked_at"], "active", "revoked", "Employee exit processed")
    for r in assets.to_dict("records"):
        if pd.notna(r["assigned_employee_id"]):
            audit("Asset", r["asset_id"], "asset_assigned", r["assigned_at"], "available", "assigned", "Suitable synthetic asset assigned")
    for r in offboardings.to_dict("records"):
        audit("OffboardingCase", r["offboarding_case_id"], "case_completed", r["completed_at"], "in_progress", "completed", "Exit tasks processed")
    for i, r in employees.iterrows():
        if i % 25 == 0:
            old_role = role_id((i + 1) % len(ROLE_NAMES) + 1)
            audit("Employee", r["employee_id"], "role_changed", r["created_at"], old_role, r["role_id"],
                  "Synthetic role change recorded; current role is stored on Employee")
    for r in assets.to_dict("records"):
        if pd.notna(r["recovered_at"]):
            audit("Asset", r["asset_id"], "asset_recovered", r["recovered_at"], "assigned", "recovered",
                  "Asset returned during synthetic offboarding")
    audit_events = pd.DataFrame(audit_rows)
    tables = {
        "Department": departments, "Role": roles, "Manager": managers, "Employee": employees,
        "OnboardingCase": onboardings, "Task": tasks, "Dependency": dependencies,
        "AccessRole": access_roles, "AccessGrant": grants, "Asset": assets,
        "AssetAssignment": asset_assignments, "OffboardingCase": offboardings, "AuditEvent": audit_events,
    }
    return tables
