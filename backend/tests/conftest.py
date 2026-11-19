from pathlib import Path

import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db import database_engine, get_db
from app.main import app


@pytest.fixture(autouse=True)
def migrated_database(tmp_path):
    root = Path(__file__).resolve().parents[1]
    ini = Config(root / "alembic.ini")
    postgres_url = os.getenv("SHOPWISE_TEST_DATABASE_URL")
    bootstrap = None
    if postgres_url:
        schema = "test_" + uuid.uuid4().hex
        bootstrap = database_engine(postgres_url)
        with bootstrap.begin() as connection:
            connection.execute(text(f"CREATE SCHEMA {schema}"))
        url = make_url(postgres_url).update_query_dict({"options": "-csearch_path=" + schema})
        engine = database_engine(url)
    else:
        engine = database_engine(f"sqlite:///{tmp_path / 'test.sqlite3'}")
    with engine.begin() as connection:
        ini.attributes["connection"] = connection
        command.upgrade(ini, "head")

    def test_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    try:
        yield engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        if bootstrap is not None:
            with bootstrap.begin() as connection:
                connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
            bootstrap.dispose()

@pytest.fixture(autouse=True)
def rate_limit_state(monkeypatch):
    from app import auth
    monkeypatch.setattr(auth, "_attempts", {})
