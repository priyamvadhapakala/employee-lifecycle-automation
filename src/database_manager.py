"""SQLite creation and deterministic loading for generated entity tables."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .config import PROJECT_ROOT

LOAD_ORDER = ["Department", "Role", "Employee", "Manager", "OnboardingCase", "OffboardingCase",
              "Task", "Dependency", "AccessRole", "AccessGrant", "Asset", "AssetAssignment", "AuditEvent"]


def connect_database(path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with foreign-key checks enabled for that connection."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_database(tables: dict[str, pd.DataFrame], database_path: str | Path | None = None) -> Path:
    path = Path(database_path) if database_path else PROJECT_ROOT / "database" / "employee_lifecycle.db"
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    connection = connect_database(path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript((PROJECT_ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
        connection.execute("BEGIN")
        for name in LOAD_ORDER:
            frame = tables[name]
            if frame.empty:
                continue
            rows = frame.copy()
            if name == "Employee":
                rows["manager_id"] = None
            cols = list(rows.columns)
            col_sql = ",".join('"' + col + '"' for col in cols)
            placeholders = ",".join("?" for _ in cols)
            values = [tuple(None if pd.isna(value) else value.item() if hasattr(value, "item") else value for value in row)
                      for row in rows.itertuples(index=False, name=None)]
            connection.executemany(f'INSERT INTO "{name}" ({col_sql}) VALUES ({placeholders})', values)
            if name == "Manager":
                for _, manager in frame.iterrows():
                    connection.execute("UPDATE Employee SET manager_id = ? WHERE employee_id = ?",
                                       (manager.manager_id, manager.employee_id))
        connection.commit()
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.IntegrityError(f"Foreign key check failed: {violations[:5]}")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return path
