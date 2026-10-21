import uuid
import pytest


def test_create_category_success(client):
    """Ověření úspěšného vytvoření kategorie dřevěných hraček přes REST API."""
    unique_name = f"Kategorie {uuid.uuid4().hex[:6]}"
    payload = {
        "name": unique_name,
        "description": "Popis testovací kategorie hraček",
    }
    response = client.post("/api/categories", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == unique_name
    assert data["description"] == "Popis testovací kategorie hraček"
    assert "id" in data


def test_create_duplicate_category_fails(client):
    """Ověření, že duplicitní název kategorie vrátí 409 Conflict."""
    unique_name = f"Unikátní {uuid.uuid4().hex[:6]}"
    payload = {"name": unique_name, "description": "První záznam"}
    
    res1 = client.post("/api/categories", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/categories", json=payload)
    assert res2.status_code == 409
    assert "již existuje" in res2.json()["detail"]


def test_list_and_get_category(client):
    """Ověření výpisu kategorií a detailu konkrétní kategorie."""
    unique_name = f"Kat-{uuid.uuid4().hex[:6]}"
    create_res = client.post("/api/categories", json={"name": unique_name})
    assert create_res.status_code == 201
    cat_id = create_res.json()["id"]

    # Výpis
    list_res = client.get("/api/categories")
    assert list_res.status_code == 200
    categories = list_res.json()
    assert any(c["id"] == cat_id for c in categories)

    # Detail
    get_res = client.get(f"/api/categories/{cat_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == unique_name


def test_update_and_delete_category(client):
    """Ověření editace a smazání kategorie."""
    unique_name = f"Upd-{uuid.uuid4().hex[:6]}"
    cat_res = client.post("/api/categories", json={"name": unique_name})
    cat_id = cat_res.json()["id"]

    # Update
    updated_name = f"{unique_name} Upraveno"
    upd_res = client.put(f"/api/categories/{cat_id}", json={"name": updated_name, "description": "Nový popis"})
    assert upd_res.status_code == 200
    assert upd_res.json()["name"] == updated_name

    # Delete
    del_res = client.delete(f"/api/categories/{cat_id}")
    assert del_res.status_code == 204

    # Ověření neexistence
    get_res = client.get(f"/api/categories/{cat_id}")
    assert get_res.status_code == 404


def test_product_multiple_categories_mn_relationship(client):
    """Ověření M:N vazby: produkt je zařazen do více kategorií současně (dle zadání Dřevěnky)."""
    # 1. Založíme dvě testovací kategorie: "Pro batolata" a "Dárky do 500 Kč"
    cat1_name = f"Batolata-{uuid.uuid4().hex[:5]}"
    cat2_name = f"Dárky500-{uuid.uuid4().hex[:5]}"
    c1 = client.post("/api/categories", json={"name": cat1_name}).json()
    c2 = client.post("/api/categories", json={"name": cat2_name}).json()

    # 2. Vytvoříme hračku (káču) patřící do obou kategorií naráz
    product_code = f"MN-{uuid.uuid4().hex[:6].upper()}"
    product_payload = {
        "code": product_code,
        "name": "Dřevěná káča pro batolata",
        "purchase_price": "40.00",
        "selling_price": "110.00",
        "min_stock_level": 5,
        "category_ids": [c1["id"], c2["id"]],
    }
    prod_res = client.post("/api/products", json=product_payload)
    assert prod_res.status_code == 201
    prod_data = prod_res.json()
    prod_id = prod_data["id"]

    # Ověření, že produkt má v odpovědi obě kategorie
    assigned_cat_ids = [cat["id"] for cat in prod_data["categories"]]
    assert c1["id"] in assigned_cat_ids
    assert c2["id"] in assigned_cat_ids
    assert len(prod_data["categories"]) == 2

    # 3. Test filtrování produktů podle category_id přes REST API
    filter1_res = client.get(f"/api/products?category_id={c1['id']}")
    assert filter1_res.status_code == 200
    p_ids_1 = [p["id"] for p in filter1_res.json()]
    assert prod_id in p_ids_1

    filter2_res = client.get(f"/api/products?category_id={c2['id']}")
    assert filter2_res.status_code == 200
    p_ids_2 = [p["id"] for p in filter2_res.json()]
    assert prod_id in p_ids_2

    # Založíme třetí kategorii a ověříme, že v ní tento produkt není
    c3 = client.post("/api/categories", json={"name": f"Jina-{uuid.uuid4().hex[:5]}"}).json()
    filter3_res = client.get(f"/api/products?category_id={c3['id']}")
    assert filter3_res.status_code == 200
    p_ids_3 = [p["id"] for p in filter3_res.json()]
    assert prod_id not in p_ids_3


def test_web_ui_category_assignment_and_filtering(client):
    """Ověření webového rozhraní: zobrazení odznaků kategorií a filtrování v HTML šabloně."""
    # 1. Založení kategorie
    cat_name = f"WebKat-{uuid.uuid4().hex[:5]}"
    cat_res = client.post("/api/categories", json={"name": cat_name})
    cat_id = cat_res.json()["id"]

    # 2. Formulář nového produktu přes web UI
    form_data = {
        "code": f"WEB-{uuid.uuid4().hex[:6].upper()}",
        "name": "Webová testovací hračka",
        "description": "Testovací hračka s kategorií",
        "purchase_price": "75.00",
        "selling_price": "180.00",
        "min_stock_level": "4",
        "category_ids": [cat_id],
    }
    create_post_res = client.post("/products/new", data=form_data, follow_redirects=True)
    assert create_post_res.status_code == 200
    assert cat_name in create_post_res.text
    assert "Webová testovací hračka" in create_post_res.text

    # 3. Filtrování v katalogu podle category_id
    filter_view_res = client.get(f"/products?category_id={cat_id}")
    assert filter_view_res.status_code == 200
    assert "Webová testovací hračka" in filter_view_res.text
    assert "Zrušit filtry" in filter_view_res.text


def test_update_product_categories(client):
    """Ověření změny přiřazených kategorií produktu."""
    # 1. Založíme produkt se 2 kategoriemi
    c1 = client.post("/api/categories", json={"name": f"K1-{uuid.uuid4().hex[:5]}"}).json()
    c2 = client.post("/api/categories", json={"name": f"K2-{uuid.uuid4().hex[:5]}"}).json()
    c3 = client.post("/api/categories", json={"name": f"K3-{uuid.uuid4().hex[:5]}"}).json()

    code = f"UPD-{uuid.uuid4().hex[:6].upper()}"
    p = client.post("/api/products", json={
        "code": code,
        "name": "Produkt pro změnu kategorií",
        "purchase_price": "50.00",
        "selling_price": "120.00",
        "category_ids": [c1["id"], c2["id"]],
    }).json()

    assert len(p["categories"]) == 2

    # 2. Aktualizujeme kategorie na c2 a c3 (odebereme c1, přidáme c3)
    update_res = client.put(f"/api/products/{p['id']}", json={
        "category_ids": [c2["id"], c3["id"]],
    })
    assert update_res.status_code == 200
    upd_p = update_res.json()
    upd_cat_ids = [c["id"] for c in upd_p["categories"]]
    assert len(upd_cat_ids) == 2
    assert c1["id"] not in upd_cat_ids
    assert c2["id"] in upd_cat_ids
    assert c3["id"] in upd_cat_ids

