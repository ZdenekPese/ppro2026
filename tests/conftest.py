import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.infrastructure.db.seed import ensure_demo_users, seed_database
from app.main import app


def _login_client(test_client: TestClient, username: str, password: str) -> TestClient:
    resp = test_client.post(
        "/login",
        data={"username": username, "password": password, "next": "/"},
        follow_redirects=False,
    )
    assert resp.status_code == 303, f"Přihlášení testovacího klienta '{username}' selhalo: {resp.status_code}"
    return test_client


@pytest.fixture
def anon_client():
    """Nepřihlášený TestClient (bez session cookie)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client():
    """Výchozí TestClient přihlášený jako jednatel (role manager)."""
    with TestClient(app) as test_client:
        yield _login_client(test_client, "dolezal", settings.DEMO_MANAGER_PASSWORD)


@pytest.fixture
def warehouse_client():
    """TestClient přihlášený jako skladník (role warehouse)."""
    with TestClient(app) as test_client:
        yield _login_client(test_client, "skladnik", settings.DEMO_WAREHOUSE_PASSWORD)


@pytest.fixture(autouse=True, scope="session")
def maintain_clean_database():
    """Zajištění demo účtů před testy a návrat DB do čistého stavu po jejich skončení."""
    with SessionLocal() as db:
        ensure_demo_users(db)
    yield
    seed_database()
