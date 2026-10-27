"""Ground-truth record creation from explicit injected issue records."""

import json
from pathlib import Path

import pandas as pd

GROUND_TRUTH_COLUMNS = ["anomaly_id", "issue_type", "entity_type", "entity_id", "expected_label",
                        "severity", "reason", "expected_rule", "affected_record_ids"]


def make_ground_truth(issues: list[dict]) -> pd.DataFrame:
    rows = []
    for issue in issues:
        rows.append({**issue, "expected_label": 1,
                     "affected_record_ids": json.dumps(issue["affected_record_ids"], separators=(",", ":"))})
    return pd.DataFrame(rows, columns=GROUND_TRUTH_COLUMNS)


def write_ground_truth(frame: pd.DataFrame, directory: str | Path) -> None:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    frame.to_csv(directory / "ground_truth.csv", index=False, encoding="utf-8", lineterminator="\n")
    records = frame.to_dict("records")
    for row in records:
        row["expected_label"] = int(row["expected_label"])
        row["affected_record_ids"] = json.loads(row["affected_record_ids"])
    (directory / "ground_truth.json").write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
