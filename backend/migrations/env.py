from alembic import context

from app import models
from app.db import Base, engine

if context.is_offline_mode():
    context.configure(url=engine.url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    def migrate(connection):
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()

    if connection := context.config.attributes.get("connection"):
        migrate(connection)
    else:
        with engine.connect() as connection:
            migrate(connection)
