import uuid
import pytest


def test_record_receipt_increases_stock_and_creates_movement(client):
    """Příjem z truhlárny navýší fyzickou zásobu a vytvoří auditní záznam."""
    prod_code = f"RCP-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Přijímaná hračka",
        "purchase_price": "50.00",
        "selling_price": "120.00",
        "min_stock_level": 5,
    })
    product_id = p_res.json()["id"]

    wh_list = client.get("/api/warehouses").json()
    hk_wh = next(w for w in wh_list if w["code"] == "WH-HK")

    # Provedení příjmu 20 ks
    receipt_res = client.post("/api/movements/receipt", json={
        "warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "quantity": 20,
        "reference_code": "DL-TEST/01",
        "note": "Zkušební příjem z dílny",
    })
    assert receipt_res.status_code == 201
    movement = receipt_res.json()
    assert movement["movement_type"] == "receipt"
    assert movement["quantity"] == 20
    assert movement["destination_warehouse_code"] == "WH-HK"
    assert movement["source_warehouse_code"] is None
    assert movement["reference_code"] == "DL-TEST/01"

    # Kontrola stavu zásoby
    stock_res = client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}")
    assert stock_res.status_code == 200
    assert stock_res.json()["physical_quantity"] == 20
    assert stock_res.json()["available_quantity"] == 20


def test_record_dispatch_decreases_stock_and_prevents_negative(client):
    """Výdej (expedice) sníží zásobu; pokus o výdej do záporu je striktně odmítnut (422)."""
    prod_code = f"DSP-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Expedovaná hračka",
        "purchase_price": "80.00",
        "selling_price": "190.00",
        "min_stock_level": 3,
    })
    product_id = p_res.json()["id"]

    wh_list = client.get("/api/warehouses").json()
    hk_wh = next(w for w in wh_list if w["code"] == "WH-HK")

    # 1. Nejprve naskladníme 10 ks
    client.post("/api/movements/receipt", json={
        "warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "quantity": 10,
    })

    # 2. Vydáme 4 ks (povolený výdej)
    dispatch_res = client.post("/api/movements/dispatch", json={
        "warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "quantity": 4,
        "reference_code": "OBJ-100",
        "note": "Expedice balíku",
    })
    assert dispatch_res.status_code == 201
    assert dispatch_res.json()["quantity"] == 4
    assert dispatch_res.json()["source_warehouse_code"] == "WH-HK"

    # Zásoba klesla na 6
    stock_res = client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}")
    assert stock_res.json()["physical_quantity"] == 6

    # 3. Pokus o výdej 10 ks (při stavu 6) -> musí selhat s 422 InsufficientStockError
    fail_res = client.post("/api/movements/dispatch", json={
        "warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "quantity": 10,
    })
    assert fail_res.status_code == 422
    assert "Nedostatečná zásoba" in fail_res.json()["detail"]

    # Zásoba zůstala 6 (žádný záporný stav)
    stock_after = client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}")
    assert stock_after.json()["physical_quantity"] == 6


