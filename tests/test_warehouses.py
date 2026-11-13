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
    created_id = res1.json()["id"]

    try:
        res2 = client.post("/api/warehouses", json=payload)
        assert res2.status_code == 409
        assert "již existuje" in res2.json()["detail"]
    finally:
        # Úklid, aby se nehromadily testovací sklady
        client.delete(f"/api/warehouses/{created_id}")


def test_create_and_delete_warehouse(client):
    """Ověření, že uživatel může volně zakládat i mazat sklady dle libosti."""
    code = f"WL-{uuid.uuid4().hex[:4].upper()}"
    res = client.post("/api/warehouses", json={
        "code": code,
        "name": f"Nový uživatelský sklad {code}",
        "location": "Pobočka Liberec",
        "is_primary": False,
    })
    assert res.status_code == 201
    wh_id = res.json()["id"]

    # Ověříme, že sklad existuje v seznamu
    list_res = client.get("/api/warehouses")
    assert any(w["id"] == wh_id for w in list_res.json())

    # Smažeme sklad
    del_res = client.delete(f"/api/warehouses/{wh_id}")
    assert del_res.status_code == 204

    # Ověříme, že už neexistuje
    get_res = client.get(f"/api/warehouses/{wh_id}")
    assert get_res.status_code == 404



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
    assert "Dochází" in html
    assert "Doplnit na sklad" in html
    assert 'id="quickRestockModal"' in html
    assert 'id="quickActionConfirmed"' in html


def test_dashboard_quick_restock_and_transfer_requires_confirmation(client):
    """Rychlé doplnění / přesun z upozornění docházejících položek vyžaduje vědomé potvrzení."""
    import uuid

    warehouses = client.get("/api/warehouses").json()
    hk = next(w for w in warehouses if w["code"] == "WH-HK")
    treb = next(w for w in warehouses if w["code"] == "WH-TREB")

    prod_res = client.post(
        "/api/products",
        json={
            "name": "Testovací docházející koník",
            "code": f"QCK-{uuid.uuid4().hex[:6].upper()}",
            "purchase_price": "100.00",
            "selling_price": "250.00",
            "min_stock_level": 10,
            "is_active": True,
        },
    )
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["id"]

    # Naskladníme 2 ks do garáže, takže celkem 2 < min 10 -> zobrazí se tlačítko Přesunout z garáže i Doplnit
    assert client.post(
        "/api/movements/receipt",
        json={"warehouse_id": treb["id"], "product_id": prod_id, "quantity": 2, "note": "Setup"},
    ).status_code == 201

    dash_html = client.get("/").text
    assert "Přesunout z garáže" in dash_html

    # 1. Pokus bez potvrzení (confirmed chybí) -> musí být odmítnuto (422) a stav zůstane 0 / 2
    fail_resp = client.post(
        "/quick-action",
        data={
            "action_type": "transfer",
            "product_id": prod_id,
            "source_warehouse_id": treb["id"],
            "destination_warehouse_id": hk["id"],
            "quantity": "2",
        },
        follow_redirects=False,
    )
    assert fail_resp.status_code == 422
    assert "vědomé potvrzení" in fail_resp.text

    # 2. Potvrzený rychlý přesun z garáže do Hradce
    ok_transfer = client.post(
        "/quick-action",
        data={
            "action_type": "transfer",
            "product_id": prod_id,
            "source_warehouse_id": treb["id"],
            "destination_warehouse_id": hk["id"],
            "quantity": "2",
            "confirmed": "true",
        },
        follow_redirects=False,
    )
    assert ok_transfer.status_code == 303
    assert "action_ok=transfer" in ok_transfer.headers["location"]

    # 3. Potvrzené rychlé doplnění na centrální sklad Hradec
    ok_receipt = client.post(
        "/quick-action",
        data={
            "action_type": "receipt",
            "product_id": prod_id,
            "warehouse_id": hk["id"],
            "quantity": "8",
            "confirmed": "true",
        },
        follow_redirects=False,
    )
    assert ok_receipt.status_code == 303
    assert "action_ok=receipt" in ok_receipt.headers["location"]

    # Ověříme výsledný stav přes API
    stocks = client.get("/api/stocks").json()
    item = next(s for s in stocks if s["product_id"] == prod_id)
    assert item["stocks"]["WH-HK"]["available_quantity"] == 10
    assert item["stocks"]["WH-TREB"]["available_quantity"] == 0
    assert item["is_below_min"] is False

