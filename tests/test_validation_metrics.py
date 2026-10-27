from src.metrics import calculate_metrics
from src.validation_engine import validate_dataset


def test_validation_rows_have_requested_entity_fields(starter_tables):
    checks, _ = validate_dataset(starter_tables)
    assert {"check_id", "check_name", "passed", "failed", "severity", "entity_type", "entity_id",
            "explanation", "expected_result", "actual_result"} <= set(checks.columns)


def test_unexpected_duplicate_email_is_reported(starter_tables):
    tables = {name: frame.copy(deep=True) for name, frame in starter_tables.items()}
    tables["Employee"].loc[1, "email"] = tables["Employee"].loc[0, "email"]
    checks, _ = validate_dataset(tables)
    assert ((checks.check_id == "UNIQUE_CONSTRAINT") & ~checks.passed).any()


def test_metrics_include_entity_counts_and_audit_rate(starter_tables):
    checks, detections = validate_dataset(starter_tables)
    metrics = calculate_metrics(starter_tables, checks, detections, starter_tables["GroundTruth"])
    assert metrics["employee_count"] == len(starter_tables["Employee"])
    assert metrics["task_count"] == len(starter_tables["Task"])
    assert metrics["access_grant_count"] == len(starter_tables["AccessGrant"])
    assert metrics["asset_count"] == len(starter_tables["Asset"])
    assert metrics["anomaly_detection"]["true_positive"] >= 5
    assert 0 <= metrics["audit_coverage_rate"] <= 1
