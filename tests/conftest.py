import pytest

from src.anomaly_injector import inject_anomalies
from src.config import load_config
from src.data_generator import generate_dataset


@pytest.fixture(scope="session")
def config():
    return load_config()


@pytest.fixture(scope="session")
def starter_tables(config):
    tables, gt = inject_anomalies(generate_dataset(config, "starter", 20261022), True)
    tables["GroundTruth"] = gt
    return tables
