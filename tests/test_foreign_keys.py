from src.database_manager import connect_database, create_database


def test_database_schema_and_foreign_keys(starter_tables, tmp_path):
    path = create_database(starter_tables, tmp_path / "test.db")
    db = connect_database(path)
    try:
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT COUNT(*) FROM Employee").fetchone()[0] == 30
    finally:
        db.close()
