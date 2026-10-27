# Employee Lifecycle Automation

A reproducible Python pipeline for synthetic employee onboarding and offboarding data. It models HR, IT, and Facilities work, records approvals and audit history, injects five labeled business-rule anomalies, validates the result, and exports CSV, JSON, SQLite, reports, and charts. It uses synthetic names and `example.test` email addresses only.

## Features

- Starter and full datasets, controlled by a fixed random seed (default `20261022`).
- Relational SQLite schema with foreign-key enforcement, checks, uniqueness constraints, and indexes.
- Explicit onboarding/offboarding and access approval policies.
- Five deliberate, separately labeled anomalies with stable identifiers and an independent rule-based validator.
- CSV/JSON data exports, validation results, metrics, charts, and SHA-256 reproducibility report.
- Pytest coverage for dataset sizes, relationships, rules, anomalies, and deterministic output.

## Technology

Python 3.11 or newer compatible Python, pandas, NumPy, SQLite (Python standard library), Matplotlib, argparse, logging, JSON/CSV, and pytest.

## Project layout

```text
employee_lifecycle_automation/
├── config/config.json
├── data/{generated,ground_truth,exports}/
├── database/{schema.sql,seed.sql}
├── docs/{architecture.md,data_dictionary.md,validation_report.md,source_manifest.md}
├── logs/
├── outputs/{reports,charts}/
├── src/{main,config,id_generator,data_generator,database_manager,workflow_engine,
│       anomaly_injector,ground_truth_generator,validation_engine,metrics,exporter,reproducibility}.py
├── tests/
├── requirements.txt
└── README.md
```

## Windows installation

Open PowerShell in the folder where the repository/project folder should live:

```powershell
$project = "employee_lifecycle_automation"
$directories = @("config", "data/generated", "data/ground_truth", "data/exports", "database", "docs", "logs", "outputs/reports", "outputs/charts", "src", "tests")
New-Item -ItemType Directory -Force -Path $project | Out-Null
foreach ($directory in $directories) { New-Item -ItemType Directory -Force -Path (Join-Path $project $directory) | Out-Null }
Set-Location $project
py -3 -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks venv activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again. Or call `.\.venv\Scripts\python.exe` directly. Command Prompt equivalent:

```bat
mkdir employee_lifecycle_automation\config
mkdir employee_lifecycle_automation\data\generated
mkdir employee_lifecycle_automation\data\ground_truth
mkdir employee_lifecycle_automation\data\exports
mkdir employee_lifecycle_automation\database
mkdir employee_lifecycle_automation\docs
mkdir employee_lifecycle_automation\logs
mkdir employee_lifecycle_automation\outputs\reports
mkdir employee_lifecycle_automation\outputs\charts
mkdir employee_lifecycle_automation\src
mkdir employee_lifecycle_automation\tests
cd employee_lifecycle_automation
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Commands

Run commands from the project directory. The CLI reads `config/config.json`; `--mode` and `--seed` override its generation settings.

```powershell
python -m src.main generate --mode starter --seed 20261022
python -m src.main generate --mode full --seed 20261022
python -m src.main all --mode starter --seed 20261022
python -m src.main all --mode full --seed 20261022
python -m src.main validate
python -m src.main metrics
python -m src.main export
python -m src.main reproduce --mode starter
python -m pytest -q
```

`all` generates a fresh dataset, applies configured anomaly injection, writes the SQLite database, validates records, calculates metrics, and produces exports and charts. `generate` writes generated tables, ground truth, and the database without running validation/metrics. The later `validate`, `metrics`, and `export` commands use the latest saved run's mode from `data/generated/run_metadata.json`. They do not append or duplicate rows. `reproduce` generates twice in memory and compares canonical CSV row counts and SHA-256 hashes; its report is `outputs/reports/reproducibility.json`.

Anomaly injection can be disabled by setting `"anomaly_injection": false` in config. Then ground-truth files are empty, the baseline should validate without business-rule violations, and detection precision/recall are null when their denominators are zero.

## Output locations

- `data/generated/*.csv`: one UTF-8 CSV for every operational entity, including AssetAssignment.
- `data/exports/*.json`: record-oriented JSON per operational entity.
- `data/ground_truth/ground_truth.csv` and `.json`: labels only; never included in operational tables.
- `database/employee_lifecycle.db`: fresh SQLite database for the latest run, foreign keys enabled.
- `database/schema.sql` and `database/seed.sql`: relational schema and stable vocabulary seed.
- `outputs/reports/validation_results.csv`, `detected_anomalies.csv`, `metrics.json`, `summary_report.csv`, and reproducibility report.
- `outputs/charts/entity_record_counts.png` and `anomaly_metrics.png`.

All run dates and timestamps are generated from a fixed 2026 synthetic date window. `run_metadata.json` records mode, seed, and anomaly setting and is intentionally excluded from generated-record checksums.

## Metric definitions

- Onboarding completion rate: completed onboarding cases / all onboarding cases.
- Average completion time: mean `completed_at - opened_at` in days for completed onboarding cases.
- Overdue task rate: unfinished tasks past the fixed reporting cutoff of 2027-01-01 UTC, plus tasks explicitly marked overdue, divided by all tasks.
- Dependency violation count: failed cycle and prerequisite checks.
- Access-policy violation count: grants failing required approval, start-date, or eligible-employee rules.
- Active grants linked to terminated employees: number of active grants for terminated employee IDs.
- Duplicate asset assignment count: assets with active assignments to more than one distinct employee.
- Asset recovery completion rate: returned historical asset assignments for terminated employees / all historical assignments for terminated employees.
- Offboarding completion rate: completed offboarding cases / all offboarding cases.
- Audit coverage rate: applicable completed tasks and cases with audit coverage / all applicable completed task and case records.
- Precision, recall, and F1: anomaly detections compared with ground truth by issue type and entity ID. Undefined zero-denominator values are JSON `null`.

See [docs/architecture.md](docs/architecture.md), [docs/data_dictionary.md](docs/data_dictionary.md), [docs/validation_report.md](docs/validation_report.md), and [docs/source_manifest.md](docs/source_manifest.md) for design details, constraints, and limitations.

## Known limitations

This is a local synthetic-data reference pipeline, not an HRIS or identity provider integration. Emails, names, approvals, and assets are generated examples. Audit event entity links are polymorphic and validated in Python. Employee role changes are represented by current role plus audit events rather than a temporal role-assignment table. AssetAssignment preserves assignment history; the Asset row represents its current state. The urgent-exit policy is a same-day revocation target, while normal exits use the next-day target. SQLite date rules depend on normalized ISO date/timestamp strings.
