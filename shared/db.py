"""Shared DB helpers to keep app code simple."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

# Ensure project root on path when imported from subpackages
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.models import SessionLocal, User, BlinkSample  # type: ignore
from datetime import datetime
from typing import Optional
from shared.config import CONFIG

@contextmanager
def db_session():
    """Context manager yielding a SQLAlchemy session."""
    with SessionLocal() as session:
        yield session

# Simple CRUD helpers

def get_or_create_default_user() -> User:
    with db_session() as db:
        user = db.query(User).first()
        if user:
            return user
        user = User(email="local@example.com", name="Local User", consent=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

def store_blink_sample(
    user_id: int,
    *,
    timestamp_iso: str,
    blink_count: int,
    device_id: str | None = None,
    app_version: str | None = None,
    cpu_percent: Optional[float] = None,
    memory_mb: Optional[float] = None,
    energy_impact: Optional[str] = None,
) -> BlinkSample:
    captured_at = datetime.fromisoformat(timestamp_iso.replace("Z", ""))
    with db_session() as db:
        sample = BlinkSample(
            user_id=user_id,
            client_sequence=int(datetime.utcnow().timestamp() * 1000),
            captured_at_utc=captured_at,
            blink_count=blink_count,
            device_id=device_id or CONFIG.device_id,
            app_version=app_version or CONFIG.app_version,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            energy_impact=energy_impact,
        )
        db.add(sample)
        db.commit()
        db.refresh(sample)
        return sample