def test_record_transfer_moves_stock_between_warehouses(client):
    """Meziskladový přesun z Garáže Třebechovice do Hradce Králové."""
    prod_code = f"TRF-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Převážená dřevěná kostka",
        "purchase_price": "40.00",
        "selling_price": "99.00",
        "min_stock_level": 5,
    })
    product_id = p_res.json()["id"]

    wh_list = client.get("/api/warehouses").json()
    hk_wh = next(w for w in wh_list if w["code"] == "WH-HK")
    treb_wh = next(w for w in wh_list if w["code"] == "WH-TREB")

    # V garáži Třebechovice máme 15 ks, v HK 2 ks
    client.put(f"/api/warehouses/{treb_wh['id']}/stocks/{product_id}", json={
        "physical_quantity": 15,
        "reserved_quantity": 0,
    })
    client.put(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}", json={
        "physical_quantity": 2,
        "reserved_quantity": 0,
    })

    # Přesuneme 8 ks z Třebechovic do HK
    trf_res = client.post("/api/movements/transfer", json={
        "source_warehouse_id": treb_wh["id"],
        "destination_warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "quantity": 8,
        "reference_code": "PREV-2026/01",
        "note": "Závoz před vánoční špičkou",
    })
    assert trf_res.status_code == 201
    movement = trf_res.json()
    assert movement["movement_type"] == "transfer"
    assert movement["source_warehouse_code"] == "WH-TREB"
    assert movement["destination_warehouse_code"] == "WH-HK"
    assert movement["quantity"] == 8

    # V Třebechovicích zbývá 7 (15 - 8)
    treb_stock = client.get(f"/api/warehouses/{treb_wh['id']}/stocks/{product_id}").json()
    assert treb_stock["physical_quantity"] == 7

    # V Hradci je nyní 10 (2 + 8)
    hk_stock = client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}").json()
    assert hk_stock["physical_quantity"] == 10


def test_transfer_validation_errors(client):
    """Ověření chybových stavů převodu: stejný sklad a nedostatek volných kusů."""
    prod_code = f"ERR-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Chybový produkt",
        "purchase_price": "10.00",
        "selling_price": "20.00",
        "min_stock_level": 1,
    })
    product_id = p_res.json()["id"]

    wh_list = client.get("/api/warehouses").json()
    hk_wh = next(w for w in wh_list if w["code"] == "WH-HK")
    treb_wh = next(w for w in wh_list if w["code"] == "WH-TREB")

    # 1. Stejný zdrojový i cílový sklad
    same_res = client.post("/api/movements/transfer", json={
        "source_warehouse_id": hk_wh["id"],
        "destination_warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "quantity": 5,
    })
    assert same_res.status_code == 422
    assert "různé" in same_res.json()["detail"]

    # 2. V Třebechovicích je 5 ks, z toho 4 rezervované (pouze 1 k dispozici)
    client.put(f"/api/warehouses/{treb_wh['id']}/stocks/{product_id}", json={
        "physical_quantity": 5,
        "reserved_quantity": 4,
    })
    exceed_res = client.post("/api/movements/transfer", json={
        "source_warehouse_id": treb_wh["id"],
        "destination_warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "quantity": 3,
    })
    assert exceed_res.status_code == 422
    assert "Nedostatečná zásoba" in exceed_res.json()["detail"]


def test_inventory_adjustment_surplus_and_shortage(client):
    """Inventurní vyrovnání skladu: řešení přebytku i manka s auditní stopou."""
    prod_code = f"INV-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Inventurní hračka",
        "purchase_price": "30.00",
        "selling_price": "70.00",
        "min_stock_level": 2,
    })
    product_id = p_res.json()["id"]

    wh_list = client.get("/api/warehouses").json()
    treb_wh = next(w for w in wh_list if w["code"] == "WH-TREB")

    # Původní stav: 5 ks
    client.put(f"/api/warehouses/{treb_wh['id']}/stocks/{product_id}", json={
        "physical_quantity": 5,
        "reserved_quantity": 0,
    })

    # A) Nalezen přebytek (na regále je fyzicky 8 ks)
    adj_surplus = client.post("/api/movements/inventory-adjustment", json={
        "warehouse_id": treb_wh["id"],
        "product_id": product_id,
        "actual_quantity": 8,
        "note": "Nalezeny 3 ks ve vedlejší polici",
    })
    assert adj_surplus.status_code == 201
    surplus_data = adj_surplus.json()
    assert surplus_data["movement_type"] == "inventory_adjustment"
    assert surplus_data["quantity"] == 3
    assert surplus_data["destination_warehouse_code"] == "WH-TREB"
    assert "přebytek" in surplus_data["note"]

    # Fyzický stav je nyní 8 ks
    assert client.get(f"/api/warehouses/{treb_wh['id']}/stocks/{product_id}").json()["physical_quantity"] == 8

    # B) Nalezeno manko (poškozeno vodou, na regále zbývá 6 ks)
    adj_shortage = client.post("/api/movements/inventory-adjustment", json={
        "warehouse_id": treb_wh["id"],
        "product_id": product_id,
        "actual_quantity": 6,
        "note": "2 ks vyřazeny kvůli poškození",
    })
    assert adj_shortage.status_code == 201
    shortage_data = adj_shortage.json()
    assert shortage_data["quantity"] == 2
    assert shortage_data["source_warehouse_code"] == "WH-TREB"
    assert "manko" in shortage_data["note"]

    # Fyzický stav je nyní 6 ks
    assert client.get(f"/api/warehouses/{treb_wh['id']}/stocks/{product_id}").json()["physical_quantity"] == 6


