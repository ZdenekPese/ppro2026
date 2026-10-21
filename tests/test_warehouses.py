import uuid
import pytest


def test_list_warehouses(client):
    """Ověření, že API vrátí seznam skladů včetně Hradce Králové a Garáže Třebechovice."""
    response = client.get("/api/warehouses")
    assert response.status_code == 200
    warehouses = response.json()
    assert len(warehouses) >= 2
    codes = [w["code"] for w in warehouses]
    assert "WH-HK" in codes
    assert "WH-TREB" in codes


def test_create_warehouse_duplicate_code_fails(client):
    """Ověření, že duplicitní kód skladu vrátí 409 Conflict."""
    unique_code = f"W-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "code": unique_code,
        "name": "Nový zkušební sklad",
        "location": "Adresa 1",
        "is_primary": False,
    }
    res1 = client.post("/api/warehouses", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/warehouses", json=payload)
    assert res2.status_code == 409
    assert "již existuje" in res2.json()["detail"]


def test_warehouse_stock_calculations_and_constraints(client):
    """Ověření dvoufázového stavu zásob: Disponibilní = Fyzická - Rezervovaná a zákaz záporu."""
    # 1. Založení nového produktu a získání primárního skladu HK
    prod_code = f"STK-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Skladová testovací hračka",
        "purchase_price": "100.00",
        "selling_price": "250.00",
        "min_stock_level": 5,
    })
    product_id = p_res.json()["id"]

    wh_list = client.get("/api/warehouses").json()
    hk_warehouse = next(w for w in wh_list if w["code"] == "WH-HK")
    wh_id = hk_warehouse["id"]

    # 2. Nastavení zásoby: 10 fyzicky, 3 rezervováno
    update_res = client.put(f"/api/warehouses/{wh_id}/stocks/{product_id}", json={
        "physical_quantity": 10,
        "reserved_quantity": 3,
    })
    assert update_res.status_code == 200
    stock_data = update_res.json()
    assert stock_data["physical_quantity"] == 10
    assert stock_data["reserved_quantity"] == 3
    assert stock_data["available_quantity"] == 7  # 10 - 3 = 7

    # 3. Pokus o záporný stav zásob (musí selhat s 422)
    neg_res = client.put(f"/api/warehouses/{wh_id}/stocks/{product_id}", json={
        "physical_quantity": -5,
    })
    assert neg_res.status_code == 422

    # 4. Pokus rezervovat víc než je fyzicky (musí selhat s 422)
    over_res = client.put(f"/api/warehouses/{wh_id}/stocks/{product_id}", json={
        "physical_quantity": 10,
        "reserved_quantity": 15,
    })
    assert over_res.status_code == 422


def test_dashboard_summary_api(client):
    """Ověření agregovaných statistik dashboardu (celková hodnota, kusy, co hoří)."""
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["total_products_count"] >= 5
    assert data["total_physical_count"] > 0
    assert float(data["total_stock_value"]) > 0
    assert len(data["warehouses"]) >= 2
    # Ověříme, že obsahuje kritické položky pod minimem
    assert data["critical_items_count"] > 0
    critical_codes = [item["product_code"] for item in data["critical_items"]]
    assert "VLK-001" in critical_codes or "KAC-002" in critical_codes


def test_stocks_overview_endpoint(client):
    """Ověření výpisu rozpadu zásob po skladech s filtrem critical."""
    # Všechny
    res_all = client.get("/api/stocks")
    assert res_all.status_code == 200
    all_stocks = res_all.json()
    assert len(all_stocks) >= 5

    # Pouze hořící pod minimem
    res_crit = client.get("/api/stocks?only_critical=true")
    assert res_crit.status_code == 200
    crit_stocks = res_crit.json()
    assert len(crit_stocks) > 0
    assert all(item["is_below_min"] for item in crit_stocks)


def test_dashboard_web_view(client):
    """Ověření vykreslení HTML dashboardu na úvodní adrese '/'."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    assert "Skladový přehled &amp; Barevný dashboard" in html or "Skladový přehled" in html
    assert "Hradec Králové" in html
    assert "Garáž Třebechovice" in html
    assert "WH-HK" in html
    assert "WH-TREB" in html
    assert "Celková hodnota zásob" in html
    assert "Disponibilní zásoba" in html
    # Indikace co hoří
    assert "položek hoří pod minimem" in html or "Upozornění truhlárny" in html
    assert "Hoří pod minimem" in html
