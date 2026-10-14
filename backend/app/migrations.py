"""One-shot additive schema initialization; API production startup never mutates schema."""

from sqlalchemy import text
from . import db
from .models import Base


def migrate(engine):
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS querypilot_schema_versions (version INTEGER PRIMARY KEY)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO querypilot_schema_versions(version) VALUES (1) ON CONFLICT DO NOTHING"
            )
        )


def main():
    migrate(db.engine)


if __name__ == "__main__":
    main()
