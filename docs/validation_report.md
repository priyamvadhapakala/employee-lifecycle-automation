# Validation report guide

The command `python -m src.main validate` writes `outputs/reports/validation_results.csv` and `detected_anomalies.csv` for the most recent generated run.

Each result row contains:

- `check_id`, `check_name`: stable rule identifier and readable description.
- `passed`, `failed`: boolean outcome and count (one failed record per violation; successful aggregate checks have `failed=0`).
- `severity`: `info`, `high`, or `critical`.
- `affected_entity`, `affected_record_id`: entity and record under review.
- `explanation`: observed problem or success explanation.
- `expected_result`, `actual_result`: expected rule outcome and observed outcome.

Detected business-rule violations are retained even when they are deliberate injected anomalies. With default injection enabled, the five intended issue classes are expected to fail their checks. Other failures indicate a baseline defect or an unexpected issue and should be investigated separately. No label column is added to operational tables or used to run the checks.

## Expected injected issues

| ID | Issue | Expected severity | Validation family |
|---|---|---|---|
| ANOM-001 | Access effective before employee start | high | ACCESS_POLICY |
| ANOM-002 | One asset has active assignments to multiple employees | high | ASSET_DUPLICATE |
| ANOM-003 | Terminated employee retains active access | critical | ACCESS_POLICY |
| ANOM-004 | Circular task prerequisite path | high | TASK_CYCLE |
| ANOM-005 | Recovered asset assignment remains active | high | ASSET_RECOVERY |

## Report template

| Run mode | Seed | Total rows | Failed checks | Unexpected failures | Detected anomaly records | Ground-truth anomaly count | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fill from run metadata | | | | | | | | | |

Metrics are calculated from generated records. Precision/recall/F1 are calculated only after independent validation, by comparing issue type and entity ID against ground truth. A metric with a zero denominator is `null`.

## Verified run (2026-10-26)

Commands run from the project root: `python -m pytest -q`; `python -m src.main all --mode starter --seed 20261022`; `python -m src.main all --mode full --seed 20261022`; `python -m src.main validate`; `python -m src.main metrics`; `python -m src.main export`; and `python -m src.main reproduce --mode full`.

- Tests: **14 passed**.
- Starter: 30 employees, 120 tasks, 45 access grants, and 36 assets. The pipeline reported 5 intended violations and 5 detected anomaly records.
- Full: 1,000 employees, 8,000 tasks, 1,500 access grants, and 1,200 assets. It reported 5 intended violations and 5 detected anomaly records.
- Detected issue/entity pairs matched all five ground-truth records: 5 true positives, 0 false positives, 0 false negatives; precision, recall, and F1 were each 1.0.
- SQLite `PRAGMA foreign_key_check` returned no violations.
- Full-mode canonical generated records reproduced identically with seed `20261022` (`identical: true`). The checksum report excludes database and chart binaries and run metadata.
- Full-mode calculated metrics: onboarding completion 0.931; average completed onboarding duration 14.467 days; overdue task rate 0.069; offboarding completion 1.0; audit coverage 1.0; asset recovery completion 0.9889. Rate formulas and denominators are listed in `outputs/reports/metrics.json`.

The five validation failures in the generated report are expected deliberate anomaly findings. The other checks passed. This distinction is based on check family and independently detected operational records; ground-truth labels are not validator inputs.
