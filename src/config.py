"""Load and validate project configuration from config/config.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Read configuration and validate settings needed by all pipeline stages."""
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    try:
        with config_path.open(encoding="utf-8") as stream:
            config = json.load(stream)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Configuration file not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in configuration file: {config_path}: {exc}") from exc

    if not isinstance(config.get("seed"), int) or isinstance(config.get("seed"), bool):
        raise ValueError("config.seed must be an integer")
    if config.get("mode") not in {"starter", "full"}:
        raise ValueError("config.mode must be 'starter' or 'full'")
    if not isinstance(config.get("anomaly_injection"), bool):
        raise ValueError("config.anomaly_injection must be true or false")
    for section in ("paths", "dataset_sizes"):
        if not isinstance(config.get(section), dict):
            raise ValueError(f"config.{section} must be an object")
    for mode in ("starter", "full"):
        sizes = config["dataset_sizes"].get(mode)
        if not isinstance(sizes, dict):
            raise ValueError(f"config.dataset_sizes.{mode} must be an object")
        for key in ("employees", "tasks", "access_grants", "assets"):
            if not isinstance(sizes.get(key), int) or sizes[key] < 0:
                raise ValueError(f"config.dataset_sizes.{mode}.{key} must be a non-negative integer")
    return config


def resolve_path(value: str | Path) -> Path:
    """Resolve a configured project-relative path without depending on cwd."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path

