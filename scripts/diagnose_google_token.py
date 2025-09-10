"""Manual diagnostic script for a Google ID token.

Usage (PowerShell):
  $env:GOOGLE_CLIENT_ID="your-client-id"  # must match backend
  python -m scripts.diagnose_google_token <ID_TOKEN>

It will verify the token locally using google.oauth2.id_token and print key fields.
"""
from __future__ import annotations

import os
import sys
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests


def main():
    if len(sys.argv) < 2:
        print("Provide an ID token as the first argument.")
        sys.exit(1)
    token = sys.argv[1].strip()
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        print("GOOGLE_CLIENT_ID not set in environment; set it before running.")
        sys.exit(2)
    try:
        info = google_id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
        safe = {k: info.get(k) for k in ["aud", "iss", "sub", "email", "email_verified", "exp", "iat"] if k in info}
        print("Token OK:")
        for k, v in safe.items():
            print(f"  {k}: {v}")
        if info.get("aud") != client_id:
            print(f"WARNING: audience mismatch (token aud={info.get('aud')}) expected={client_id}")
    except Exception as e:
        print(f"Token verification failed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()