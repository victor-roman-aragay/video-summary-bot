"""Tests for database factory"""

import os
import pytest
from video_summary_bot.database.factory import get_database
from video_summary_bot.database.operations import Database


class TestDatabaseFactory:
    """Tests for the database factory function"""

    def test_defaults_to_sqlite_when_no_env(self, monkeypatch, tmp_db_path):
        """When neither DATABASE_URL nor USE_SUPABASE is set, use SQLite"""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("USE_SUPABASE", raising=False)
        monkeypatch.setenv("SQLITE_DB_PATH", tmp_db_path)

        db = get_database()
        assert isinstance(db, Database)

    def test_defaults_to_sqlite_when_supabase_false(self, monkeypatch, tmp_db_path):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("USE_SUPABASE", "false")
        monkeypatch.setenv("SQLITE_DB_PATH", tmp_db_path)

        db = get_database()
        assert isinstance(db, Database)

    def test_raises_when_supabase_true_but_no_url(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("USE_SUPABASE", "true")

        with pytest.raises(ValueError, match="USE_SUPABASE=true but DATABASE_URL not set"):
            get_database()

    def test_raises_when_database_url_not_postgresql(self, monkeypatch):
        """A non-postgresql DATABASE_URL should still default to SQLite"""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///local.db")
        monkeypatch.delenv("USE_SUPABASE", raising=False)
        # Since it doesn't start with postgresql://, it should fall through to SQLite
        # We just verify it doesn't crash and returns a Database instance
        from video_summary_bot.database.factory import get_database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            monkeypatch.setenv("SQLITE_DB_PATH", f.name)
        db = get_database()
        assert isinstance(db, Database)
