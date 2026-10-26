import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.db.seed import seed_database


@pytest.fixture
def client():
    """TestClient pro odesílání požadavků na FastAPI aplikaci."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True, scope="session")
def maintain_clean_database():
    """Zajištění, že po proběhnutí testů je databáze vždy vrácena do čistého stavu s 25 hračkami."""
    yield
    seed_database()
