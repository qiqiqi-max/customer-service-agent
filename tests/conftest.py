import tempfile
from pathlib import Path

import pytest

import config
from database import dispose_engines


@pytest.fixture(scope="session", autouse=True)
def isolated_database():
    """Run the suite against a throwaway SQLite file instead of the developer database."""
    original_url = config.database_url
    original_path = config.conversation_db_path
    with tempfile.TemporaryDirectory() as tmp_dir:
        config.database_url = ""
        config.conversation_db_path = str(Path(tmp_dir) / "test.sqlite3")
        dispose_engines()
        try:
            yield
        finally:
            dispose_engines()
            config.database_url = original_url
            config.conversation_db_path = original_path
