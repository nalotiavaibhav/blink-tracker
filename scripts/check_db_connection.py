"""Simple connectivity check to the configured DATABASE_URL.
Creates tables if not present and prints a quick summary.
"""

import os

from backend.models import init_database, User


def main() -> None:
    db_url = os.getenv("DATABASE_URL", "sqlite:///waw_local.db")
    print(f"Connecting to: {db_url}")
    engine, SessionMaker = init_database(db_url)
    with SessionMaker() as session:
        # Ensure tables exist (init_database already creates them)
        # Show user count as a minimal query
        try:
            count = session.query(User).count()
        except Exception as e:
            print(f"Query failed: {e}")
            raise
        print(f"OK: users table accessible (rows={count})")


if __name__ == "__main__":
    main()