def test_inventory_adjustment_cannot_drop_below_reserved(client):
    """Inventurní stav nesmí klesnout pod již rezervované kusy pro zákazníky."""
    prod_code = f"RES-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Rezervovaná hračka",
        "purchase_price": "50.00",
        "selling_price": "100.00",
        "min_stock_level": 2,
    })
    product_id = p_res.json()["id"]

    wh_list = client.get("/api/warehouses").json()
    hk_wh = next(w for w in wh_list if w["code"] == "WH-HK")

    # 10 fyzicky, 4 rezervováno pro objednávky
    client.put(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}", json={
        "physical_quantity": 10,
        "reserved_quantity": 4,
    })

    # Pokusíme se inventurou snížit fyzický stav na 2 (což je méně než 4 rezervované)
    fail_adj = client.post("/api/movements/inventory-adjustment", json={
        "warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "actual_quantity": 2,
        "note": "Ztráta zboží",
    })
    assert fail_adj.status_code == 422
    assert "Nedostatečná zásoba" in fail_adj.json()["detail"]


def test_list_movements_api_filtering(client):
    """Test filtrování auditního deníku podle typu pohybu a produktu."""
    res_all = client.get("/api/movements")
    assert res_all.status_code == 200
    all_movements = res_all.json()
    assert len(all_movements) > 0

    # Filtrovat pouze příjmy
    res_receipts = client.get("/api/movements?movement_type=receipt")
    assert res_receipts.status_code == 200
    for m in res_receipts.json():
        assert m["movement_type"] == "receipt"


def test_web_movements_views_and_form_submissions(client):
    """Ověření webového rozhraní auditního deníku a formuláře."""
    # 1. Zobrazení deníku
    list_page = client.get("/movements")
    assert list_page.status_code == 200
    assert "Auditní deník skladových pohybů" in list_page.text

    # 2. Zobrazení formuláře
    form_page = client.get("/movements/new?movement_type=receipt")
    assert form_page.status_code == 200
    assert "Zadání skladového pohybu" in form_page.text

    # 3. Odeslání formuláře příjmu
    wh_list = client.get("/api/warehouses").json()
    wh = wh_list[0]
    prod_list = client.get("/api/products").json()
    prod = prod_list[0]

    receipt_form_res = client.post(
        "/movements/receipt",
        data={
            "warehouse_id": wh["id"],
            "product_id": prod["id"],
            "quantity": 7,
            "reference_code": "WEB-DL-01",
            "note": "Webový příjem",
        },
        follow_redirects=False,
    )
    assert receipt_form_res.status_code == 303
    assert receipt_form_res.headers["location"] == "/movements"

    # 4. Odeslání nevalidního převodu vrátí 422 a chybové hlášení
    invalid_trf_res = client.post(
        "/movements/transfer",
        data={
            "source_warehouse_id": wh["id"],
            "destination_warehouse_id": wh["id"],  # Stejný sklad!
            "product_id": prod["id"],
            "quantity": 5,
        },
    )
    assert invalid_trf_res.status_code == 422
    assert "Chyba při meziskladovém přesunu" in invalid_trf_res.text
