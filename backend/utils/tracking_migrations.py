"""Add tracking identities and membership versions on API initialization."""

from uuid import uuid4

from sqlalchemy import inspect, text


def migrate_tracking_identity(engine):
    # Serialize inspection, DDL and backfill across API processes. Do not read care data.
    with engine.begin() as connection:
        if engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        elif engine.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(728154291)"))

        columns = {column["name"] for column in inspect(connection).get_columns("tracking_entries")}
        if "record_key" not in columns:
            connection.execute(text("ALTER TABLE tracking_entries ADD COLUMN record_key VARCHAR(36)"))
        if "revision" not in columns:
            connection.execute(text("ALTER TABLE tracking_entries ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"))

        missing = connection.execute(text("SELECT id FROM tracking_entries WHERE record_key IS NULL")).scalars().all()
        for entry_id in missing:
            connection.execute(
                text("UPDATE tracking_entries SET record_key = :key WHERE id = :id AND record_key IS NULL"),
                {"key": str(uuid4()), "id": entry_id},
            )
        connection.execute(text("UPDATE tracking_entries SET revision = 1 WHERE revision IS NULL"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_tracking_record_key ON tracking_entries (record_key)"))
        member_columns = {column["name"] for column in inspect(connection).get_columns("family_members")}
        if "revision" not in member_columns:
            connection.execute(text("ALTER TABLE family_members ADD COLUMN revision INTEGER NOT NULL DEFAULT 1"))
        connection.execute(text("UPDATE family_members SET revision = 1 WHERE revision IS NULL"))
        # Do not silently resolve legacy duplicates or combine their sharing permissions.
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_family_member_family_user ON family_members (family_id, user_id)"))
