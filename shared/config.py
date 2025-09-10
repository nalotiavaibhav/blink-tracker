"""Centralized configuration with sane defaults.
Values can be provided via (in order):
- Environment variables / .env (highest priority)
- app_config.json at repo root (packaged for production)
- Built-in safe defaults for local dev
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Ensure .env is loaded for desktop and scripts as well
load_dotenv()

def _load_file_config() -> dict:
    """Load optional app_config.json from project root.
    This lets packaged desktop builds pick up the API base URL without user input.
    """
    try:
        root = Path(__file__).resolve().parents[1]
        cfg_path = root / 'app_config.json'
        if cfg_path.exists():
            with open(cfg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}

_FILE_CFG = _load_file_config()

@dataclass(frozen=True)
class AppConfig:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///waw_local.db")
    device_id: str = os.getenv("DEVICE_ID", "desktop-001")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    # API base from env first, then app_config.json (apiBase/API_BASE_URL), then localhost fallback
    api_base_url: str = (
        os.getenv("API_BASE_URL")
        or _FILE_CFG.get("apiBase")
        or _FILE_CFG.get("API_BASE_URL")
        or "http://localhost:8000"
    )
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", _FILE_CFG.get("googleClientId", ""))
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", _FILE_CFG.get("googleClientSecret", ""))

CONFIG = AppConfig()
