import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """TestClient pro odesílání požadavků na FastAPI aplikaci."""
    with TestClient(app) as test_client:
        yield test_client
