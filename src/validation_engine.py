"""Rule-based data-quality and anomaly validation independent of ground truth."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

import pandas as pd


def validate_dataset(tables: dict[str, pd.DataFrame], mode: str = "starter", expected_counts: dict[str, int] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return structured checks and independently detected anomaly records."""
    checks: list[dict[str, Any]] = []
    detections: list[dict[str, Any]] = []
    def issue(check_id: str, name: str, entity: str, record: str, explanation: str,
              severity: str = "high", check_name: str | None = None) -> None:
        checks.append({"check_id": check_id, "check_name": check_name or name, "passed": False, "failed": 1,
                       "severity": severity, "entity_type": entity, "entity_id": record,
                       "affected_entity": entity, "affected_record_id": record,
                       "explanation": explanation, "expected_result": "rule satisfied", "actual_result": "violation"})
    def detect(issue_type: str, entity: str, entity_id: str, affected: list[str], reason: str) -> None:
        detections.append({"issue_type": issue_type, "entity_type": entity, "entity_id": entity_id,
                           "affected_record_ids": json.dumps(affected, separators=(",", ":")), "reason": reason})
    def passcheck(cid: str, name: str, entity: str, actual: Any = "no violations") -> None:
        checks.append({"check_id": cid, "check_name": name, "passed": True, "failed": 0,
                       "severity": "info", "entity_type": entity, "entity_id": "",
                       "affected_entity": entity, "affected_record_id": "",
                       "explanation": "No violations found.", "expected_result": "rule satisfied", "actual_result": str(actual)})

    # Key uniqueness and required values.
    for table_name, frame in tables.items():
        if table_name == "GroundTruth":
            continue
        if "" in frame.columns:
            pass
        pk = frame.columns[0] if len(frame.columns) else None
        if pk and frame[pk].duplicated().any():
            for value in frame.loc[frame[pk].duplicated(keep=False), pk].astype(str).unique():
                issue("PK_UNIQUE", "Primary key uniqueness", table_name, value, f"Duplicate {pk} value.")
        else:
            passcheck("PK_UNIQUE", "Primary key uniqueness", table_name)
        unique_constraints = {"Employee": [["email"]], "Department": [["department_name"], ["cost_center"]],
                              "Role": [["role_name"]], "OnboardingCase": [["employee_id"]],
                              "Dependency": [["task_id", "prerequisite_task_id"]],
                              "AccessRole": [["role_name"]], "Asset": [["serial_number"]]}
        for unique_columns in unique_constraints.get(table_name, []):
            if all(column in frame for column in unique_columns):
                duplicates = frame[frame[unique_columns].notna().all(axis=1) & frame.duplicated(unique_columns, keep=False)]
                for _, duplicate in duplicates.iterrows():
                    values = tuple(duplicate[column] for column in unique_columns)
                    issue("UNIQUE_CONSTRAINT", f"Unique {' + '.join(unique_columns)}", table_name,
                          str(duplicate.iloc[0]), f"Duplicate unique value {values!r}.")
        id_patterns = {
            "Department": r"DEPT-\d{3}", "Role": r"ROLE-\d{3}", "Manager": r"MGR-\d{3}",
            "Employee": r"EMP-\d{6}", "OnboardingCase": r"ONB-\d{4}-\d{6}",
            "Task": r"TASK-(?:ONB|OFF)-\d{4}-\d{6}-\d{3}", "Dependency": r"DEP-\d{6}",
            "AccessRole": r"AROLE-\d{3}", "AccessGrant": r"GRANT-EMP-\d{6}-\d{3}",
            "Asset": r"AST-\d{6}", "AssetAssignment": r"ASG-\d{6}",
            "OffboardingCase": r"OFF-\d{4}-\d{6}", "AuditEvent": r"AUD-\d{9}",
        }
        pattern = id_patterns.get(table_name)
        if pattern:
            bad_ids = frame[~frame.iloc[:, 0].astype(str).map(lambda value: re.fullmatch(pattern, value) is not None)]
            if bad_ids.empty:
                passcheck("ID_FORMAT", "Deterministic ID format", table_name)
            else:
                for _, row in bad_ids.iterrows():
                    issue("ID_FORMAT", "Deterministic ID format", table_name, str(row.iloc[0]), f"Identifier does not match {pattern}.")
        required = [c for c in frame.columns if c not in {"manager_id", "actual_start_date", "termination_date", "completed_at", "onboarding_case_id", "offboarding_case_id", "approved_by", "approved_at", "old_value", "new_value", "effective_to", "revoked_at", "source_task_id", "assigned_employee_id", "assigned_at", "delivered_at", "acknowledged_at", "recovered_at", "active_to"}]
        missing = [c for c in required if c in frame and frame[c].isna().any()]
        if missing:
            for ix in frame.index[frame[missing].isna().any(axis=1)]:
                issue("REQUIRED_FIELDS", "Required fields present", table_name, str(frame.iloc[ix, 0]), f"Null required fields: {missing}")
        enums = {
            "Role": {"employment_type_default": {"full_time", "contractor"}},
            "Employee": {"employment_type": {"full_time", "contractor"}, "employment_status": {"pending", "active", "completed", "terminated"}},
            "OnboardingCase": {"status": {"planned", "in_progress", "blocked", "completed", "cancelled"}},
            "Task": {"owner_team": {"HR", "IT", "Facilities", "Manager"}, "status": {"blocked", "pending", "in_progress", "completed", "cancelled", "overdue"}, "priority": {"low", "normal", "high", "urgent"}},
            "AccessGrant": {"status": {"pending", "active", "revoked", "denied", "expired"}},
            "Asset": {"asset_type": {"laptop", "phone", "badge", "monitor", "accessory"}, "asset_status": {"available", "assigned", "in_transit", "recovered", "retired", "lost"}},
            "AssetAssignment": {"assignment_status": {"assigned", "returned", "cancelled"}},
            "OffboardingCase": {"exit_type": {"resignation", "termination", "contract_end", "retirement"}, "urgency": {"normal", "urgent"}, "status": {"planned", "in_progress", "blocked", "completed", "cancelled"}},
            "AuditEvent": {"entity_type": {"Employee", "OnboardingCase", "Task", "AccessGrant", "Asset", "OffboardingCase"}},
        }
        for column, allowed in enums.get(table_name, {}).items():
            invalid = frame[frame[column].notna() & ~frame[column].isin(allowed)]
            for _, row in invalid.iterrows():
                issue("ENUM_VALUES", "Allowed lifecycle and enum values", table_name, str(row.iloc[0]),
                      f"{column}={row[column]!r} is outside {sorted(allowed)}.")

    relations = {
        "Employee": [("department_id", "Department", "department_id"), ("role_id", "Role", "role_id"), ("manager_id", "Manager", "manager_id")],
        "Manager": [("employee_id", "Employee", "employee_id")],
        "OnboardingCase": [("employee_id", "Employee", "employee_id")],
        "Task": [("onboarding_case_id", "OnboardingCase", "onboarding_case_id"), ("offboarding_case_id", "OffboardingCase", "offboarding_case_id")],
        "Dependency": [("task_id", "Task", "task_id"), ("prerequisite_task_id", "Task", "task_id")],
        "AccessGrant": [("employee_id", "Employee", "employee_id"), ("access_role_id", "AccessRole", "access_role_id"), ("source_task_id", "Task", "task_id")],
        "Asset": [("assigned_employee_id", "Employee", "employee_id")],
        "AssetAssignment": [("asset_id", "Asset", "asset_id"), ("employee_id", "Employee", "employee_id")],
        "OffboardingCase": [("employee_id", "Employee", "employee_id")],
    }
    for child, refs in relations.items():
        frame = tables[child]
        for col, parent, parent_col in refs:
            valid = set(tables[parent][parent_col].dropna())
            bad = frame[frame[col].notna() & ~frame[col].isin(valid)]
            for _, row in bad.iterrows():
                issue("FK_INTEGRITY", "Foreign key integrity", child, str(row.iloc[0]), f"{col} references missing {parent}.{parent_col}.")
    if not any(row["check_id"] == "FK_INTEGRITY" and not row["passed"] for row in checks):
        passcheck("FK_INTEGRITY", "Foreign key integrity", "all entities")

    task_rows = tables["Task"]
    bad_case_refs = task_rows[task_rows.onboarding_case_id.notna() == task_rows.offboarding_case_id.notna()]
    for _, task in bad_case_refs.iterrows():
        issue("TASK_CASE_REFERENCE", "Task belongs to exactly one case", "Task", str(task.task_id),
              "Task must reference exactly one onboarding or offboarding case.")
    if bad_case_refs.empty:
        passcheck("TASK_CASE_REFERENCE", "Task belongs to exactly one case", "Task")

    employees = tables["Employee"].set_index("employee_id", drop=False)
    tasks = tables["Task"].set_index("task_id", drop=False)
    grants = tables["AccessGrant"]
    # Date and access policy rules.
    policy_issue = False
    for _, grant in grants.iterrows():
        emp = employees.loc[grant.employee_id]
        start = emp.actual_start_date or emp.planned_start_date
        access = tables["AccessRole"].set_index("access_role_id").loc[grant.access_role_id]
        reasons = []
        if grant.status == "active" and pd.Timestamp(grant.effective_from).date() < pd.Timestamp(start).date():
            reasons.append("grant effective before employee start")
        if grant.status == "active" and int(access.approval_required) and pd.isna(grant.approved_at):
            reasons.append("required approval missing")
        if grant.status == "active" and emp.employment_status == "terminated":
            reasons.append("active grant belongs to terminated employee")
        if pd.notna(grant.approved_at) and pd.Timestamp(grant.approved_at) > pd.Timestamp(grant.effective_from):
            reasons.append("grant effective before required approval timestamp")
        if pd.notna(grant.effective_to) and pd.Timestamp(grant.effective_to) < pd.Timestamp(grant.effective_from):
            reasons.append("grant effective end precedes effective start")
        for reason in reasons:
            policy_issue = True
            issue("ACCESS_POLICY", "Access policy compliance", "AccessGrant", grant.access_grant_id, reason,
                  "critical" if "terminated" in reason else "high")
            if "before employee start" in reason:
                detect("access_before_start_or_approval", "AccessGrant", grant.access_grant_id,
                       [grant.access_grant_id, grant.employee_id], reason)
            if "terminated" in reason:
                detect("terminated_employee_active_grant", "AccessGrant", grant.access_grant_id,
                       [grant.access_grant_id, grant.employee_id], reason)
    if not policy_issue:
        passcheck("ACCESS_POLICY", "Access approval and effective-date rules", "AccessGrant")

    # Task prerequisite checks and directed cycle detection.
    deps = tables["Dependency"]
    adjacency: dict[str, list[str]] = defaultdict(list)
    for _, dep in deps.iterrows():
        adjacency[dep.prerequisite_task_id].append(dep.task_id)
        if tasks.loc[dep.task_id].status == "completed" and tasks.loc[dep.prerequisite_task_id].status != "completed":
            issue("TASK_PREREQUISITE", "Task prerequisites completed first", "Task", dep.task_id,
                  f"Prerequisite {dep.prerequisite_task_id} is not completed.")
    state: dict[str, int] = {}
    cycles: list[list[str]] = []
    def visit(node: str, stack: list[str]) -> None:
        if state.get(node) == 1:
            cycles.append(stack[stack.index(node):] + [node] if node in stack else stack + [node])
            return
        if state.get(node) == 2:
            return
        state[node] = 1
        for child in adjacency[node]:
            visit(child, stack + [node])
        state[node] = 2
    for tid in tasks.index:
        visit(tid, [])
    for cycle in cycles:
        issue("TASK_CYCLE", "Task dependency graph is acyclic", "Dependency", cycle[0], f"Cycle detected: {' -> '.join(cycle)}")
        cycle_tasks = set(cycle)
        cycle_edges = deps[deps.task_id.isin(cycle_tasks) & deps.prerequisite_task_id.isin(cycle_tasks)]
        edge_id = cycle_edges.dependency_id.astype(str).max() if not cycle_edges.empty else cycle[0]
        detect("circular_task_dependency", "Dependency", edge_id,
               cycle + cycle_edges.dependency_id.astype(str).tolist(), "Task dependency graph contains a cycle.")
    if not cycles:
        passcheck("TASK_CYCLE", "Task dependency graph is acyclic", "Dependency")

    # Asset assignment reconciliation.
    assignments = tables["AssetAssignment"]
    active_assignments = assignments[assignments.assignment_status.eq("assigned")]
    for aid, group in active_assignments.groupby("asset_id"):
        if group.employee_id.nunique() > 1:
            ids = [aid] + group.asset_assignment_id.astype(str).tolist() + group.employee_id.astype(str).tolist()
            issue("ASSET_DUPLICATE", "No duplicate active asset assignments", "Asset", aid, "Asset is actively assigned to multiple employees.")
            detect("duplicate_asset_assignment", "Asset", aid, ids, "Asset is actively assigned to multiple employees.")
    assets = tables["Asset"].set_index("asset_id")
    for _, assignment in assignments.iterrows():
        asset = assets.loc[assignment.asset_id]
        if pd.notna(assignment.acknowledged_at) and pd.isna(assignment.delivered_at):
            issue("ASSET_DELIVERY", "Asset acknowledgement follows delivery", "AssetAssignment",
                  str(assignment.asset_assignment_id), "Acknowledgement exists without a delivery timestamp.")
        if pd.notna(assignment.recovered_at) and assignment.assignment_status == "assigned":
            issue("ASSET_RECOVERY", "Asset recovery reconciliation", "Asset", assignment.asset_id,
                  "Recovered asset assignment remains marked assigned.")
            detect("recovered_asset_marked_assigned", "Asset", assignment.asset_id,
                   [assignment.asset_id, assignment.asset_assignment_id], "Recovered asset still has active assignment status.")
    for asset_id, asset in assets.iterrows():
        if asset.asset_status == "recovered" and pd.notna(asset.assigned_employee_id):
            issue("ASSET_RECOVERY", "Asset recovery reconciliation", "Asset", str(asset_id),
                  "Asset marked recovered still has an assigned employee.")
        active = active_assignments[active_assignments.asset_id.eq(asset_id)]
        if asset.asset_status == "assigned" and pd.notna(asset.assigned_employee_id):
            if active.empty or not active.employee_id.eq(asset.assigned_employee_id).any():
                issue("ASSET_RECONCILIATION", "Asset current state matches assignment history", "Asset", str(asset_id),
                      "Asset current assignee has no matching active assignment record.")
    if active_assignments.groupby("asset_id").employee_id.nunique().le(1).all():
        passcheck("ASSET_DUPLICATE", "No duplicate active asset assignments", "AssetAssignment")

    # Lifecycle, offboarding completion and audit coverage.
    for _, employee in tables["Employee"].iterrows():
        if pd.Timestamp(employee.planned_start_date).date() < pd.Timestamp(employee.hire_date).date():
            issue("DATE_ORDER", "Employee dates are chronologically valid", "Employee", employee.employee_id,
                  "Planned start date precedes hire date.")
        if pd.notna(employee.actual_start_date) and pd.Timestamp(employee.actual_start_date).date() < pd.Timestamp(employee.hire_date).date():
            issue("DATE_ORDER", "Employee dates are chronologically valid", "Employee", employee.employee_id,
                  "Actual start date precedes hire date.")
        if pd.notna(employee.termination_date) and pd.Timestamp(employee.termination_date).date() < pd.Timestamp(employee.actual_start_date).date():
            issue("DATE_ORDER", "Employee dates are chronologically valid", "Employee", employee.employee_id,
                  "Termination date precedes actual start date.")
        if employee.employment_status == "terminated" and not employee.termination_date:
            issue("EMPLOYMENT_LIFECYCLE", "Employment status and dates reconcile", "Employee", employee.employee_id,
                  "Terminated employee has no termination date.")
    off = tables["OffboardingCase"]
    completed_cases = tables["OnboardingCase"][tables["OnboardingCase"].status.eq("completed")]
    for _, case in off.iterrows():
        if pd.Timestamp(case.last_working_date).date() < pd.Timestamp(case.opened_at).date():
            issue("DATE_ORDER", "Offboarding dates are chronologically valid", "OffboardingCase", case.offboarding_case_id,
                  "Last working date precedes offboarding case opening.")
        if case.status == "completed":
            case_tasks = tables["Task"][tables["Task"].offboarding_case_id.eq(case.offboarding_case_id)]
            if case_tasks.empty or not case_tasks.status.eq("completed").all():
                issue("OFFBOARDING_COMPLETE", "Completed exits have completed tasks", "OffboardingCase", case.offboarding_case_id,
                      "Offboarding marked complete with unfinished or missing tasks.")
    audited = set(zip(tables["AuditEvent"].entity_type, tables["AuditEvent"].entity_id))
    for _, case in completed_cases.iterrows():
        if ("OnboardingCase", case.onboarding_case_id) not in audited:
            issue("AUDIT_COVERAGE", "Important changes have audit events", "OnboardingCase", case.onboarding_case_id,
                  "Onboarding case state lacks an audit event.")
    for _, case in off[off.status.eq("completed")].iterrows():
        if ("OffboardingCase", case.offboarding_case_id) not in audited:
            issue("AUDIT_COVERAGE", "Important changes have audit events", "OffboardingCase", case.offboarding_case_id,
                  "Offboarding case state lacks an audit event.")
    for _, task in tasks.iterrows():
        if task.status == "completed" and ("Task", task.task_id) not in audited:
            issue("AUDIT_COVERAGE", "Important changes have audit events", "Task", task.task_id,
                  "Completed task lacks an audit event.")

    # Ground-truth references are checked, but never used to produce detections.
    gt = tables.get("GroundTruth", pd.DataFrame())
    entity_id_columns = {name: frame.columns[0] for name, frame in tables.items() if name != "GroundTruth" and len(frame.columns)}
    for _, label in gt.iterrows():
        entity_frame = tables.get(str(label.entity_type))
        id_column = entity_id_columns.get(str(label.entity_type))
        if entity_frame is None or id_column is None or str(label.entity_id) not in set(entity_frame[id_column].astype(str)):
            issue("GROUND_TRUTH_REFERENCE", "Ground-truth references existing records", str(label.entity_type), str(label.entity_id),
                  "Ground-truth entity reference does not resolve.")
    if len(gt) == 0 or not any(row["check_id"] == "GROUND_TRUTH_REFERENCE" and not row["passed"] for row in checks):
        passcheck("GROUND_TRUTH_REFERENCE", "Ground-truth references existing records", "GroundTruth")

    if expected_counts:
        aliases = {"employees": "Employee", "tasks": "Task", "access_grants": "AccessGrant", "assets": "Asset"}
        for key, table in aliases.items():
            expected = expected_counts.get(key)
            if expected is not None and len(tables[table]) != expected:
                issue("ROW_COUNTS", "Required dataset row counts", table, "", f"Expected {expected} rows, found {len(tables[table])}.")
            else:
                passcheck("ROW_COUNTS", f"Required {key} row count", table, len(tables[table]))
    return pd.DataFrame(checks), pd.DataFrame(detections, columns=["issue_type", "entity_type", "entity_id", "affected_record_ids", "reason"])
