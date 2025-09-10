"""Trigger /v1/auth/send-otp against the running app in-process.

Uses FastAPI TestClient so we don't need to spin up Uvicorn. The app
will connect to the database configured via DATABASE_URL (RDS) and
send email via SMTP_* env vars if present.

Recipient precedence:
- TEST_OTP_EMAIL env var, else
- SMTP_USER, else
- raises error.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    # Decide recipient email
    email = os.getenv("TEST_OTP_EMAIL") or os.getenv("SMTP_USER")
    if not email:
        raise SystemExit("Set TEST_OTP_EMAIL or SMTP_USER in .env to choose recipient.")

    # Ensure repository root is on sys.path so we can import 'backend'
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Import app after env is loaded so backend.main picks it up
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    resp = client.post("/v1/auth/send-otp", json={"email": email})
    print("Status:", resp.status_code)
    try:
        print("Response:", resp.json())
    except Exception:
        print("Raw response:", resp.text)


if __name__ == "__main__":
    main()
