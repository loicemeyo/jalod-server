"""Alembic migration environment.

Wires Alembic to the application's SQLAlchemy models so that ``alembic``
and ``scripts/init_db.py`` manage the real database schema.

The target database URL is resolved from the environment exactly like the
application does (``DATABASE_URL``, then ``NEON_DATABASE_URL``, then
``POSTGRES_URL``, falling back to SQLite), including Neon-style URL
normalization.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Project root is the parent of the directory containing this file.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

# Make the application modules importable regardless of the working directory.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Match the environment loading performed by src/app.py.
load_dotenv(PROJECT_ROOT / ".flaskenv", override=True)
load_dotenv(PROJECT_ROOT / ".env")

from db import db, _normalize_database_url  # noqa: E402

# Import every model so its tables are registered on the shared metadata.
from models.member import memberModel  # noqa: F401,E402
from models.contribution import ContributionModel  # noqa: F401,E402
from models.treasury import TreasuryModel  # noqa: F401,E402
from models.welfare import WelfareModel  # noqa: F401,E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = db.metadata


def resolve_database_url() -> str:
    database_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("NEON_DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
    )
    if not database_url:
        return "sqlite:///jalod.db"
    if database_url.startswith(("postgres://", "postgresql://")):
        database_url = _normalize_database_url(database_url)
    return database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a connection)."""
    url = config.get_main_option("sqlalchemy.url") or resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against the configured database."""
    # Build the engine from the ini section dict so that URLs containing '%'
    # (e.g. passwords) are not mangled by ConfigParser interpolation.
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = resolve_database_url()

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
