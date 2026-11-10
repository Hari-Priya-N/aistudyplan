"""
Tiny, dependency-free schema upgrader.

`Base.metadata.create_all()` creates missing *tables* but never adds new
*columns* to tables that already exist. So that a database created by an
earlier version of this project (e.g. a teammate's local tutor.db or an
existing Postgres) keeps working after pulling this update, this adds any
missing columns on startup. For a larger project you would switch to Alembic.
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import Base


def upgrade_schema(engine: Engine) -> list[str]:
    applied: list[str] = []
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            # The role column may be a native Postgres ENUM created before "management" existed.
            conn.execute(text(
                "DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'roleenum') THEN "
                "ALTER TYPE roleenum ADD VALUE IF NOT EXISTS 'management'; END IF; END $$;"
            ))
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            present = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                default = ""
                if column.name == "must_change_password":
                    default = " DEFAULT FALSE" if engine.dialect.name == "postgresql" else " DEFAULT 0"
                elif column.name == "kind":
                    default = " DEFAULT 'practice'"
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}{default}'))
                applied.append(f"{table.name}.{column.name}")
    return applied
