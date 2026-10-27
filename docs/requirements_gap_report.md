# Requirements gap report

## Inspection baseline

- Repository: `employee_lifecycle_automation`; the existing architecture is a seeded Python generator, workflow policy helpers, anomaly injector, independent validator, metrics/export pipeline, SQLite schema, and pytest suite.
- Baseline test run: `python -m pytest -q` — **10 passed**.
- Configuration already sets seed `20261022`, starter size 30 employees / 120 tasks / 45 access grants / 36 assets, and full size 1,000 / 8,000 / 1,500 / 1,200.
- Existing generated CSV, report, and chart outputs are present. The CSV file names and export code show both operational CSV/JSON exports and separate ground truth. A successful, current full pipeline and its exact saved record counts have not yet been independently verified in this inspection.

## Requirements status

| Requirement area | Status | Evidence and gap |
|---|---|---|
| Existing structure and documentation | Mostly satisfied | README, data dictionary, architecture, validation guide, manifest, schema, seed, CLI, and tests exist. This report is added before implementation changes as requested. Documentation has a few report-definition mismatches noted below. |
| Five deterministic anomalies and separate truth | Partially satisfied | Injector creates five stable IDs and independent operational changes; truth is written separately. Need verify detection identity/issue type, baseline foreign keys after injection, and corrected recovered-asset path. |
| Structured validation | Partially satisfied | Validator checks PK formats, required values, enums, many FKs, access policies, dependencies, assets, lifecycle, audit, truth references, and key counts. Result columns are `affected_entity`/`affected_record_id`, duplicate-PK logic assumes first column is PK, some FKs/uniqueness/chronology cases are not covered, and missing columns/rows may raise rather than become findings. |
| Workflow and audit | Partially satisfied | Transition/access/deadline helpers exist and the generator emits tasks and audit records. Need verify dependency rules, approval evidence, assignment/recovery reconciliation and audit completeness; urgent exit behavior is described but not yet verified against generated records. |
| Evaluation metrics | Partially satisfied | Counts, completion rates, overdue/dependency/access/asset/offboarding/audit metrics and precision/recall/F1 exist. Gaps include explicit named counts for employees/tasks/grants/assets, metric numerator/denominator coverage, audit denominator alignment, and anomaly score matching beyond issue type + entity ID (ground-truth stable anomaly IDs are not carried into detections). |
| Dataset requirements | Configured; verification pending | Full required sizes are configured. Need run full generation and assert exact counts, and inspect edge cases around zero/full table counts. Starter mode exists. |
| Reproducibility | Mostly satisfied | Fixed seed, stable ordering, canonical CSV SHA-256 and repeated in-memory generation are implemented. Need execute the requested command and verify checksums; database/report/chart binaries are intentionally excluded. |
| Exports and reports | Mostly satisfied | Operational CSV/JSON, SQLite, SQL schema/seed, validation/detections/metrics, charts, HTML, and reproducibility report paths are implemented. Need verify actual reports, CSV metrics export semantics, and refresh documentation with run results. |
| Automated tests | Partially satisfied | Ten real tests pass, covering baseline counts, FKs, injected issue classes, workflow helpers and reproducibility. Missing direct assertions for many invalid records, audit, asset/access reconciliation, start/approval edge cases, exact detection identity, and broader CLI/full-mode behavior. |
| CLI compatibility | Implemented; verification pending | `all`, `validate`, `metrics`, `export`, `reproduce`, and starter/full options exist. Must run the requested pipeline commands and ensure command output/files agree. |

## Concrete defects or risks found before changes

1. The validator still identifies a table's primary-key column by its first column; this matches current generated table order but could be brittle if schemas are reordered.
2. Validation covers task case ownership, the configured unique constraints, delivery acknowledgement order, and current asset-to-assignment reconciliation. Tests do not yet mutate every date/state branch.

The metrics compare independent detections with ground truth by `(issue_type, entity_id)`. The entity ID is the stable operational identifier, and the anomaly ID remains a label-only identifier, so it is not provided to the detector.

The recovered-asset validator uses the asset index label as the ID. This works with the current indexed table but obscures the source of the identifier; implementation makes that explicit while updating the result schema.

## Planned implementation order

1. Harden structured validation and fix concrete record-handling defects while preserving existing table/CLI conventions.
2. Align metrics and stable ground-truth evaluation with validator output; update targeted tests.
3. Run starter and full pipelines, validation, metrics, exports, and reproducibility checks; update validation and architecture documentation with measured results and limitations.

## Completion update

Implemented structured entity fields (keeping the prior aliases for compatibility), checks for modeled unique constraints and exactly-one-case task ownership, explicit asset ID use in recovery findings, delivery and assignment reconciliation, entity-specific ground-truth references, explicit entity counts, and audit coverage computed from its actual applicable records. Added tests for per-anomaly identity matching, validation result fields, duplicate email detection, and metric counts/audit rates. Corrected Dependency uniqueness validation to respect its composite key.

The final verified runs and metrics are recorded in `validation_report.md`. Remaining test-coverage limitations: the suite does not yet independently mutate every lifecycle, approval, audit, and asset date/state rule; it covers the starter anomaly set, foreign keys, full/starter sizes, the access policy helper, unexpected email duplication, and deterministic generation.
