"""Verify the analytical role cannot read app identities or write warehouse tables."""

from sqlalchemy import text
from .agent.catalog import WAREHOUSE_TABLES


def verify_warehouse_role(engine):
    with engine.connect() as connection:
        superuser, bypass = connection.execute(
            text(
                "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )
        ).one()
        if superuser or bypass:
            raise RuntimeError("Warehouse role must be unprivileged")
        for table in ("users", "ask_logs", "analysis_runs", "rate_windows"):
            can_read = connection.execute(
                text("SELECT has_table_privilege(current_user,:relation,'SELECT')"),
                {"relation": "public." + table},
            ).scalar_one()
            if can_read:
                raise RuntimeError("Warehouse role can read application records")
        for table in WAREHOUSE_TABLES:
            writable = connection.execute(
                text(
                    "SELECT has_table_privilege(current_user,:relation,'INSERT,UPDATE,DELETE,TRUNCATE')"
                ),
                {"relation": "public." + table},
            ).scalar_one()
            readable = connection.execute(
                text("SELECT has_table_privilege(current_user,:relation,'SELECT')"),
                {"relation": "public." + table},
            ).scalar_one()
            if writable or not readable:
                raise RuntimeError(
                    "Warehouse role needs SELECT-only access to reviewed relations"
                )
