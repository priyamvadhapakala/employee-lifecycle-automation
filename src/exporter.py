"""Stable CSV/JSON exports and compact metrics charts."""

from __future__ import annotations

import json
import html
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .config import PROJECT_ROOT, resolve_path
from .ground_truth_generator import write_ground_truth


def export_tables(tables: dict[str, pd.DataFrame], config: dict[str, Any], checks: pd.DataFrame | None = None,
                 metrics: dict[str, Any] | None = None, detections: pd.DataFrame | None = None) -> list[Path]:
    generated = resolve_path(config["paths"]["generated_data"])
    exports = resolve_path(config["paths"]["exports"])
    report_dir = resolve_path(config["paths"]["reports"])
    chart_dir = resolve_path(config["paths"]["charts"])
    for directory in (generated, exports, report_dir, chart_dir):
        directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name in sorted(k for k in tables if k != "GroundTruth"):
        frame = tables[name].sort_values(frame_sort_column(tables[name]), kind="stable") if len(tables[name]) else tables[name]
        csv_path = generated / f"{name}.csv"
        frame.to_csv(csv_path, index=False, encoding="utf-8", lineterminator="\n")
        json_path = exports / f"{name}.json"
        json_path.write_text(frame.to_json(orient="records", force_ascii=False, indent=2, date_format="iso") + "\n", encoding="utf-8")
        written.extend([csv_path, json_path])
    gt = tables.get("GroundTruth", pd.DataFrame())
    write_ground_truth(gt, resolve_path(config["paths"]["ground_truth"]))
    if checks is not None:
        path = report_dir / "validation_results.csv"
        checks.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
        written.append(path)
    if detections is not None:
        path = report_dir / "detected_anomalies.csv"
        detections.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
        written.append(path)
    if metrics is not None:
        (report_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        pd.json_normalize(metrics, sep=".").to_csv(report_dir / "summary_report.csv", index=False, encoding="utf-8", lineterminator="\n")
        written.extend([report_dir / "metrics.json", report_dir / "summary_report.csv"])
        counts = metrics["entity_record_counts"]
        plt.figure(figsize=(9, 4))
        plt.bar(list(counts), list(counts.values()), color="#3977a8")
        plt.xticks(rotation=35, ha="right")
        plt.ylabel("Records")
        plt.title("Generated records by entity")
        plt.tight_layout()
        chart = chart_dir / "entity_record_counts.png"
        plt.savefig(chart, dpi=130)
        plt.close()
        plt.figure(figsize=(6, 4))
        anomaly = metrics["anomaly_detection"]
        labels = ["Precision", "Recall", "F1"]
        values = [anomaly[x] or 0 for x in ("precision", "recall", "f1")]
        plt.bar(labels, values, color=["#5c9e75", "#d7a343", "#8d70a8"])
        plt.ylim(0, 1)
        plt.title("Anomaly detection evaluation")
        plt.tight_layout()
        chart2 = chart_dir / "anomaly_metrics.png"
        plt.savefig(chart2, dpi=130)
        plt.close()
        written.extend([chart, chart2])
        dashboard = report_dir / "index.html"
        dashboard.write_text(_dashboard_html(metrics, checks, detections, generated, report_dir, chart_dir), encoding="utf-8")
        stylesheet = Path(__file__).with_name("report.css")
        (report_dir / "style.css").write_text(stylesheet.read_text(encoding="utf-8"), encoding="utf-8")
        written.extend([dashboard, report_dir / "style.css"])
    return written


def frame_sort_column(frame: pd.DataFrame) -> str:
    return frame.columns[0]


def _dashboard_html(metrics: dict[str, Any], checks: pd.DataFrame | None, detections: pd.DataFrame | None,
                    generated: Path, report_dir: Path, chart_dir: Path) -> str:
    metadata_path = generated / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    counts = metrics.get("entity_record_counts", {})
    metric_rows = [
        ("Onboarding completion", metrics.get("onboarding_completion_rate"), "percent"),
        ("Average onboarding time", metrics.get("average_onboarding_completion_days"), "days"),
        ("Overdue task rate", metrics.get("overdue_task_rate"), "percent"),
        ("Asset recovery completion", metrics.get("asset_recovery_completion_rate"), "percent"),
        ("Offboarding completion", metrics.get("offboarding_completion_rate"), "percent"),
        ("Audit coverage", metrics.get("audit_coverage_rate"), "percent"),
    ]
    def show_metric(value: Any, kind: str) -> str:
        if value is None:
            return "Not defined"
        return f"{value * 100:.1f}%" if kind == "percent" else f"{value:.1f} {kind}"
    count_rows = "".join(f"<tr><th>{html.escape(name)}</th><td>{value:,}</td></tr>" for name, value in counts.items())
    metric_html = "".join(f"<tr><th>{html.escape(name)}</th><td>{show_metric(value, kind)}</td></tr>" for name, value, kind in metric_rows)
    failed = int((~checks.passed).sum()) if checks is not None and not checks.empty else 0
    expected_checks = {"ACCESS_POLICY", "ASSET_DUPLICATE", "TASK_CYCLE", "ASSET_RECOVERY"}
    unexpected = int(((~checks.passed) & ~checks.check_id.isin(expected_checks)).sum()) if checks is not None and not checks.empty else 0
    detection_rows = ""
    if detections is not None and not detections.empty:
        detection_rows = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in (row.issue_type, row.entity_type, row.entity_id, row.reason)) + "</tr>"
            for row in detections.itertuples()
        )
    else:
        detection_rows = '<tr><td colspan="4">No anomalies detected.</td></tr>'
    quality = metrics.get("anomaly_detection", {})
    mode = html.escape(str(metadata.get("mode", "unknown")))
    seed = html.escape(str(metadata.get("seed", "unknown")))
    chart_base = "../charts"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Employee Lifecycle Automation — Run Summary</title><link rel="stylesheet" href="style.css"></head><body><main>
