from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_login_shows_customer_demo_and_redirects_to_shop(anon_client):
    """Přihlašovací stránka nabízí demo zákazníka + registraci a po přihlášení míří do /shop."""
    login_page = anon_client.get("/login")
    assert login_page.status_code == 200
    assert "Marie Svobodová" in login_page.text
    assert "zakaznik" in login_page.text
    assert "Vytvořit účet zákazníka" in login_page.text
    assert "status-dot" not in login_page.text
    assert "&bull;" not in login_page.text

    resp = anon_client.post(
        "/login",
        data={"username": "zakaznik", "password": settings.DEMO_CUSTOMER_PASSWORD, "next": "/"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/shop"

    # Přihlášený zákazník na "/" je automaticky přesměrován do /shop
    root_resp = anon_client.get("/", follow_redirects=False)
    assert root_resp.status_code == 303
    assert root_resp.headers["location"] == "/shop"


def test_customer_rbac_blocks_internal_routes(customer_client):
    """Zákazník smí do /shop a /my-orders, ale interní skladové a manažerské sekce vrací 403."""
    shop_resp = customer_client.get("/shop")
    assert shop_resp.status_code == 200
    assert "E-shop dřevěných hraček" in shop_resp.text
    assert "Marie Svobodová" in shop_resp.text
    assert "Nákupní cena" not in shop_resp.text
    assert "REST API (Swagger)" not in shop_resp.text

    my_orders_resp = customer_client.get("/my-orders")
    assert my_orders_resp.status_code == 200
    assert "Moje objednávky" in my_orders_resp.text
    assert "REST API (Swagger)" not in my_orders_resp.text

    for forbidden_path in [
        "/products",
        "/products/new",
        "/movements",
        "/movements/new",
        "/orders",
        "/orders/new",
        "/customers",
        "/reports",
    ]:
        res = customer_client.get(forbidden_path)
        assert res.status_code == 403, f"Zákazník nesmí mít přístup na {forbidden_path}"

    quick_res = customer_client.post(
        "/quick-action",
        data={
            "action_type": "receipt",
            "product_id": str(uuid4()),
            "quantity": "5",
            "confirmed": "true",
        },
    )
    assert quick_res.status_code == 403


def test_customer_self_registration_creates_customer_and_user_and_orders(client):
    """Samoobslužná registrace založí Customer + User(customer) a umožní ihned objednat."""
    suffix = uuid4().hex[:6]
    username = f"eliska_{suffix}"
    email = f"eliska.{suffix}@example.cz"

    # Založení testovací hračky a jejího naskladnění přes manažera
    sku = f"ESHOP-{suffix.upper()}"
    prod_res = client.post(
        "/api/products",
        json={
            "code": sku,
            "name": f"Dřevěná káča {suffix}",
            "description": "Testovací hračka pro registraci zákazníka",
            "purchase_price": "120.00",
            "selling_price": "290.00",
            "min_stock_level": 3,
            "is_active": True,
            "category_ids": [],
        },
    )
    assert prod_res.status_code == 201
    product_id = prod_res.json()["id"]

    warehouses = client.get("/api/warehouses").json()
    hk_wh = next(w for w in warehouses if w["code"] == "WH-HK")
    client.post(
        "/api/movements/receipt",
        json={
            "warehouse_id": hk_wh["id"],
            "product_id": product_id,
            "quantity": 6,
            "reference_code": f"REG-{suffix}",
            "note": "Příjem pro registrační test",
        },
    )

    with TestClient(app) as reg_client:
        reg_page = reg_client.get("/register")
        assert reg_page.status_code == 200
        assert "Nový zákaznický účet" in reg_page.text

        # Neshodná hesla -> 422
        mismatch = reg_client.post(
            "/register",
            data={
                "username": username,
                "first_name": "Eliška",
                "last_name": "Králová",
                "email": email,
                "phone": "+420 777 555 111",
                "address": "Gočárova 42, 500 02 Hradec Králové",
                "password": "heslo123",
                "password_confirm": "jineheslo",
            },
        )
        assert mismatch.status_code == 422
        assert "Zadaná hesla se neshodují" in mismatch.text

        # Úspěšná registrace -> 303 do /shop
        ok_reg = reg_client.post(
            "/register",
            data={
                "username": username,
                "first_name": "Eliška",
                "last_name": "Králová",
                "email": email,
                "phone": "+420 777 555 111",
                "address": "Gočárova 42, 500 02 Hradec Králové",
                "password": "heslo123",
                "password_confirm": "heslo123",
            },
            follow_redirects=False,
        )
        assert ok_reg.status_code == 303
        assert ok_reg.headers["location"] == "/shop"

        # Nový zákazník vidí svůj profil a může objednat
        shop_res = reg_client.get("/shop")
        assert shop_res.status_code == 200
        assert "Eliška Králová" in shop_res.text

        order_res = reg_client.post(
            "/shop/order",
            data={f"qty_{product_id}": "2", "note": "Registrace + první nákup"},
            follow_redirects=False,
        )
        assert order_res.status_code == 303
        assert order_res.headers["location"].startswith("/my-orders/")

        orders_list = reg_client.get("/my-orders")
        assert orders_list.status_code == 200
        assert "1 druhů" in orders_list.text

    # Zákazník se zapsal do interního adresáře zákazníků s 1 objednávkou
    customers = client.get(f"/api/customers?search={email}").json()
    assert len(customers) == 1
    assert customers[0]["orders_count"] == 1


def test_customer_order_end_to_end_propagation(customer_client, warehouse_client, client):
    """Objednávka zákazníka se propíše do rezervací, alertů, /orders, /customers, expedice i reportů."""
    suffix = uuid4().hex[:6]
    sku = f"TRN-{suffix.upper()}"

    cats = client.get("/api/categories").json()
    cat_id = cats[0]["id"] if cats else None

    prod_res = client.post(
        "/api/products",
        json={
            "code": sku,
            "name": f"Dřevěný vláček E2E {suffix}",
            "description": "Test propisování objednávky zákazníka",
            "purchase_price": "200.00",
            "selling_price": "450.00",
            "min_stock_level": 5,
            "is_active": True,
            "category_ids": [cat_id] if cat_id else [],
        },
    )
    assert prod_res.status_code == 201
    product_id = prod_res.json()["id"]

    warehouses = client.get("/api/warehouses").json()
    hk_wh = next(w for w in warehouses if w["code"] == "WH-HK")

    # Naskladníme 8 ks do Hradce
    receipt_res = client.post(
        "/api/movements/receipt",
        json={
            "warehouse_id": hk_wh["id"],
            "product_id": product_id,
            "quantity": 8,
            "reference_code": f"DL-E2E-{suffix}",
            "note": "Počáteční naskladnění pro E2E zákaznickou objednávku",
        },
    )
    assert receipt_res.status_code == 201

    # 1. Zákazník vidí produkt v /shop se stavem Skladem (8 ks) a prodejní cenou 450.00 Kč
    shop_before = customer_client.get(f"/shop?search={sku}")
    assert shop_before.status_code == 200
    assert "Skladem (8 ks)" in shop_before.text
    assert "450.00 Kč" in shop_before.text
    assert "200.00" not in shop_before.text

    # 2. Pokus o prázdný košík -> 422
    empty_res = customer_client.post("/shop/order", data={f"qty_{product_id}": "0"})
    assert empty_res.status_code == 422

    # 3. Zákazník objedná 4 ks -> zůstane 4 ks (< min_stock_level 5)
    create_res = customer_client.post(
        "/shop/order",
        data={
            f"qty_{product_id}": "4",
            "note": "Prosím dárkově zabalit",
        },
        follow_redirects=False,
    )
    assert create_res.status_code == 303
    detail_url = create_res.headers["location"]
    assert detail_url.startswith("/my-orders/")
    order_id = detail_url.split("/my-orders/")[1].split("?")[0]

    detail_res = customer_client.get(detail_url)
    assert detail_res.status_code == 200
    assert "Objednávka přijata!" in detail_res.text
    assert "Rezervováno (K expedici)" in detail_res.text
    assert "order-item-thumb" in detail_res.text
    assert "/static/img/toys/" in detail_res.text
    assert "Kód SKU" not in detail_res.text
    assert sku not in detail_res.text
    assert "450.00 Kč" in detail_res.text
    assert "1800.00 Kč" in detail_res.text
    assert "Prosím dárkově zabalit" in detail_res.text

    # 4. Ověření rezervace ve skladu a ochrany před přeprodejem
    stock_after = client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}").json()
    assert stock_after["physical_quantity"] == 8
    assert stock_after["reserved_quantity"] == 4
    assert stock_after["available_quantity"] == 4

    oversell = customer_client.post("/shop/order", data={f"qty_{product_id}": "5"})
    assert oversell.status_code == 422
    assert client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}").json()["reserved_quantity"] == 4

    # 5. Propis do upozornění k doobjednání a dashboardu (4 < 5)
    restock_res = client.get("/api/reports/restock-recommendations")
    assert restock_res.status_code == 200
    assert any(item["product_code"] == sku for item in restock_res.json())

    # 6. Neměnnost ceny: manažer změní ceníkovou cenu, ale v zákaznické objednávce zůstane 450.00 Kč
    patch_res = client.put(
        f"/api/products/{product_id}",
        json={"selling_price": "590.00"},
    )
    assert patch_res.status_code == 200
    detail_after_reprice = customer_client.get(f"/my-orders/{order_id}")
    assert "450.00 Kč" in detail_after_reprice.text
    assert "1800.00 Kč" in detail_after_reprice.text

    # 7. Objednávka je viditelná v interním přehledu /orders a skladník ji fyzicky expeduje
    staff_order_page = warehouse_client.get(f"/orders/{order_id}")
    assert staff_order_page.status_code == 200
    assert "Marie Svobodová" in staff_order_page.text
    assert "Smetanovo nábřeží 124" in staff_order_page.text
    assert "order-card-header" in staff_order_page.text

    my_orders_res = customer_client.get("/my-orders")
    assert my_orders_res.status_code == 200
    assert "summary-card" in my_orders_res.text
    assert "table-container" in my_orders_res.text

    dispatch_res = warehouse_client.post(f"/orders/{order_id}/dispatch", follow_redirects=False)
    assert dispatch_res.status_code == 303

    # 8. Ověření fyzického odpisu, auditní stopy (StockMovement), stavu u zákazníka a tržeb v reportu
    stock_dispatched = client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}").json()
    assert stock_dispatched["physical_quantity"] == 4
    assert stock_dispatched["reserved_quantity"] == 0
    assert stock_dispatched["available_quantity"] == 4

    movements = client.get(f"/api/movements?product_id={product_id}&movement_type=dispatch").json()
    assert len(movements) == 1
    assert movements[0]["quantity"] == 4
    assert movements[0]["performed_by"] == "Jan Novák"

    customer_dispatched_view = customer_client.get(f"/my-orders/{order_id}")
    assert customer_dispatched_view.status_code == 200
    assert "Odesláno zákazníkovi" in customer_dispatched_view.text

    if cats:
        turnover_res = client.get("/api/reports/category-turnover")
        assert turnover_res.status_code == 200
        cat_row = next(r for r in turnover_res.json() if r["category_name"] == cats[0]["name"])
        assert Decimal(str(cat_row["total_revenue"])) >= Decimal("1800.00")


