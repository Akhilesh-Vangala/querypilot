"""Operator account provisioning; password is read from the local terminal."""

import argparse
from getpass import getpass
from sqlalchemy import select
from .db import SessionLocal
from .models import User
from .auth import hash_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=["analyst", "admin"], default="analyst")
    args = parser.parse_args()
    email = args.email.strip().lower()
    if "@" not in email or len(email) > 254 or not 1 <= len(args.name) <= 100:
        raise SystemExit("Invalid account details")
    password = getpass("New password (at least 16 characters): ")
    if not 16 <= len(password.encode()) <= 72:
        raise SystemExit("Password must be 16–72 bytes")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords differ")
    with SessionLocal.begin() as session:
        if session.scalar(select(User).where(User.email == email)):
            raise SystemExit("Account already exists; no changes made")
        session.add(
            User(
                email=email,
                full_name=args.name,
                role=args.role,
                hashed_password=hash_password(password),
            )
        )
    print("Account created.")


if __name__ == "__main__":
    main()
