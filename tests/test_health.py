from unittest.mock import MagicMock
from app.core.database import get_db
from app.main import app


def test_home_page_returns_200(client):
    """Ověření, že úvodní stránka aplikace vrací stav 200 OK a obsahuje název Dřevěnka."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Dřevěnka s.r.o." in response.text


def test_health_check_healthy(client):
    """Ověření, že healthcheck endpoint vrací očekávanou JSON strukturu."""
    # Mock databázové session pro běh testu bez nutnosti spuštěného PostgreSQL serveru
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "drevenka-warehouse-api"
        assert data["database"] == "connected"
    finally:
        app.dependency_overrides.clear()


def test_favicon_served(client):
    """Ověření, že favicon webu je dostupná jak na /favicon.ico, tak jako SVG v /static/img/favicon.svg."""
    resp_ico = client.get("/favicon.ico")
    assert resp_ico.status_code == 200
    assert "image/x-icon" in resp_ico.headers.get("content-type", "")
    assert len(resp_ico.content) > 0

    resp_svg = client.get("/static/img/favicon.svg")
    assert resp_svg.status_code == 200
    assert "svg" in resp_svg.headers.get("content-type", "").lower()
    assert b"<svg" in resp_svg.content
    assert b"brandGrad" in resp_svg.content

