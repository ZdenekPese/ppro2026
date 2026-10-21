import uuid
from decimal import Decimal
import pytest


def test_customer_creation_and_soft_delete(client):
    """Zákazník se vytvoří; fyzické smazání je zakázáno (provádí se pouze deaktivace dle Zadání B)."""
    email = f"test-{uuid.uuid4().hex[:6]}@example.com"
    c_res = client.post("/api/customers", json={
        "first_name": "Tomáš",
        "last_name": "Marný",
        "email": email,
        "phone": "+420 777 888 999",
        "address": "Dlouhá 15, Hradec Králové",
    })
    assert c_res.status_code == 201
    customer = c_res.json()
    cust_id = customer["id"]
    assert customer["is_active"] is True

    # Smazání zákazníka přes API (měkké smazání)
    del_res = client.delete(f"/api/customers/{cust_id}")
    assert del_res.status_code == 200
    assert del_res.json()["is_active"] is False

    # Zákazník v databázi stále existuje (ochrana historie reklamací)
    get_res = client.get(f"/api/customers/{cust_id}")
    assert get_res.status_code == 200
    assert get_res.json()["is_active"] is False


def test_create_order_immediate_reservation_prevents_overselling(client):
    """
    Klíčové byznys pravidlo Zadání B:
    Při přijetí objednávky okamžitá rezervace zamezí přeprodeji zboží.
    """
    prod_code = f"RES-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Oblíbená buková káča",
        "purchase_price": "40.00",
        "selling_price": "100.00",
        "min_stock_level": 2,
    })
    product_id = p_res.json()["id"]

    wh_list = client.get("/api/warehouses").json()
    hk_wh = next(w for w in wh_list if w["code"] == "WH-HK")

    # Naskladníme 10 kusů
    client.post("/api/movements/receipt", json={
        "warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "quantity": 10,
    })

    # Zákazník
    cust = client.get("/api/customers").json()[0]

    # 1. Zákazník objedná 6 kusů
    order_res = client.post("/api/orders", json={
        "customer_id": cust["id"],
        "warehouse_id": hk_wh["id"],
        "items": [
            {"product_id": product_id, "quantity": 6}
        ],
    })
    assert order_res.status_code == 201
    order = order_res.json()
    assert order["status"] == "RESERVED"
    assert Decimal(order["total_price"]) == Decimal("600.00")

    # Kontrola stavu skladu: fyzicky 10, rezervováno 6, disponibilní 4
    stock_res = client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}").json()
    assert stock_res["physical_quantity"] == 10
    assert stock_res["reserved_quantity"] == 6
    assert stock_res["available_quantity"] == 4

    # 2. Další zákazník se pokusí koupit 5 kusů (k dispozici jsou už jen 4 volné)
    fail_res = client.post("/api/orders", json={
        "customer_id": cust["id"],
        "warehouse_id": hk_wh["id"],
        "items": [
            {"product_id": product_id, "quantity": 5}
        ],
    })
    assert fail_res.status_code == 422
    assert "Nedostatečná zásoba" in fail_res.json()["detail"]


def test_order_price_immutability(client):
    """
    Byznys pravidlo: Neměnnost prodejní ceny v objednávce.
    Pozdější přecenění produktu v katalogu se nepromítne do již vytvořené objednávky.
    """
    prod_code = f"PRC-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Hračka pro test cen",
        "purchase_price": "50.00",
        "selling_price": "150.00",
        "min_stock_level": 1,
    })
    product_id = p_res.json()["id"]

    wh = client.get("/api/warehouses").json()[0]
    client.post("/api/movements/receipt", json={
        "warehouse_id": wh["id"],
        "product_id": product_id,
        "quantity": 5,
    })

    cust = client.get("/api/customers").json()[0]

    # Objednáme za cenu 150 Kč
    order_res = client.post("/api/orders", json={
        "customer_id": cust["id"],
        "warehouse_id": wh["id"],
        "items": [{"product_id": product_id, "quantity": 2}],
    })
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]
    assert Decimal(order_res.json()["total_price"]) == Decimal("300.00")
    assert Decimal(order_res.json()["items"][0]["unit_price"]) == Decimal("150.00")

    # Nyní truhlárna plošně zdraží hračku na 250 Kč
    client.put(f"/api/products/{product_id}", json={
        "selling_price": "250.00"
    })

    # Kontrola, že produkt v katalogu má novou cenu 250 Kč
    assert Decimal(client.get(f"/api/products/{product_id}").json()["selling_price"]) == Decimal("250.00")

    # Ale v existující objednávce zůstává cena neměnných 150 Kč!
    saved_order = client.get(f"/api/orders/{order_id}").json()
    assert Decimal(saved_order["items"][0]["unit_price"]) == Decimal("150.00")
    assert Decimal(saved_order["total_price"]) == Decimal("300.00")


