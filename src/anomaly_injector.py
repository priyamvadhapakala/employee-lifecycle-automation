"""Inject the five specified, traceable business-rule anomalies."""

from __future__ import annotations

import pandas as pd

from .ground_truth_generator import make_ground_truth
from .id_generator import audit_event_id


def inject_anomalies(tables: dict[str, pd.DataFrame], enabled: bool = True) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    tables = {name: frame.copy(deep=True) for name, frame in tables.items()}
    if not enabled:
        return tables, make_ground_truth([])
    issues = []
    def audit(entity_type: str, entity_id: str, reason: str) -> None:
        events = tables["AuditEvent"]
        events.loc[len(events)] = {
            "audit_event_id": audit_event_id(len(events) + 1), "entity_type": entity_type,
            "entity_id": entity_id, "event_type": "anomaly_injected",
            "event_at": "2026-12-31T09:00:00Z", "actor": "synthetic.anomaly_injector",
            "old_value": None, "new_value": "injected_violation", "reason": reason,
        }
    def record(anomaly_id: str, issue_type: str, entity_type: str, entity_id: str,
               severity: str, reason: str, rule: str, affected: list[str]) -> None:
        issues.append({"anomaly_id": anomaly_id, "issue_type": issue_type, "entity_type": entity_type,
                       "entity_id": entity_id, "severity": severity, "reason": reason,
                       "expected_rule": rule, "affected_record_ids": affected})

    grants = tables["AccessGrant"]
    eligible = grants[grants["status"].eq("active")]
    if not eligible.empty:
        ix = eligible.index[0]
        grant = grants.loc[ix]
        employee = tables["Employee"].set_index("employee_id").loc[grant.employee_id]
        before = pd.Timestamp(employee.actual_start_date or employee.planned_start_date) - pd.Timedelta(days=2)
        grants.at[ix, "effective_from"] = before.strftime("%Y-%m-%dT09:00:00Z")
        audit("AccessGrant", grant.access_grant_id, "Deliberately injected early access effective date")
        record("ANOM-001", "access_before_start_or_approval", "AccessGrant", grant.access_grant_id, "high",
               "Grant effective date was moved before the employee start date.",
               "Access must be approved when required and effective on or after the employee start date.",
               [grant.access_grant_id, grant.employee_id])

    assignments = tables["AssetAssignment"]
    if not assignments.empty and len(tables["Employee"]) > 1:
        first = assignments.iloc[0]
        other = next(e for e in tables["Employee"].employee_id if e != first.employee_id)
        duplicate_id = f"ASG-{len(assignments) + 1:06d}"
        duplicate = first.copy()
        duplicate["asset_assignment_id"] = duplicate_id
        duplicate["employee_id"] = other
        duplicate["assignment_status"] = "assigned"
        duplicate["recovered_at"] = None
        assignments.loc[len(assignments)] = duplicate
        audit("Asset", first.asset_id, "Deliberately injected overlapping asset assignment")
        record("ANOM-002", "duplicate_asset_assignment", "Asset", first.asset_id, "high",
               "The same asset has two simultaneously active employee assignments.",
               "An asset may have at most one active assignment at a time.",
               [first.asset_id, first.asset_assignment_id, duplicate_id, first.employee_id, other])

    employees = tables["Employee"]
    terminated = employees[employees.employment_status.eq("terminated")]
    term_grants = grants[grants.employee_id.isin(terminated.employee_id)]
    if not term_grants.empty:
        ix = term_grants.index[0]
        grant = grants.loc[ix]
        grants.at[ix, "status"] = "active"
        grants.at[ix, "revoked_at"] = None
        grants.at[ix, "effective_to"] = None
        audit("AccessGrant", grant.access_grant_id, "Deliberately injected active grant after termination")
        record("ANOM-003", "terminated_employee_active_grant", "AccessGrant", grant.access_grant_id, "critical",
               "An active access grant was retained for a terminated employee.",
               "Terminated employees must not have active access grants.", [grant.access_grant_id, grant.employee_id])

    deps = tables["Dependency"]
    pairs = deps[deps.task_id.ne(deps.prerequisite_task_id)]
    if not pairs.empty:
        pair = pairs.iloc[0]
        new_id = f"DEP-{len(deps) + 1:06d}"
        deps.loc[len(deps)] = {"dependency_id": new_id, "task_id": pair.prerequisite_task_id,
                               "prerequisite_task_id": pair.task_id, "created_at": pair.created_at}
        audit("Task", pair.task_id, "Deliberately injected reverse prerequisite edge creating a cycle")
        record("ANOM-004", "circular_task_dependency", "Dependency", new_id, "high",
               "A reverse dependency was added, creating a two-task cycle.",
               "The task prerequisite graph must be acyclic.",
               [pair.task_id, pair.prerequisite_task_id, pair.dependency_id, new_id])

    assets = tables["Asset"]
    recovered = assets[assets.asset_status.eq("recovered")]
    if not recovered.empty:
        ix = recovered.index[0]
        asset = assets.loc[ix]
        assets.at[ix, "asset_status"] = "assigned"
        hit = assignments[assignments.asset_id.eq(asset.asset_id)]
        if not hit.empty:
            assignments.loc[hit.index[0], "assignment_status"] = "assigned"
            assignment_id = assignments.loc[hit.index[0], "asset_assignment_id"]
            assets.at[ix, "assigned_employee_id"] = assignments.loc[hit.index[0], "employee_id"]
            assets.at[ix, "assigned_at"] = assignments.loc[hit.index[0], "assigned_at"]
            assets.at[ix, "delivered_at"] = assignments.loc[hit.index[0], "delivered_at"]
            assets.at[ix, "acknowledged_at"] = assignments.loc[hit.index[0], "acknowledged_at"]
        else:
            assignment_id = ""
        audit("Asset", asset.asset_id, "Deliberately injected assigned state after recovery")
        record("ANOM-005", "recovered_asset_marked_assigned", "Asset", asset.asset_id, "high",
               "A recovered asset is still marked as assigned.",
               "Recovered assets must not retain an active assignment.",
               [asset.asset_id] + ([assignment_id] if assignment_id else []))

    tables["GroundTruth"] = make_ground_truth(issues)
    return tables, tables["GroundTruth"]
