"""Minimal API client for WaW backend (login + batch upload)."""
from __future__ import annotations

import requests
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LoginResult:
    access_token: str
    user: Dict


class ApiClient:
    """Lightweight synchronous API client used by the desktop app."""

    def __init__(self, base_url: str):
        self.base_url = self._sanitize_base_url(base_url)
        self._token = None  # bearer token string
        self._last_token_error = None  # last validation failure reason

    # ---- helpers ----
    @staticmethod
    def _sanitize_base_url(url: str) -> str:
        # Remove internal whitespace (user often types 'http://127.0.0.1 :8000')
        if not url:
            return ""
        url = url.strip().replace(" ", "")
        # Common user typos for localhost we auto-correct:
        #  - 127v0.0.1  (accidental 'v' instead of '.')
        #  - 127..0.1   (double dot)
        #  - missing scheme (add http://)
        lowered = url.lower()
        if lowered.startswith("127") or lowered.startswith("localhost"):
            # prepend scheme if absent
            if not lowered.startswith("http://") and not lowered.startswith("https://"):
                url = f"http://{url}"
        # After ensuring scheme, fix specific typos
        # Only alter host portion
        try:
            from urllib.parse import urlparse, urlunparse
            parts = urlparse(url)
            host = parts.hostname or ""
            fixed_host = host.replace("127v0.0.1", "127.0.0.1").replace("127..0.1", "127.0.0.1")
            if fixed_host != host:
                # Rebuild netloc (preserve port if any)
                netloc = fixed_host
                if parts.port:
                    netloc = f"{fixed_host}:{parts.port}"
                url = urlunparse((parts.scheme, netloc, parts.path, parts.params, parts.query, parts.fragment))
        except Exception:
            pass  # best-effort normalization
        return url.rstrip('/')

    @property
    def is_authed(self) -> bool:
        return bool(self._token)

    @property
    def last_token_error(self) -> Optional[str]:
        return self._last_token_error

    def set_token(self, token: str) -> None:
        self._token = token

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def login(self, email: str, password: str) -> LoginResult:
        """Password-based login (pairs with /v1/auth/login-password)."""
        resp = requests.post(
            f"{self.base_url}/v1/auth/login-password",
            json={"email": email, "password": password},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        self._token = token
        return LoginResult(access_token=token, user=data["user"])        

    def google_login(self, id_token: str) -> LoginResult:
        resp = requests.post(
            f"{self.base_url}/v1/auth/google",
            json={"id_token": id_token},
            timeout=10,
        )
        if resp.status_code >= 400:
            # Extract backend detail for clearer UI messaging
            detail = None
            try:
                j = resp.json()
                detail = j.get("detail") if isinstance(j, dict) else None
            except Exception:
                pass
            if detail:
                raise requests.HTTPError(f"{resp.status_code} Google auth failed: {detail}", response=resp)
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        self._token = token
        return LoginResult(access_token=token, user=data["user"]) 

    def send_otp(self, email: str) -> Dict:
        resp = requests.post(
            f"{self.base_url}/v1/auth/send-otp",
            json={"email": email},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def verify_otp(self, email: str, code: str) -> LoginResult:
        resp = requests.post(
            f"{self.base_url}/v1/auth/verify-otp",
            json={"email": email, "code": code},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        self._token = token
        return LoginResult(access_token=token, user=data["user"])

    def upload_blinks(self, samples: List[Dict]) -> Dict:
        resp = requests.post(
            f"{self.base_url}/v1/blinks",
            headers=self._headers(),
            json={"samples": samples},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def upload_sessions(self, sessions: List[Dict]) -> Dict:
        resp = requests.post(
            f"{self.base_url}/v1/sessions",
            headers=self._headers(),
            json={"sessions": sessions},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def get_me(self) -> Dict:
        resp = requests.get(
            f"{self.base_url}/v1/me",
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_sessions(self, limit: int = 50) -> List[Dict]:
        resp = requests.get(
            f"{self.base_url}/v1/sessions",
            headers=self._headers(),
            params={"limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def get_session_summary(self) -> Dict:
        resp = requests.get(
            f"{self.base_url}/v1/sessions/summary",
            headers=self._headers(),
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def delete_my_account(self) -> Dict:
        resp = requests.delete(
            f"{self.base_url}/v1/me",
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    # --- Added back after accidental removal ---
    def validate_token(self) -> bool:
        """Check that the current bearer token is still valid.

        Returns True when valid. On failure, sets last_token_error with a short reason.
        """
        if not self._token:
            self._last_token_error = "no_token"
            return False
        url = f"{self.base_url}/v1/me"
        try:
            self._last_token_error = None
            resp = requests.get(url, headers=self._headers(), timeout=8)
            if resp.status_code == 401:
                self._token = None
                detail = None
                try:
                    if resp.headers.get('content-type','').startswith('application/json'):
                        data = resp.json()
                        if isinstance(data, dict):
                            detail = data.get('detail')
                except Exception:
                    pass
                self._last_token_error = f"unauthorized: {detail}" if detail else "unauthorized"
                return False
            if resp.status_code >= 500:
                # Server side failure; keep token (likely transient) but record reason
                detail = None
                try:
                    if resp.headers.get('content-type','').startswith('application/json'):
                        data = resp.json()
                        if isinstance(data, dict):
                            detail = data.get('detail')
                except Exception:
                    pass
                self._last_token_error = f"server_error:{resp.status_code}" + (f" {detail}" if detail else "")
                return False
            resp.raise_for_status()
            return True
        except requests.Timeout:
            self._last_token_error = "timeout"
        except requests.ConnectionError as e:
            self._last_token_error = f"connection: {e}"[:120]
        except requests.RequestException as e:
            self._last_token_error = f"request: {e}"[:120]
        return False

    def set_password(self, new_password: str) -> Dict:
        """Set or update password for the currently authenticated user.

        Requires a valid bearer token (after Google or OTP signup)."""
        if not self._token:
            raise RuntimeError("Auth required before setting password")
        resp = requests.post(
            f"{self.base_url}/v1/auth/set-password",
            headers=self._headers(),
            json={"password": new_password},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    # Password reset (OTP-based, no auth required for request)
    def request_password_reset(self, email: str) -> Dict:
        resp = requests.post(
            f"{self.base_url}/v1/auth/request-password-reset",
            json={"email": email},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def confirm_password_reset(self, email: str, code: str, new_password: str) -> Dict:
        resp = requests.post(
            f"{self.base_url}/v1/auth/confirm-password-reset",
            json={"email": email, "code": code, "new_password": new_password},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
