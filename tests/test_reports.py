import uuid
from decimal import Decimal
import pytest


def test_category_turnover_with_mn_relationship(client):
    """
    Test Fáze 7:
    Měsíční obrat po kategoriích a M:N vazba.
    Pokud hračka patří do více kategorií současně, její tržby se správně promítnou
    do všech jejích přiřazených kategorií.
    """
    # 1. Založíme dvě testovací kategorie
    cat_res1 = client.post("/api/categories", json={
        "name": f"Hračky pro kluky {uuid.uuid4().hex[:6]}",
        "description": "Auta, vláčky a stavebnice",
    })
    cat_res2 = client.post("/api/categories", json={
        "name": f"Dárky na Vánoce {uuid.uuid4().hex[:6]}",
        "description": "Sezónní vánoční inspirace",
    })
    cat1_id = cat_res1.json()["id"]
    cat2_id = cat_res2.json()["id"]

    # 2. Založíme produkt se dvěma kategoriemi
    prod_code = f"REP-{uuid.uuid4().hex[:6].upper()}"
    p_res = client.post("/api/products", json={
        "code": prod_code,
        "name": "Dřevěný parní vláček s tendrem",
        "purchase_price": "200.00",
        "selling_price": "500.00",
        "min_stock_level": 5,
        "category_ids": [cat1_id, cat2_id],
    })
    assert p_res.status_code == 201
    product = p_res.json()
    product_id = product["id"]

    # 3. Získáme sklad HK a naskladníme 10 kusů
    wh_list = client.get("/api/warehouses").json()
    hk_wh = next(w for w in wh_list if w["code"] == "WH-HK")
    client.post("/api/movements/receipt", json={
        "warehouse_id": hk_wh["id"],
        "product_id": product_id,
        "quantity": 10,
    })

    # 4. Získáme zákazníka a vytvoříme objednávku na 2 kusy
    cust = client.get("/api/customers").json()[0]
    order_res = client.post("/api/orders", json={
        "customer_id": cust["id"],
        "warehouse_id": hk_wh["id"],
        "items": [
            {"product_id": product_id, "quantity": 2}
        ],
    })
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # 5. Expedujeme objednávku (status DISPATCHED)
    disp_res = client.post(f"/api/orders/{order_id}/dispatch")
    assert disp_res.status_code == 200

    # 6. Zavoláme API pro obrat po kategoriích
    rep_res = client.get("/api/reports/category-turnover")
    assert rep_res.status_code == 200
    cat_data = rep_res.json()

    # Najdeme obě testované kategorie
    cat1_stat = next(c for c in cat_data if c["category_id"] == cat1_id)
    cat2_stat = next(c for c in cat_data if c["category_id"] == cat2_id)

    # Obě kategorie musí obsahovat tržby z tohoto produktu (2 ks * 500 Kč = 1000 Kč)
    assert cat1_stat["items_sold_count"] >= 2
    assert Decimal(cat1_stat["total_revenue"]) >= Decimal("1000.00")
    assert Decimal(cat1_stat["total_cost"]) >= Decimal("400.00")
    assert Decimal(cat1_stat["gross_profit"]) >= Decimal("600.00")
    assert Decimal(cat1_stat["margin_percentage"]) > Decimal("0.00")

    assert cat2_stat["items_sold_count"] >= 2
    assert Decimal(cat2_stat["total_revenue"]) >= Decimal("1000.00")
    assert Decimal(cat2_stat["total_cost"]) >= Decimal("400.00")
    assert Decimal(cat2_stat["gross_profit"]) >= Decimal("600.00")


def test_financial_summary_and_modes(client):
    """Test celkového finančního přehledu e-shopu a přepínání rezervací."""
    # 1. Pouze realizované tržby
    res_dispatched = client.get("/api/reports/financial-summary?include_reserved=false")
    assert res_dispatched.status_code == 200
    sum_disp = res_dispatched.json()

    assert "total_revenue" in sum_disp
    assert "total_cost" in sum_disp
    assert "total_gross_profit" in sum_disp
    assert "average_margin_percentage" in sum_disp

    rev = Decimal(sum_disp["total_revenue"])
    cost = Decimal(sum_disp["total_cost"])
    profit = Decimal(sum_disp["total_gross_profit"])
    assert profit == rev - cost

    # 2. Včetně rozpracovaných rezervací
    res_all = client.get("/api/reports/financial-summary?include_reserved=true")
    assert res_all.status_code == 200
    sum_all = res_all.json()
    assert Decimal(sum_all["total_revenue"]) >= rev