def test_customer_order_cancellation_and_isolation(customer_client, client):
    """Zákazník smí stornovat vlastní neexpedovanou objednávku (uvolní rezervaci) a nevidí cizí."""
    suffix = uuid4().hex[:6]
    sku = f"CNC-{suffix.upper()}"
    prod_res = client.post(
        "/api/products",
        json={
            "code": sku,
            "name": f"Storno kostky {suffix}",
            "description": "Test storna zákazníkem",
            "purchase_price": "100.00",
            "selling_price": "250.00",
            "min_stock_level": 2,
            "is_active": True,
            "category_ids": [],
        },
    )
    assert prod_res.status_code == 201
    product_id = prod_res.json()["id"]

    warehouses = client.get("/api/warehouses").json()
    hk_wh = next(w for w in warehouses if w["code"] == "WH-HK")
    client.post(
        "/api/movements/receipt",
        json={
            "warehouse_id": hk_wh["id"],
            "product_id": product_id,
            "quantity": 5,
            "reference_code": f"DL-CNC-{suffix}",
            "note": "Příjem pro storno test",
        },
    )

    order_res = customer_client.post(
        "/shop/order",
        data={f"qty_{product_id}": "3"},
        follow_redirects=False,
    )
    assert order_res.status_code == 303
    order_id = order_res.headers["location"].split("/my-orders/")[1].split("?")[0]
    assert client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}").json()["reserved_quantity"] == 3

    # Jiný přihlášený zákazník má cizí objednávku zablokovanou (403)
    with TestClient(app) as other_cust:
        other_cust.post(
            "/register",
            data={
                "username": f"other_{suffix}",
                "first_name": "Karel",
                "last_name": "Novotný",
                "email": f"karel.{suffix}@example.cz",
                "phone": "+420 606 111 222",
                "address": "Pražská 9, 500 04 Hradec Králové",
                "password": "heslo123",
                "password_confirm": "heslo123",
            },
            follow_redirects=False,
        )
        assert other_cust.get(f"/my-orders/{order_id}").status_code == 403
        assert other_cust.post(f"/my-orders/{order_id}/cancel").status_code == 403

    # Původní zákazník stornuje -> rezervace se ihned uvolní
    cancel_res = customer_client.post(f"/my-orders/{order_id}/cancel", follow_redirects=False)
    assert cancel_res.status_code == 303
    assert "cancelled=1" in cancel_res.headers["location"]

    prod_restored = client.get(f"/api/warehouses/{hk_wh['id']}/stocks/{product_id}").json()
    assert prod_restored["reserved_quantity"] == 0
    assert prod_restored["available_quantity"] == 5


