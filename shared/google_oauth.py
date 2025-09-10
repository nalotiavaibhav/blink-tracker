"""Google OAuth helper for desktop to obtain an ID token via Installed App flow."""
from __future__ import annotations

from typing import Optional

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except Exception:
    InstalledAppFlow = None  # type: ignore


def get_google_id_token_interactive(client_id: str, client_secret: str) -> Optional[str]:
    """Run the Google Installed App OAuth flow and return an ID token.

    Uses the full userinfo.* scopes to avoid scope-mismatch errors sometimes raised
    when Google internally expands shorthand scopes ("email profile") to their
    canonical forms (https://www.googleapis.com/auth/userinfo.email, etc.).
    Returns None if the flow cannot be executed (dependency missing).
    """
    if InstalledAppFlow is None:
        return None

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"],  # Desktop app type uses localhost loopback
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    # Canonical scopes (avoid shorthand to prevent scope-change warning)
    scopes_primary = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    def run_flow(scopes_list):
        flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes_list)
        # prompt='consent' ensures id_token is issued; access_type offline for refresh tokens if needed
        return flow.run_local_server(port=0, prompt="consent", access_type="offline")

    try:
        creds = run_flow(scopes_primary)
    except Exception as e:
        msg = str(e).lower()
        # Retry once with legacy shorthand scopes if Google rejects canonical for some reason
        if "scope has changed" in msg or "invalid scope" in msg:
            try:
                legacy_scopes = ["openid", "email", "profile"]
                creds = run_flow(legacy_scopes)
            except Exception:
                raise
        else:
            raise

    return getattr(creds, "id_token", None)
