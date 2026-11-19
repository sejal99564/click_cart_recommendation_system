import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shopwise.db")
if os.getenv("APP_ENV") == "production" and "DATABASE_URL" not in os.environ:
    raise RuntimeError("Set DATABASE_URL in production")

def database_engine(url: str):
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
    return engine


engine = database_engine(DATABASE_URL)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
