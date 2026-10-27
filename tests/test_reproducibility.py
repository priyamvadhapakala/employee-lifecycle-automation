from src.reproducibility import _digest_tables
from src.data_generator import generate_dataset
from src.anomaly_injector import inject_anomalies


def test_same_seed_produces_identical_hashes(config):
    first, _ = inject_anomalies(generate_dataset(config, "starter", 20261022), True)
    second, _ = inject_anomalies(generate_dataset(config, "starter", 20261022), True)
    assert _digest_tables(first) == _digest_tables(second)
