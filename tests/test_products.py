from decimal import Decimal
import pytest
from app.domain.exceptions import DuplicateProductCodeError, InvalidPriceError
from app.domain.models.product import ProductCreate, ProductUpdate
from app.domain.services.product_service import ProductService
from app.infrastructure.db.models import Product


def test_create_product_success(client):
    """Ověření úspěšného vytvoření nového produktu přes REST API."""
    payload = {
        "code": "TEST-AUT-001",
        "name": "Dřevěné autíčko sportovní",
        "description": "Bukové autíčko s otáčivými koly",
        "purchase_price": "85.00",
        "selling_price": "210.00",
        "min_stock_level": 6,
        "is_active": True,
    }
    response = client.post("/api/products", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "TEST-AUT-001"
    assert data["name"] == "Dřevěné autíčko sportovní"
    assert float(data["selling_price"]) == 210.00


def test_create_product_duplicate_code_fails(client):
    """Ověření, že duplicitní kód produktu (SKU) vrátí 409 Conflict."""
    payload = {
        "code": "TEST-DUP-001",
        "name": "Testovací hračka 1",
        "purchase_price": "50.00",
        "selling_price": "100.00",
        "min_stock_level": 5,
    }
    # První pokus - úspěch
    res1 = client.post("/api/products", json=payload)
    assert res1.status_code == 201

    # Druhý pokus se stejným kódem - konflikt
    res2 = client.post("/api/products", json=payload)
    assert res2.status_code == 409
    assert "již v systému existuje" in res2.json()["detail"]


def test_create_product_negative_price_fails(client):
    """Ověření, že záporná nákupní nebo prodejní cena je odmítnuta."""
    payload = {
        "code": "TEST-NEG-001",
        "name": "Záporná cena",
        "purchase_price": "-10.00",
        "selling_price": "100.00",
        "min_stock_level": 5,
    }
    response = client.post("/api/products", json=payload)
    assert response.status_code == 422


def test_search_products(client):
    """Ověření vyhledávání v katalogu produktů."""
    response = client.get("/api/products?search=káča")
    assert response.status_code == 200
    products = response.json()
    assert len(products) >= 1
    assert any("káča" in p["name"].lower() for p in products)
