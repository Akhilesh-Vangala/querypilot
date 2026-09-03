from __future__ import annotations

import sys
from pathlib import Path

# Allow `python seed.py` from backend/ without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db import SessionLocal, engine  # noqa: E402
from app.models import Base  # noqa: E402
from app.warehouse import seed_all  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        seed_all(session)
    finally:
        session.close()
    print("QueryPilot warehouse and demo users are ready.")


if __name__ == "__main__":
    main()
