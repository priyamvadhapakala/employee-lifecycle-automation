from src.data_generator import generate_dataset


def test_starter_expected_sizes(config):
    data = generate_dataset(config, "starter", 20261022)
    sizes = config["dataset_sizes"]["starter"]
    assert len(data["Employee"]) == sizes["employees"]
    assert len(data["Task"]) == sizes["tasks"]
    assert len(data["AccessGrant"]) == sizes["access_grants"]
    assert len(data["Asset"]) == sizes["assets"]


def test_full_required_sizes(config):
    data = generate_dataset(config, "full", 20261022)
    assert len(data["Employee"]) == 1000
    assert len(data["Task"]) == 8000
    assert len(data["AccessGrant"]) == 1500
    assert len(data["Asset"]) == 1200


def test_ids_unique_and_states_allowed(starter_tables):
    assert starter_tables["Employee"].employee_id.is_unique
    assert starter_tables["Task"].task_id.is_unique
    assert set(starter_tables["Employee"].employment_status) <= {"pending", "active", "completed", "terminated"}