def test_top_selling_products(client):
    """Test žebříčku nejprodávanějších hraček za dané období."""
    res = client.get("/api/reports/top-products?limit=5")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    if items:
        first = items[0]
        assert "product_code" in first
        assert "units_sold" in first
        assert "total_revenue" in first
        assert "margin_percentage" in first


def test_restock_recommendation_logic(client):
    """
    Test byznys logiky doporučení k doobjednání (ADR 1 & Zadání B):
    1. Položka chybí na centrále HK, ale je v garáži -> doporučí TRANSFER_FROM_GARAGE
    2. Položka chybí všude -> doporučí PRODUCE_IN_WORKSHOP
    """
    wh_list = client.get("/api/warehouses").json()
    hk_wh = next(w for w in wh_list if w["code"] == "WH-HK")
    treb_wh = next(w for w in wh_list if w["code"] == "WH-TREB")

    # Scénář 1: Zásoba pouze v garáži Třebechovice, na centrále HK 0
    code_transfer = f"REST-TR-{uuid.uuid4().hex[:6].upper()}"
    p_res1 = client.post("/api/products", json={
        "code": code_transfer,
        "name": "Dřevěná káča pro transfer",
        "purchase_price": "30.00",
        "selling_price": "80.00",
        "min_stock_level": 6,
    })
    prod1_id = p_res1.json()["id"]

    # Naskladníme 10 kusů pouze do Garáže Třebechovice (WH-TREB)
    client.post("/api/movements/receipt", json={
        "warehouse_id": treb_wh["id"],
        "product_id": prod1_id,
        "quantity": 10,
    })

    # Scénář 2: Zásoba chybí všude (0 kusů celkem)
    code_produce = f"REST-PR-{uuid.uuid4().hex[:6].upper()}"
    p_res2 = client.post("/api/products", json={
        "code": code_produce,
        "name": "Houpací koník na objednávku",
        "purchase_price": "500.00",
        "selling_price": "1200.00",
        "min_stock_level": 8,
    })
    prod2_id = p_res2.json()["id"]

    # Zavoláme API doporučení k doobjednání
    rec_res = client.get("/api/reports/restock-recommendations")
    assert rec_res.status_code == 200
    recommendations = rec_res.json()

    # Najdeme obě testované položky
    rec_transfer = next((r for r in recommendations if r["product_id"] == prod1_id), None)
    rec_produce = next((r for r in recommendations if r["product_id"] == prod2_id), None)

    assert rec_transfer is not None
    assert rec_transfer["action_type"] == "TRANSFER_FROM_GARAGE"
    assert "transfer" in rec_transfer["direct_action_url"]
    assert "source_warehouse_id" in rec_transfer["direct_action_url"]

    assert rec_produce is not None
    assert rec_produce["action_type"] == "PRODUCE_IN_WORKSHOP"
    assert rec_produce["urgency"] == "CRITICAL"
    assert "receipt" in rec_produce["direct_action_url"]


def test_web_reports_dashboard_view(client):
    """Test vykreslení webového rozhraní /reports."""
    # 1. Výchozí zobrazení
    res = client.get("/reports")
    assert res.status_code == 200
    html = res.text
    assert "Manažerský reporting" in html
    assert "Celkový obrat" in html
    assert "Hrubý zisk sortimentu" in html
    assert "Obrat a ziskovost po kategoriích" in html
    assert "Doporučení k doobjednání" in html
    assert "TOP nejprodávanější dřevěné hračky" in html

    # 2. Filtrované zobrazení s parametry
    filter_res = client.get("/reports?year=2026&month=10&include_reserved=true")
    assert filter_res.status_code == 200
    filter_html = filter_res.text
    assert "Říjen 2026" in filter_html
    assert "Režim: Včetně otevřených rezervací" in filter_html
