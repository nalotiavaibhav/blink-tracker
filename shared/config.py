"""Centralized configuration with sane defaults.
Values can be overridden via environment variables or .env.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///waw_local.db")
    device_id: str = os.getenv("DEVICE_ID", "desktop-001")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000")

CONFIG = AppConfig()
