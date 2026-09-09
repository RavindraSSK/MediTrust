"""
Lightweight, idempotent schema migrations that run on startup.

``Base.metadata.create_all`` creates missing tables; the statements below add
columns introduced after the first release to existing SQLite and PostgreSQL
databases. Every statement is safe to re-run.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# (table, column, sqlite type, postgres type)
ADDED_COLUMNS = [
    ("users", "first_name", "VARCHAR", "VARCHAR"),
    ("users", "last_name", "VARCHAR", "VARCHAR"),
    ("users", "role_status", "VARCHAR DEFAULT 'approved' NOT NULL", "VARCHAR DEFAULT 'approved'"),
    ("users", "created_at", "DATETIME", "TIMESTAMPTZ DEFAULT now()"),
    ("users", "last_login_at", "DATETIME", "TIMESTAMPTZ"),
    ("assessments", "first_name", "VARCHAR", "VARCHAR"),
    ("assessments", "last_name", "VARCHAR", "VARCHAR"),
    ("prediction_logs", "full_name", "VARCHAR", "VARCHAR"),
    ("prediction_logs", "first_name", "VARCHAR", "VARCHAR"),
    ("prediction_logs", "last_name", "VARCHAR", "VARCHAR"),
    ("prediction_logs", "model_version", "VARCHAR", "VARCHAR"),
    ("prediction_logs", "created_by_user_id", "INTEGER", "INTEGER"),
    ("prediction_logs", "explanation_summary", "TEXT", "TEXT"),
    ("prediction_logs", "clinical_context", "TEXT", "TEXT"),
    ("case_escalations", "doctor_id", "INTEGER", "INTEGER"),
    ("case_escalations", "doctor_decision", "VARCHAR", "VARCHAR"),
    ("case_escalations", "doctor_note", "VARCHAR", "VARCHAR"),
    ("case_escalations", "reviewed_at", "DATETIME", "TIMESTAMPTZ"),
]

NAME_BACKFILL_TABLES = ["users", "assessments", "prediction_logs"]


def _sqlite_columns(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).mappings().all()
    return {row["name"] for row in rows}


def run_migrations(engine: Engine) -> None:
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "sqlite":
            for table, column, sqlite_type, _ in ADDED_COLUMNS:
                if column in _sqlite_columns(conn, table):
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sqlite_type}"))
                logger.info("Added column %s.%s", table, column)

            conn.execute(
                text("UPDATE users SET role_status = 'approved' WHERE role_status IS NULL OR trim(role_status) = ''")
            )
            for table in NAME_BACKFILL_TABLES:
                columns = _sqlite_columns(conn, table)
                if not {"full_name", "first_name", "last_name"} <= columns:
                    continue
                conn.execute(
                    text(
                        f"""
                        UPDATE {table}
                        SET
                            first_name = CASE
                                WHEN instr(trim(full_name), ' ') > 0 THEN substr(trim(full_name), 1, instr(trim(full_name), ' ') - 1)
                                ELSE trim(full_name)
                            END,
                            last_name = CASE
                                WHEN instr(trim(full_name), ' ') > 0 THEN substr(trim(full_name), instr(trim(full_name), ' ') + 1)
                                ELSE ''
                            END
                        WHERE full_name IS NOT NULL AND (first_name IS NULL OR trim(first_name) = '')
                        """
                    )
                )
                conn.execute(
                    text(f"UPDATE {table} SET last_name = '' WHERE last_name IS NULL AND full_name IS NOT NULL")
                )
            return

        if dialect == "postgresql":
            for table, column, _, pg_type in ADDED_COLUMNS:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {pg_type}"))

            conn.execute(
                text("UPDATE users SET role_status = 'approved' WHERE role_status IS NULL OR btrim(role_status) = ''")
            )
            for table in NAME_BACKFILL_TABLES:
                conn.execute(
                    text(
                        f"""
                        UPDATE {table}
                        SET
                            first_name = CASE
                                WHEN strpos(btrim(coalesce(full_name, '')), ' ') > 0 THEN split_part(btrim(full_name), ' ', 1)
                                ELSE btrim(coalesce(full_name, ''))
                            END,
                            last_name = CASE
                                WHEN strpos(btrim(coalesce(full_name, '')), ' ') > 0
                                    THEN btrim(substr(btrim(full_name), strpos(btrim(full_name), ' ') + 1))
                                ELSE ''
                            END
                        WHERE full_name IS NOT NULL AND (first_name IS NULL OR btrim(first_name) = '' OR last_name IS NULL)
                        """
                    )
                )
            return

        logger.warning("No migration routine for dialect %s; relying on create_all only", dialect)
