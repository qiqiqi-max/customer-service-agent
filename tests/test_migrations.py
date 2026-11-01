import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[1]
ACTOR_COLUMNS = {"approved_by", "rejected_by", "executed_by"}


class TestMigrations(unittest.TestCase):
    def test_fresh_database_upgrades_downgrades_and_upgrades_again(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = str(Path(tmp_dir) / "migrations.sqlite3")
            # No ini file: env.py would otherwise run fileConfig and disable app loggers.
            alembic_config = AlembicConfig()
            alembic_config.set_main_option("script_location", str(ROOT / "alembic"))
            with patch("config.database_url", ""), patch("config.conversation_db_path", db_path):
                command.upgrade(alembic_config, "head")
                head_columns = self._refund_columns(db_path)
                command.downgrade(alembic_config, "-1")
                downgraded_columns = self._refund_columns(db_path)
                command.upgrade(alembic_config, "head")
                reupgraded_columns = self._refund_columns(db_path)

        self.assertTrue(ACTOR_COLUMNS <= head_columns)
        self.assertFalse(ACTOR_COLUMNS & downgraded_columns)
        self.assertTrue(ACTOR_COLUMNS <= reupgraded_columns)

    def _refund_columns(self, db_path: str) -> set[str]:
        engine = create_engine(f"sqlite:///{Path(db_path).as_posix()}")
        try:
            return {column["name"] for column in inspect(engine).get_columns("refund_requests")}
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
