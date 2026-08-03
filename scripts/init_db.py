#!/usr/bin/env python
"""Initialize the application database.

Loads the database URL from ``.env`` / the environment and applies all
pending Alembic migrations (schema only). It is equivalent to running
``alembic upgrade head`` from the project root.

Usage:
    python scripts/init_db.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".flaskenv", override=True)
load_dotenv(PROJECT_ROOT / ".env")


def main() -> None:
    database_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("NEON_DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
    )
    if not database_url:
        print(
            "error: DATABASE_URL is not set. Add it to .env (or export it) and try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    alembic_ini = PROJECT_ROOT / "alembic.ini"
    if not alembic_ini.exists():
        print(f"error: {alembic_ini} not found.", file=sys.stderr)
        sys.exit(1)

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))

    print("Applying database migrations...")
    command.upgrade(config, "head")
    print("Database schema is up to date.")


if __name__ == "__main__":
    main()
