import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import inspect, text
from sqlalchemy.pool import NullPool
from flask_sqlalchemy import SQLAlchemy

try:
    from .logging_config import get_logger
except ImportError:  # pragma: no cover - allows running from src directory
    from logging_config import get_logger

logger = get_logger("jalod_api.db")


# Central SQLAlchemy instance used across the application.
db = SQLAlchemy()


def _normalize_database_url(database_url: str) -> str:
    """Convert common Neon/Postgres URLs into a SQLAlchemy-compatible URI."""

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    parsed_url = urlparse(database_url)
    query_params = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
    query_params.setdefault("sslmode", "require")
    query_params.pop("channelbinding", None)
    query_params.pop("channel_binding", None)

    return urlunparse(parsed_url._replace(query=urlencode(query_params)))


def configure_database(app):
    """Configure database connection for Flask app."""

    database_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("NEON_DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
    )

    if not database_url:
        database_url = "sqlite:///jalod.db"
        logger.warning("DATABASE_URL not set, falling back to SQLite")
    elif database_url.startswith(("postgres://", "postgresql://")):
        database_url = _normalize_database_url(database_url)

    # Mask credentials in logs.
    parsed = urlparse(database_url)
    safe_host = parsed.hostname or "unknown"
    logger.info("Configuring database: backend=%s host=%s", parsed.scheme, safe_host)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if database_url.startswith("sqlite:"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "poolclass": NullPool,
        }
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 10,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }

    db.init_app(app)

    return db


def ensure_member_auth_columns(app):
    """Add auth columns to an existing Members table when the database was created before auth support."""

    with app.app_context():
        inspector = inspect(db.engine)

        if "Members" not in inspector.get_table_names():
            return

        existing_columns = {column["name"] for column in inspector.get_columns("Members")}
        columns_added = []

        with db.engine.begin() as connection:
            if "password_hash" not in existing_columns:
                connection.execute(text('ALTER TABLE "Members" ADD COLUMN password_hash VARCHAR(255)'))
                columns_added.append("password_hash")

            if "contributions_tier" not in existing_columns:
                connection.execute(text('ALTER TABLE "Members" ADD COLUMN contributions_tier NUMERIC(10, 2)'))
                columns_added.append("contributions_tier")

            if "contributions_debt" not in existing_columns:
                connection.execute(text('ALTER TABLE "Members" ADD COLUMN contributions_debt NUMERIC(10, 2)'))
                columns_added.append("contributions_debt")

            if "loans_debt" not in existing_columns:
                connection.execute(text('ALTER TABLE "Members" ADD COLUMN loans_debt NUMERIC(10, 2)'))
                columns_added.append("loans_debt")

            if "contributions_dated_at" not in existing_columns:
                connection.execute(text('ALTER TABLE "Members" ADD COLUMN contributions_dated_at TIMESTAMP'))
                columns_added.append("contributions_dated_at")

            if "role" not in existing_columns:
                connection.execute(text('ALTER TABLE "Members" ADD COLUMN role VARCHAR(10) NOT NULL DEFAULT \'user\''))
                columns_added.append("role")

            if db.engine.dialect.name == "postgresql" and "password_hash" not in existing_columns:
                connection.execute(text('UPDATE "Members" SET password_hash = \'\' WHERE password_hash IS NULL'))
                connection.execute(text('ALTER TABLE "Members" ALTER COLUMN password_hash SET DEFAULT \'\''))
                connection.execute(text('ALTER TABLE "Members" ALTER COLUMN password_hash SET NOT NULL'))

            if db.engine.dialect.name == "postgresql":
                connection.execute(text('ALTER TABLE "Members" ALTER COLUMN age_group DROP NOT NULL'))

        if columns_added:
            logger.info("Schema migration: added columns to Members table: %s", ", ".join(columns_added))
        else:
            logger.debug("Schema migration: Members table already up to date")