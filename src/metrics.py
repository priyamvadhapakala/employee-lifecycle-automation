"""Operational metrics and ground-truth evaluation."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def calculate_metrics(tables: dict[str, pd.DataFrame], checks: pd.DataFrame,
                      detections: pd.DataFrame, ground_truth: pd.DataFrame) -> dict[str, Any]:
    employees, tasks = tables["Employee"], tables["Task"]
    completed_cases = tables["OnboardingCase"][tables["OnboardingCase"].status.eq("completed")]
    completion_days = []
    for _, case in completed_cases.iterrows():
        if case.completed_at:
            completion_days.append((pd.Timestamp(case.completed_at) - pd.Timestamp(case.opened_at)).total_seconds() / 86400)
    overdue = tasks[(tasks.status.eq("overdue")) | (tasks.status.ne("completed") & (pd.to_datetime(tasks.due_at, utc=True) < pd.Timestamp("2027-01-01T00:00:00Z")))]
    active_grants = tables["AccessGrant"][tables["AccessGrant"].status.eq("active")]
    terminated_ids = set(employees.loc[employees.employment_status.eq("terminated"), "employee_id"])
    bad_terminated = active_grants[active_grants.employee_id.isin(terminated_ids)]
    active_assign = tables["AssetAssignment"][tables["AssetAssignment"].assignment_status.eq("assigned")]
    duplicate_assets = sum(1 for _, group in active_assign.groupby("asset_id") if group.employee_id.nunique() > 1)
    exited = tables["OffboardingCase"]
    exit_asset_assignments = tables["AssetAssignment"][tables["AssetAssignment"].employee_id.isin(terminated_ids)]
    recovered_exit_assets = exit_asset_assignments[exit_asset_assignments.assignment_status.eq("returned")]
    detected_keys = {(r.issue_type, r.entity_id) for r in detections.itertuples()} if not detections.empty else set()
    truth_keys = {(r.issue_type, r.entity_id) for r in ground_truth.itertuples()} if not ground_truth.empty else set()
    tp = len(detected_keys & truth_keys)
    fp = len(detected_keys - truth_keys)
    fn = len(truth_keys - detected_keys)
    precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
    f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and precision + recall else (0.0 if precision == 0 or recall == 0 else None)
    audit_relevant = len(tasks[tasks.status.eq("completed")]) + len(completed_cases) + len(exited[exited.status.eq("completed")])
    audited = set(zip(tables["AuditEvent"].entity_type, tables["AuditEvent"].entity_id))
    audited_relevant = sum(("Task", row.task_id) in audited for row in tasks[tasks.status.eq("completed")].itertuples())
    audited_relevant += sum(("OnboardingCase", row.onboarding_case_id) in audited for row in completed_cases.itertuples())
    audited_relevant += sum(("OffboardingCase", row.offboarding_case_id) in audited for row in exited[exited.status.eq("completed")].itertuples())
    entity_counts = {name: int(len(frame)) for name, frame in tables.items() if name != "GroundTruth"}
    return {
        "employee_count": int(len(employees)),
        "task_count": int(len(tasks)),
        "access_grant_count": int(len(tables["AccessGrant"])),
        "asset_count": int(len(tables["Asset"])),
        "entity_record_counts": entity_counts,
        "onboarding_completion_rate": _ratio(len(completed_cases), len(tables["OnboardingCase"])),
        "average_onboarding_completion_days": sum(completion_days) / len(completion_days) if completion_days else None,
        "overdue_task_rate": _ratio(len(overdue), len(tasks)),
        "task_dependency_violation_count": int((checks.check_id.isin(["TASK_CYCLE", "TASK_PREREQUISITE"])).sum()),
        "access_policy_violation_count": int((checks.check_id == "ACCESS_POLICY").sum()),
        "active_grants_linked_to_terminated_employees": int(len(bad_terminated)),
        "duplicate_asset_assignment_count": int(duplicate_assets),
        "asset_recovery_completion_rate": _ratio(len(recovered_exit_assets), len(exit_asset_assignments)),
        "offboarding_completion_rate": _ratio(int(exited.status.eq("completed").sum()), len(exited)),
        "audit_coverage_rate": _ratio(audited_relevant, audit_relevant),
        "anomaly_detection": {"true_positive": tp, "false_positive": fp, "false_negative": fn,
                              "precision": precision, "recall": recall, "f1": f1,
                              "undefined_denominator_policy": "null when a denominator is zero"},
        "metric_denominators": {
            "onboarding_completion_rate": "completed onboarding cases / all onboarding cases",
            "average_onboarding_completion_days": "mean completed_at minus opened_at, in days, over completed cases",
            "overdue_task_rate": "overdue or unfinished past-due tasks / all tasks (fixed reporting cutoff 2027-01-01 UTC)",
            "asset_recovery_completion_rate": "returned historical asset assignments for terminated employees / all historical asset assignments for terminated employees",
            "offboarding_completion_rate": "completed offboarding cases / all offboarding cases",
            "audit_coverage_rate": "completed tasks, onboarding cases, and offboarding cases with an entity audit event / all completed tasks and cases",
        },
    }
