from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg import sql

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402


def prepare_month(connection: psycopg.Connection, year: int, month: int) -> None:
    start = datetime(year, month, 1, tzinfo=ZoneInfo("Asia/Jakarta"))
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    name = f"inventory_activity_log_{year:04d}_{month:02d}"
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL(
                "CREATE TABLE IF NOT EXISTS {} PARTITION OF inventory_activity_log FOR VALUES FROM ({}) TO ({})"
            ).format(
                sql.Identifier(name),
                sql.Literal(start.date()),
                sql.Literal(end.date()),
            )
        )


def migrate(database_url: str) -> None:
    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    migrations = [path.read_text(encoding="utf-8") for path in sorted(migration_dir.glob("*.sql"))]
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    with psycopg.connect(database_url) as connection:
        for migration_sql in migrations:
            connection.execute(migration_sql)
        prepare_month(connection, now.year, now.month)
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        prepare_month(connection, next_month.year, next_month.month)


if __name__ == "__main__":
    configured = Settings().inventory_database_url
    if not configured:
        raise SystemExit("INVENTORY_DATABASE_URL is required")
    migrate(configured.get_secret_value())
