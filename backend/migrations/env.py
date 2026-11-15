"""Alembic environment. The database URL comes from app settings (DATABASE_URL), or from -x url=..."""

from alembic import context
from sqlalchemy import create_engine

from app.config import load_settings
from app.db import Base

url = context.get_x_argument(as_dictionary=True).get("url") or context.config.get_main_option("sqlalchemy.url")
url = url or load_settings().database_url

engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