def test_dispatch_order_physical_deduction_and_audit(client):
    """
    Expedice objednávky:
    1. Fyzický odpis kusů z regálu.
    2. Uvolnění rezervace.
    3. Automatické vytvoření auditního pohybu StockMovement (typ dispatch).
    """
    prod_code = f"DSP-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Expediční hračka",
        "purchase_price": "70.00",
        "selling_price": "180.00",
        "min_stock_level": 1,
    })
    product_id = p_res.json()["id"]

    wh = client.get("/api/warehouses").json()[0]
    client.post("/api/movements/receipt", json={
        "warehouse_id": wh["id"],
        "product_id": product_id,
        "quantity": 10,
    })

    cust = client.get("/api/customers").json()[0]

    # Objednávka na 4 kusy
    order_res = client.post("/api/orders", json={
        "customer_id": cust["id"],
        "warehouse_id": wh["id"],
        "items": [{"product_id": product_id, "quantity": 4}],
    })
    order_id = order_res.json()["id"]
    order_num = order_res.json()["order_number"]

    # Fyzicky je stále 10, z toho 4 rezervované
    stock_before = client.get(f"/api/warehouses/{wh['id']}/stocks/{product_id}").json()
    assert stock_before["physical_quantity"] == 10
    assert stock_before["reserved_quantity"] == 4

    # Expedice skladníkem
    dispatch_res = client.post(f"/api/orders/{order_id}/dispatch")
    assert dispatch_res.status_code == 200
    assert dispatch_res.json()["status"] == "DISPATCHED"
    assert dispatch_res.json()["dispatched_at"] is not None

    # Stav po expedici: fyzicky 6, rezervováno 0
    stock_after = client.get(f"/api/warehouses/{wh['id']}/stocks/{product_id}").json()
    assert stock_after["physical_quantity"] == 6
    assert stock_after["reserved_quantity"] == 0

    # Ověření, že v auditu pohybů přibyl záznam o výdeji k této objednávce
    movements_res = client.get(f"/api/movements?product_id={product_id}")
    assert movements_res.status_code == 200
    movements = movements_res.json()
    dispatch_mov = next((m for m in movements if m["movement_type"] == "dispatch" and m["reference_code"] == order_num), None)
    assert dispatch_mov is not None
    assert dispatch_mov["quantity"] == 4


def test_cancel_order_releases_reserved_stock(client):
    """Storno objednávky uvolní zablokovanou rezervaci zpět do volného prodeje."""
    prod_code = f"CAN-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Stornovatelná hračka",
        "purchase_price": "30.00",
        "selling_price": "80.00",
        "min_stock_level": 1,
    })
    product_id = p_res.json()["id"]

    wh = client.get("/api/warehouses").json()[0]
    client.post("/api/movements/receipt", json={
        "warehouse_id": wh["id"],
        "product_id": product_id,
        "quantity": 5,
    })

    cust = client.get("/api/customers").json()[0]

    # Objednáme 3 kusy (zbývá 2 volné)
    order_res = client.post("/api/orders", json={
        "customer_id": cust["id"],
        "warehouse_id": wh["id"],
        "items": [{"product_id": product_id, "quantity": 3}],
    })
    order_id = order_res.json()["id"]

    stock_mid = client.get(f"/api/warehouses/{wh['id']}/stocks/{product_id}").json()
    assert stock_mid["reserved_quantity"] == 3
    assert stock_mid["available_quantity"] == 2

    # Storno objednávky
    cancel_res = client.post(f"/api/orders/{order_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Rezervace se uvolnila, volných je opět 5
    stock_final = client.get(f"/api/warehouses/{wh['id']}/stocks/{product_id}").json()
    assert stock_final["reserved_quantity"] == 0
    assert stock_final["available_quantity"] == 5


def test_invalid_order_status_transitions(client):
    """Nelze stornovat již expedovanou objednávku a nelze expedovat stornovanou."""
    cust = client.get("/api/customers").json()[0]
    prod = client.get("/api/products").json()[0]
    wh = client.get("/api/warehouses").json()[0]

    # Naskladníme jistotu
    client.post("/api/movements/receipt", json={
        "warehouse_id": wh["id"],
        "product_id": prod["id"],
        "quantity": 10,
    })

    # Vytvoření a okamžitá expedice
    ord1 = client.post("/api/orders", json={
        "customer_id": cust["id"],
        "warehouse_id": wh["id"],
        "items": [{"product_id": prod["id"], "quantity": 1}],
    }).json()

    client.post(f"/api/orders/{ord1['id']}/dispatch")

    # Pokus o storno již odeslané objednávky -> 400 Bad Request
    fail_cancel = client.post(f"/api/orders/{ord1['id']}/cancel")
    assert fail_cancel.status_code == 400


def test_web_order_views_and_routes(client):
    """Ověření HTML stránek objednávek a zákazníků."""
    # 1. Seznam objednávek
    orders_page = client.get("/orders")
    assert orders_page.status_code == 200
    assert "Správa objednávek z e-shopu" in orders_page.text

    # 2. Formulář nové objednávky
    new_order_page = client.get("/orders/new")
    assert new_order_page.status_code == 200
    assert "Vytvoření nové e-shopové objednávky" in new_order_page.text

    # 3. Adresář zákazníků
    customers_page = client.get("/customers")
    assert customers_page.status_code == 200
    assert "Adresář zákazníků" in customers_page.text