<header><h1>Employee Lifecycle Automation</h1><p class="sub">Synthetic onboarding and offboarding run summary</p>
<div class="meta"><span class="pill">Mode: {mode}</span><span class="pill">Seed: {seed}</span><span class="pill status">{failed} detected rule violations · {unexpected} unexpected</span></div></header>
<div class="grid"><section><h2>Dataset size</h2><table>{count_rows}</table></section>
<section><h2>Workflow metrics</h2><table>{metric_html}</table></section></div>
<section><h2>Anomaly evaluation</h2><div class="score"><div><strong>{show_metric(quality.get('precision'), 'percent')}</strong><span>Precision</span></div><div><strong>{show_metric(quality.get('recall'), 'percent')}</strong><span>Recall</span></div><div><strong>{show_metric(quality.get('f1'), 'percent')}</strong><span>F1 score</span></div><div><strong>{quality.get('true_positive', 0)}</strong><span>True positives</span></div></div>
<p class="note">The five labeled anomalies are deliberate examples. The validator detects them from operational records and rules; labels are used only for this evaluation.</p>
<h2>Detected anomalies</h2><table><thead><tr><th>Issue type</th><th>Entity</th><th>Record ID</th><th>Detection reason</th></tr></thead><tbody>{detection_rows}</tbody></table></section>
<div class="grid"><section><h2>Generated records</h2><img src="{chart_base}/entity_record_counts.png" alt="Bar chart of generated record counts"></section><section><h2>Anomaly scores</h2><img src="{chart_base}/anomaly_metrics.png" alt="Bar chart of anomaly precision, recall, and F1"></section></div>
<section class="links"><h2>Reports and data</h2><a href="validation_results.csv">Validation results CSV</a><a href="detected_anomalies.csv">Detected anomalies CSV</a><a href="metrics.json">Metrics JSON</a><a href="summary_report.csv">Summary CSV</a><a href="../../data/ground_truth/ground_truth.csv">Ground truth CSV</a><a href="../../data/generated/Employee.csv">Employee CSV</a><a href="../../data/generated/Task.csv">Task CSV</a><p class="note">All employee data is synthetic. Dates and timestamps use the project's fixed synthetic calendar.</p></section>
</main></body></html>'''
