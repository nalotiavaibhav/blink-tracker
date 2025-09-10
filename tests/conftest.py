import os
import pytest
from fastapi.testclient import TestClient

# Ensure test-specific settings (in-memory / temp DB)
# Use a separate SQLite DB file for isolation
TEST_DB_PATH = 'test_waw.db'

os.environ.setdefault('DATABASE_URL', f'sqlite:///{TEST_DB_PATH}')
os.environ.setdefault('ALLOW_AUTO_USER_CREATE', 'true')
os.environ.setdefault('ADMIN_EMAILS', 'admin1@example.com,admin2@example.com')
os.environ.setdefault('ADMIN_SHARED_PASSWORD', 'admin@waw')
os.environ.setdefault('LOGIN_RATE_LIMIT_MAX', '50')  # relax for tests

from backend.main import app  # noqa: E402 after env vars

@pytest.fixture(scope='session')
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def cleanup_db():
    # Before each test, ensure tables are empty by recreating DB file
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
    # Re-initialize by importing models again (FastAPI startup already set engine)
    from backend.models import init_database
    init_database(f'sqlite:///{TEST_DB_PATH}')
    yield
