"""Compare deterministic canonical exports from repeated seeded generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .anomaly_injector import inject_anomalies
from .config import PROJECT_ROOT
from .data_generator import generate_dataset
from .exporter import frame_sort_column


def _digest_tables(tables: dict) -> dict[str, dict[str, Any]]:
    result = {}
    for name in sorted(k for k in tables if k != "GroundTruth"):
        frame = tables[name]
        if len(frame):
            frame = frame.sort_values(frame_sort_column(frame), kind="stable")
        content = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
        result[name + ".csv"] = {"rows": int(len(frame)), "sha256": hashlib.sha256(content).hexdigest()}
    gt = tables.get("GroundTruth")
    if gt is not None:
        content = gt.to_csv(index=False, lineterminator="\n").encode("utf-8")
        result["ground_truth.csv"] = {"rows": int(len(gt)), "sha256": hashlib.sha256(content).hexdigest()}
    return result


def check_reproducibility(config: dict, mode: str | None = None, seed: int | None = None) -> dict[str, Any]:
    chosen_mode = mode or config["mode"]
    chosen_seed = config["seed"] if seed is None else int(seed)
    first, _ = inject_anomalies(generate_dataset(config, chosen_mode, chosen_seed), config["anomaly_injection"])
    second, _ = inject_anomalies(generate_dataset(config, chosen_mode, chosen_seed), config["anomaly_injection"])
    one, two = _digest_tables(first), _digest_tables(second)
    report = {"mode": chosen_mode, "seed": chosen_seed, "identical": one == two,
              "first_run": one, "second_run": two,
              "metadata_policy": "This report is written after comparison and is excluded from its own checksums."}
    path = PROJECT_ROOT / "outputs" / "reports" / "reproducibility.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
