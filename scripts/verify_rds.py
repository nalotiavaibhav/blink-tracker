import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


def main():
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set.")
        return
    print(f"Connecting to: {url}")
    engine = create_engine(url)
    with engine.connect() as conn:
        # Verify connection
        version = conn.execute(text("select version()"))
        print("DB version:", version.scalar())

        # List tables in 'public' schema
        tables = conn.execute(
            text(
                """
                select table_name from information_schema.tables
                where table_schema='public' order by table_name
                """
            )
        ).fetchall()
        print("Tables:", [t[0] for t in tables])

        # Counts
        for t in ["users", "user_sessions", "tracking_sessions", "blink_samples", "email_otps"]:
            try:
                cnt = conn.execute(text(f"select count(*) from {t}")).scalar()
                print(f"{t}: {cnt}")
            except Exception as e:
                print(f"{t}: error -> {e}")

        # Show recent users
        try:
            rows = conn.execute(text("select id,email,created_at from users order by id desc limit 5")).fetchall()
            print("Recent users:", rows)
        except Exception as e:
            print("users query error:", e)


if __name__ == "__main__":
    main()
