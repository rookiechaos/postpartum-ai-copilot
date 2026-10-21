"""Read-only worker schema gate. Never initializes, alters or backfills data."""

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path


def worker_schema_ready(engine):
    from models.database import Base

    try:
        if engine.dialect.name == "sqlite" and engine.url.database not in (None, "", ":memory:"):
            if not Path(engine.url.database).is_file():
                return False  # Wait for the deployer; do not create an empty database.
        with engine.connect() as connection:
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            for table in Base.metadata.tables.values():
                if table.name not in tables:
                    return False
                present = {column["name"] for column in inspector.get_columns(table.name)}
                if not set(table.columns.keys()).issubset(present):
                    return False
            # These unique indexes are established at the end of the existing
            # serialized upgrade, after identity backfill and duplicate checks.
            for name, columns in (("tracking_entries", {"record_key"}),
                                  ("family_members", {"family_id", "user_id"})):
                if not any(index.get("unique") and set(index.get("column_names") or []) == columns
                           for index in inspector.get_indexes(name)):
                    return False
        return True
    except SQLAlchemyError:
        return False
