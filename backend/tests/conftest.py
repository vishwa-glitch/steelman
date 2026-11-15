"""Shared fixtures. API tests use a real Postgres test database (steelman_test in the local Docker Postgres)
and fake model clients, so they cost no AI calls. They are skipped if the database isn't running."""

import dataclasses

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app import api
from app.config import load_settings
from app.db import make_session_factory

TEST_DB = "postgresql+psycopg://steelman:steelman-local-only@localhost:5433/steelman_test"


@pytest.fixture(scope="session")
def migrated_db():
    try:
        with create_engine(TEST_DB).connect() as c:
            c.execute(text("select 1"))
    except OperationalError:
        pytest.skip("Postgres test database not running (docker compose up -d)")
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", TEST_DB)
    command.upgrade(cfg, "head")
    return TEST_DB


@pytest.fixture
def make_client(migrated_db):
    """make_client(llm, **setting_overrides) -> TestClient on a clean database."""
    factory = make_session_factory(migrated_db)

    def build(llm, **overrides):
        with factory() as s:
            s.execute(text("TRUNCATE debates, usage"))
            s.commit()
        base = dataclasses.replace(
            load_settings(),
            database_url=migrated_db,
            openrouter_api_key="test",
            daily_ai_call_limit=100,
            debates_per_ip_per_day=100,
        )
        settings = dataclasses.replace(base, **overrides)

        from app.main import app

        app.dependency_overrides[api.get_settings] = lambda: settings
        app.dependency_overrides[api.get_llm] = lambda: llm
        return TestClient(app)

    yield build
    from app.main import app

    app.dependency_overrides.clear()
