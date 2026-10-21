import uuid
from decimal import Decimal
import pytest


def test_create_product_success(client):
    """Ověření úspěšného vytvoření nového produktu přes REST API."""
    unique_code = f"AUT-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "code": unique_code,
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
    assert data["code"] == unique_code
    assert data["name"] == "Dřevěné autíčko sportovní"
    assert float(data["selling_price"]) == 210.00


def test_create_product_duplicate_code_fails(client):
    """Ověření, že duplicitní kód produktu (SKU) vrátí 409 Conflict."""
    unique_code = f"DUP-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "code": unique_code,
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
        "code": f"NEG-{uuid.uuid4().hex[:6].upper()}",
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


def test_create_product_price_overflow_fails(client):
    """Ověření, že cena nad limit 99 999 999.99 vrátí 422 místo Internal Server Error (500)."""
    payload = {
        "code": f"OVR-{uuid.uuid4().hex[:6].upper()}",
        "name": "Přetečená cena",
        "purchase_price": "100000000.00",
        "selling_price": "200000000.00",
        "min_stock_level": 5,
    }
    response = client.post("/api/products", json=payload)
    assert response.status_code == 422
    assert response.status_code != 500


def test_web_form_price_overflow_displays_field_error(client):
    """Ověření, že webový formulář zobrazí chybovou hlášku u pole místo 500 Internal Server Error."""
    form_data = {
        "code": f"WBO-{uuid.uuid4().hex[:6].upper()}",
        "name": "Webová přetečená cena",
        "description": "Test overflow",
        "purchase_price": "100000000.00",
        "selling_price": "200.00",
        "min_stock_level": "5",
    }
    response = client.post("/products/new", data=form_data)
    assert response.status_code == 422
    assert response.status_code != 500
    assert "input-error" in response.text
    assert "field-error" in response.text


def test_web_form_edit_price_overflow_displays_field_error(client):
    """Ověření, že editace produktu s cenou nad limit zobrazí chybu u inputu a nepadá na 500."""
    # Nejprve založíme platný produkt
    unique_code = f"EDO-{uuid.uuid4().hex[:6].upper()}"
    create_payload = {
        "code": unique_code,
        "name": "Produkt k editaci",
        "purchase_price": "150.00",
        "selling_price": "300.00",
        "min_stock_level": 5,
    }
    create_res = client.post("/api/products", json=create_payload)
    assert create_res.status_code == 201
    product_id = create_res.json()["id"]

    # Pokusíme se upravit cenu na 100 milionů
    edit_data = {
        "name": "Produkt s obří cenou",
        "description": "Popis",
        "purchase_price": "150.00",
        "selling_price": "100000000.00",
        "min_stock_level": "5",
        "is_active": "true",
    }
    edit_res = client.post(f"/products/{product_id}/edit", data=edit_data)
    assert edit_res.status_code == 422
    assert edit_res.status_code != 500
    assert "input-error" in edit_res.text
    assert "field-error" in edit_res.text
    assert "99 999 999,99" in edit_res.text

