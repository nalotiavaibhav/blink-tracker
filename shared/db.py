"""Shared DB helpers to keep app code simple."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

# Ensure project root on path when imported from subpackages
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.models import init_database, User, BlinkSample  # type: ignore
from datetime import datetime
from typing import Optional
from shared.config import CONFIG
from typing import Optional as _Optional

# Lazy, module-level cache for engine/sessionmaker
_SESSION_LOCAL: _Optional[object] = None

@contextmanager
def db_session():
    """Context manager yielding a SQLAlchemy session."""
    global _SESSION_LOCAL
    if _SESSION_LOCAL is None:
        _engine, _SESSION_LOCAL = init_database(CONFIG.database_url)
    with _SESSION_LOCAL() as session:  # type: ignore[operator]
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

def fetch_pending_samples(limit: int = 200) -> list[BlinkSample]:
    with db_session() as db:
        return (
            db.query(BlinkSample)
            .filter(BlinkSample.sync_status != 'synced')
            .order_by(BlinkSample.captured_at_utc.asc())
            .limit(limit)
            .all()
        )

def mark_samples_synced(ids: list[int]) -> None:
    if not ids:
        return
    with db_session() as db:
        (
            db.query(BlinkSample)
            .filter(BlinkSample.id.in_(ids))
            .update({BlinkSample.sync_status: 'synced'}, synchronize_session=False)
        )
        db.commit()
