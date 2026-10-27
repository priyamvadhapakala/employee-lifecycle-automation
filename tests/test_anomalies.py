from src.validation_engine import validate_dataset


def test_all_five_injected_anomalies_have_ground_truth(starter_tables):
    assert set(starter_tables["GroundTruth"].anomaly_id) == {"ANOM-001", "ANOM-002", "ANOM-003", "ANOM-004", "ANOM-005"}


def test_validator_independently_detects_all_injected_types(starter_tables):
    _, detections = validate_dataset(starter_tables, "starter", {"employees": 30, "tasks": 120, "access_grants": 45, "assets": 36})
    found = set(detections.issue_type)
    assert {"access_before_start_or_approval", "duplicate_asset_assignment", "terminated_employee_active_grant",
            "circular_task_dependency", "recovered_asset_marked_assigned"} <= found


def test_ground_truth_labels_are_positive_and_have_explanations(starter_tables):
    truth = starter_tables["GroundTruth"]
    assert truth.expected_label.astype(int).eq(1).all()
    assert truth.reason.str.len().gt(0).all()
    assert truth.expected_rule.str.len().gt(0).all()


def test_every_ground_truth_issue_matches_detected_type_and_record(starter_tables):
    _, detections = validate_dataset(starter_tables)
    expected = set(zip(starter_tables["GroundTruth"].issue_type, starter_tables["GroundTruth"].entity_id))
    observed = set(zip(detections.issue_type, detections.entity_id))
    assert expected <= observed
