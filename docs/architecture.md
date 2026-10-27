# Architecture

## Pipeline shape

```text
config.json → config loader → seeded generator → workflow records
                                ↓
                       anomaly injector → separate ground truth
                                ↓
          SQLite database ← validator → detections / validation report
                                ↓
                         metrics → CSV/JSON exports and charts
                                ↓
                    reproducibility checksum comparison
```

`src/main.py` orchestrates the stages. `data_generator.py` creates master records first, then cases, tasks/dependencies, grants, assets/assignments, and audit events using both NumPy and Python random generators seeded from the same integer. Date ranges and timestamps are fixed in the synthetic 2026 calendar, not based on wall-clock time. IDs are formatting functions over deterministic sequence values.

`workflow_engine.py` contains explicit state-transition and access eligibility policies. The generator creates baseline valid records. `anomaly_injector.py` makes five targeted post-generation changes and creates labels through `ground_truth_generator.py`. `validation_engine.py` inspects the records and rules without reading ground-truth labels; only the metrics stage compares detections to labels.

`database_manager.py` recreates the SQLite database per generation and turns on foreign-key enforcement. Master records are loaded before dependents. Employee manager references are set after Manager records exist to resolve the organizational cycle. Ground truth is kept outside the operational database. `AuditEvent` uses a polymorphic entity reference; application validation handles that reference.

## Workflow policy

- Onboarding cases start 14 days before planned start. Baseline tasks use an acyclic prerequisite chain and completed tasks record approvals when required.
- Access effective dates cannot precede actual (or planned, for pending employees) start dates. Access roles with `approval_required=1` need an approval timestamp before provisioning.
- Equipment has a current state in Asset and a historical row in AssetAssignment. Delivery and acknowledgement follow assignment; returns keep the historical assignment row.
- Offboarding cases have urgency `normal` or `urgent`. Urgent exits target access revocation on the last working date; normal exits target the following day. The synthetic workflow records revocation and asset-recovery tasks.
- Employee and case state transitions are explicit in `workflow_engine.py`. Important generated transitions are written to append-only audit rows.

## Data and reproducibility boundaries

Operational table CSV files and per-entity JSON exports do not contain ground-truth labels. Ground truth is stored under `data/ground_truth`. Reproducibility hashes use deterministic row ordering and UTF-8 CSV serialization with LF line endings. Database binary files and chart binaries are not included in the canonical checksum comparison; SQLite and PNG encoders can vary by runtime/library version. Run metadata is also excluded.

## Scope limitations

The pipeline creates synthetic records only and has no external services, web framework, personal data input, authentication, or production HR integrations. `Employee.role_id` is the current role; role history is represented in audit events. The data set includes an `AssetAssignment` bridge in addition to the twelve requested business entities so asset assignment history and a multi-employee duplicate can be represented without violating the Asset primary key.