def test_customer_shop_renders_eshop_storefront_and_product_images(customer_client):
    """Zákaznický e-shop zobrazuje výlohu s obrázky hraček a zákaznickými filtry bez kódů SKU."""
    resp = customer_client.get("/shop")
    assert resp.status_code == 200
    html = resp.text
    assert "shop-hero" in html
    assert "Poctivé české hračky ze dřeva" in html
    assert "shop-category-chips" in html
    assert "Všechny hračky" in html
    assert "Dárky do 500 Kč" in html
    assert "Pro kluky" in html
    assert "Pro holky" in html
    assert "Nákupní košík" in html
    assert "Do košíku" in html
    assert "shop-product-img" in html
    assert "/static/img/toys/train.svg" in html
    assert "/static/img/toys/duck.svg" in html
    assert "sku-badge" not in html
    assert "VLK-001" not in html
    assert "KAC-002" not in html
    assert "podle kódu" not in html
    assert "filter-select" not in html
    assert "Batolata-" not in html
    assert "Dárky500-" not in html
    assert "status-dot" not in html
    assert "&bull;" not in html
    assert "·" not in html
    assert "&middot;" not in html
    assert "REST API (Swagger)" not in html
    assert "shop-search-input-wrapper" in html

    # Zákaznické čipy jsou omezené na čistou sadu bez zahlcení z DB
    assert html.count('class="shop-cat-chip') == 6

    do500_res = customer_client.get("/shop?tag=do500")
    assert do500_res.status_code == 200
    assert "Dřevěný vláček" in do500_res.text

    boys_res = customer_client.get("/shop?tag=kluky")
    assert boys_res.status_code == 200
    assert "Dřevěný vláček" in boys_res.text

    girls_res = customer_client.get("/shop?tag=holky")
    assert girls_res.status_code == 200
    assert "Houpací koník" in girls_res.text

    for img_path in [
        "/static/img/toys/train.svg",
        "/static/img/toys/duck.svg",
        "/static/img/toys/rocking_horse.svg",
        "/static/img/toys/default_toy.svg",
    ]:
        img_res = customer_client.get(img_path)
        assert img_res.status_code == 200, f"Obrázek {img_path} se nepodařilo načíst"
        assert "<svg" in img_res.text


def test_staff_views_render_toy_thumbnails(client, warehouse_client):
    """Náhledové ilustrace hraček se zobrazují i jednateli a skladníkovi v přehledech, pohybech a reportech."""
    for test_client in (client, warehouse_client):
        for path in ("/", "/products", "/movements"):
            res = test_client.get(path)
            assert res.status_code == 200
            assert "staff-toy-thumb" in res.text
            assert "/static/img/toys/" in res.text

    reports_res = client.get("/reports")
    assert reports_res.status_code == 200
    assert "staff-toy-thumb" in reports_res.text
    assert "/static/img/toys/" in reports_res.text
    assert "REST API (Swagger)" in reports_res.text
