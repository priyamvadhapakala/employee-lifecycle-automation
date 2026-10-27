"""Command-line entry point for generating and analyzing synthetic workflows."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from .anomaly_injector import inject_anomalies
from .config import PROJECT_ROOT, load_config, resolve_path
from .data_generator import generate_dataset
from .database_manager import create_database
from .exporter import export_tables
from .ground_truth_generator import write_ground_truth
from .metrics import calculate_metrics
from .reproducibility import check_reproducibility
from .validation_engine import validate_dataset

LOG = logging.getLogger("employee_lifecycle_automation")
TABLE_NAMES = ["Department", "Role", "Manager", "Employee", "OnboardingCase", "Task", "Dependency", "AccessRole",
               "AccessGrant", "Asset", "AssetAssignment", "OffboardingCase", "AuditEvent"]


def _load_saved(config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    generated = resolve_path(config["paths"]["generated_data"])
    tables = {name: pd.read_csv(generated / f"{name}.csv", keep_default_na=True) for name in TABLE_NAMES}
    gt_path = resolve_path(config["paths"]["ground_truth"]) / "ground_truth.csv"
    tables["GroundTruth"] = pd.read_csv(gt_path) if gt_path.exists() else pd.DataFrame()
    return tables


def _generate(config: dict[str, Any], mode: str, seed: int) -> dict[str, pd.DataFrame]:
    tables, ground_truth = inject_anomalies(generate_dataset(config, mode, seed), config["anomaly_injection"])
    tables["GroundTruth"] = ground_truth
    write_ground_truth(ground_truth, resolve_path(config["paths"]["ground_truth"]))
    db = create_database(tables, resolve_path(config["paths"]["database"]))
    metadata_path = resolve_path(config["paths"]["generated_data"]) / "run_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps({"mode": mode, "seed": seed, "anomaly_injection": config["anomaly_injection"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    LOG.info("Created %s with seed %s and database %s", mode, seed, db)
    return tables


def _saved_mode(config: dict[str, Any]) -> str:
    metadata = resolve_path(config["paths"]["generated_data"]) / "run_metadata.json"
    if metadata.exists():
        saved = json.loads(metadata.read_text(encoding="utf-8"))
        if saved.get("mode") in ("starter", "full"):
            return saved["mode"]
    return config["mode"]


def _validate(config: dict[str, Any], mode: str, tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    expected = config["dataset_sizes"][mode]
    checks, detections = validate_dataset(tables, mode, expected)
    path = resolve_path(config["paths"]["reports"]) / "validation_results.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    checks.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    print(f"Validation checks: {len(checks)}; violations: {int((~checks.passed).sum())}; detected anomaly records: {len(detections)}")
    print(f"Validation report: {path}")
    return checks, detections


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and validate synthetic employee lifecycle workflows")
    parser.add_argument("--config", default=None, help="Configuration JSON path (defaults to config/config.json)")
    parser.add_argument("--verbose", action="store_true", help="Enable informational log output")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("generate", "all"):
        command = sub.add_parser(name)
        command.add_argument("--mode", choices=("starter", "full"), default=None)
        command.add_argument("--seed", type=int, default=None)
    sub.add_parser("validate")
    sub.add_parser("metrics")
    sub.add_parser("export")
    sub.add_parser("reproduce").add_argument("--mode", choices=("starter", "full"), default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)
    mode = getattr(args, "mode", None) or config["mode"]
    seed = getattr(args, "seed", None)
    seed = config["seed"] if seed is None else seed

    if args.command == "generate":
        tables = _generate(config, mode, seed)
        export_tables(tables, config)
        print(f"Generated {mode} data using seed {seed}.")
    elif args.command == "all":
        tables = _generate(config, mode, seed)
        checks, detections = _validate(config, mode, tables)
        metrics = calculate_metrics(tables, checks, detections, tables["GroundTruth"])
        export_tables(tables, config, checks, metrics, detections)
        print(f"All pipeline stages finished. Reports: {resolve_path(config['paths']['reports'])}")
    elif args.command == "validate":
        mode = _saved_mode(config)
        tables = _load_saved(config)
        checks, detections = _validate(config, mode, tables)
        (resolve_path(config["paths"]["reports"]) / "detected_anomalies.csv").write_text(detections.to_csv(index=False, lineterminator="\n"), encoding="utf-8")
    elif args.command == "metrics":
        mode = _saved_mode(config)
        tables = _load_saved(config)
        checks, detections = validate_dataset(tables, mode, config["dataset_sizes"][mode])
        metrics = calculate_metrics(tables, checks, detections, tables["GroundTruth"])
        export_tables(tables, config, checks, metrics, detections)
        print(json.dumps(metrics, indent=2, sort_keys=True))
    elif args.command == "export":
        mode = _saved_mode(config)
        tables = _load_saved(config)
        checks, detections = validate_dataset(tables, mode, config["dataset_sizes"][mode])
        metrics = calculate_metrics(tables, checks, detections, tables["GroundTruth"])
        export_tables(tables, config, checks, metrics, detections)
        create_database(tables, resolve_path(config["paths"]["database"]))
        print("CSV, JSON, database, reports, and charts exported.")
    elif args.command == "reproduce":
        report = check_reproducibility(config, mode, seed)
        print(f"Reproducible: {report['identical']}; report: outputs/reports/reproducibility.json")
        return 0 if report["identical"] else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
