"""One-shot schema/warehouse/role bootstrap. Never run at API startup."""

import argparse
import os
import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from .models import Base
from .warehouse import seed_warehouse, seed_users, warehouse_is_empty
from .agent.catalog import WAREHOUSE_TABLES
from .migrations import migrate


def bootstrap():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo-users",
        action="store_true",
        help="Development only: known synthetic accounts",
    )
    args = parser.parse_args()
    from .config import get_settings

    settings = get_settings()
    if args.demo_users and settings.app_environment == "production":
        raise SystemExit("Production cannot create demo accounts")
    owner = os.environ["MIGRATION_DATABASE_URL"]
    engine = create_engine(owner)
    migrate(engine)
    with Session(engine) as session:
        if warehouse_is_empty(session):
            seed_warehouse(session)
        if args.demo_users:
            seed_users(session)
    # Passwords are structured SQL values and are never logged or passed in argv.
    raw = owner.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(raw, autocommit=True) as connection:
        with connection.cursor() as cursor:
            for role, key in [
                ("querypilot_app", "APP_DATABASE_PASSWORD"),
                ("querypilot_reader", "WAREHOUSE_DATABASE_PASSWORD"),
            ]:
                password = os.environ[key]
                if len(password) < 16:
                    raise SystemExit(
                        "Database role passwords must be at least 16 characters"
                    )
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,))
                if not cursor.fetchone():
                    cursor.execute(
                        sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(role))
                    )
                cursor.execute(
                    sql.SQL(
                        "ALTER ROLE {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS PASSWORD {}"
                    ).format(sql.Identifier(role), sql.Literal(password))
                )
            cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            cursor.execute(
                "GRANT USAGE ON SCHEMA public TO querypilot_app, querypilot_reader"
            )
            for table in WAREHOUSE_TABLES:
                cursor.execute(
                    sql.SQL("GRANT SELECT ON {} TO querypilot_reader").format(
                        sql.Identifier(table)
                    )
                )
            for table in ("users", "ask_logs", "analysis_runs", "rate_windows"):
                cursor.execute(
                    sql.SQL(
                        "GRANT SELECT,INSERT,UPDATE,DELETE ON {} TO querypilot_app"
                    ).format(sql.Identifier(table))
                )
            cursor.execute(
                "GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO querypilot_app"
            )
    engine.dispose()
    print(
        "Bootstrap complete: versioned schema, synthetic warehouse, split unprivileged roles."
    )


if __name__ == "__main__":
    bootstrap()
