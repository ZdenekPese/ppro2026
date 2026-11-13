from uuid import uuid4

from app.core.config import settings
from app.domain.services.auth_service import hash_password, verify_password


def test_password_hashing_and_verification():
    """Heslo je zahashováno pomocí scrypt se solí a správně ověřeno."""
    secret = "SilneTestovaciHeslo123"
    hashed = hash_password(secret)
    assert hashed.startswith("scrypt$")
    assert verify_password(secret, hashed) is True
    assert verify_password("SpatneHeslo", hashed) is False
    assert verify_password(secret, "neplatny_format") is False


def test_unauthenticated_web_routes_redirect_to_login(anon_client):
    """Nepřihlášený uživatel je z webových stránek přesměrován na /login."""
    for path in ["/", "/products", "/movements", "/orders", "/customers", "/reports"]:
        resp = anon_client.get(path, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"].startswith("/login")


def test_login_page_renders_with_demo_roles_and_without_dots(anon_client):
    """Přihlašovací obrazovka se vykreslí s demo rolemi a bez kruhových teček."""
    resp = anon_client.get("/login")
    assert resp.status_code == 200
    body = resp.text
    assert "Dřevěnka s.r.o." in body
    assert "Petr Doležal" in body
    assert "Jan Novák" in body
    assert "status-dot" not in body
    assert "&bull;" not in body


def test_login_invalid_credentials_returns_401(anon_client):
    """Špatné heslo nebo neexistující uživatel vrátí 401 a srozumitelnou českou chybu."""
    resp = anon_client.post(
        "/login",
        data={"username": "dolezal", "password": "spatne-heslo", "next": "/"},
        follow_redirects=False,
    )
    assert resp.status_code == 401
    assert "Neplatné uživatelské jméno nebo heslo" in resp.text


def test_open_redirect_protection_on_login(anon_client):
    """Externí parametr next nesmí způsobit přesměrování mimo aplikaci."""
    resp = anon_client.post(
        "/login",
        data={
            "username": "dolezal",
            "password": settings.DEMO_MANAGER_PASSWORD,
            "next": "https://evil.example.com/phish",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"


def test_role_warehouse_permissions_and_restrictions(warehouse_client, client):
    """Skladník smí operovat se skladem, ale reporty a katalogový ceník má blokované (403)."""
    # Povolené operativní stránky
    for path in ["/", "/products", "/movements", "/orders", "/customers"]:
        resp = warehouse_client.get(path)
        assert resp.status_code == 200, f"Skladník by měl mít přístup na {path}"

    # Zakázané manažerské stránky
    forbidden_reports = warehouse_client.get("/reports")
    assert forbidden_reports.status_code == 403
    assert "Přístup omezen podle role" in forbidden_reports.text

    forbidden_new_product = warehouse_client.get("/products/new")
    assert forbidden_new_product.status_code == 403

    # Získání existujícího produktu přes manager API pro ověření blokace /edit
    products_resp = client.get("/api/products")
    assert products_resp.status_code == 200
    items = products_resp.json()
    assert len(items) > 0
    first_product_id = items[0]["id"]

    forbidden_edit = warehouse_client.get(f"/products/{first_product_id}/edit")
    assert forbidden_edit.status_code == 403

    # Jednatel (manager) má přístup ke všemu
    assert client.get("/reports").status_code == 200
    assert client.get("/products/new").status_code == 200
    assert client.get(f"/products/{first_product_id}/edit").status_code == 200


def test_logout_invalidates_session_cookie(anon_client):
    """Odhlášení zruší session v databázi a další požadavek vyžaduje nové přihlášení."""
    login_resp = anon_client.post(
        "/login",
        data={"username": "skladnik", "password": settings.DEMO_WAREHOUSE_PASSWORD, "next": "/"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 303
    assert anon_client.get("/").status_code == 200

    logout_resp = anon_client.post("/logout", follow_redirects=False)
    assert logout_resp.status_code == 303
    assert logout_resp.headers["location"] == "/login?logged_out=1"

    after_logout = anon_client.get("/", follow_redirects=False)
    assert after_logout.status_code == 303
    assert after_logout.headers["location"].startswith("/login")


def test_api_auth_flow(anon_client):
    """REST API /api/auth/login, /me a /logout pracují konzistentně se session cookie."""
    unauth_me = anon_client.get("/api/auth/me")
    assert unauth_me.status_code == 401

    login_resp = anon_client.post(
        "/api/auth/login",
        json={"username": "dolezal", "password": settings.DEMO_MANAGER_PASSWORD},
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert data["username"] == "dolezal"
    assert data["role"] == "manager"
    assert data["full_name"] == "Petr Doležal"

    me_resp = anon_client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "dolezal"

    logout_resp = anon_client.post("/api/auth/logout")
    assert logout_resp.status_code == 204

    me_after = anon_client.get("/api/auth/me")
    assert me_after.status_code == 401


def test_stock_movement_records_performed_by_authenticated_user(warehouse_client, client):
    """Webový příjem skladu uloží do auditní stopy jméno přihlášeného pracovníka."""
    products_resp = client.get("/api/products")
    product_id = products_resp.json()[0]["id"]
    warehouses_resp = client.get("/api/warehouses")
    hk_warehouse = next(w for w in warehouses_resp.json() if "Hradec" in w["name"])

    ref_code = f"AUTH-{uuid4().hex[:6].upper()}"
    receipt_resp = warehouse_client.post(
        "/movements/receipt",
        data={
            "product_id": product_id,
            "warehouse_id": hk_warehouse["id"],
            "quantity": "1",
            "reference_code": ref_code,
            "note": "Test auditní stopy přihlášeného skladníka",
        },
        follow_redirects=False,
    )
    assert receipt_resp.status_code == 303

    movements_resp = client.get(f"/api/movements?search={ref_code}")
    assert movements_resp.status_code == 200
    matched = [m for m in movements_resp.json() if m.get("reference_code") == ref_code]
    assert len(matched) == 1
    assert matched[0]["performed_by"] == "Jan Novák"

    # Kompenzační výdej, aby čistý stav skladu zůstal nezměněn
    client.post(
        "/api/movements/dispatch",
        json={
            "product_id": product_id,
            "warehouse_id": hk_warehouse["id"],
            "quantity": 1,
            "reference_code": f"{ref_code}-REV",
            "note": "Kompenzace testovacího příjmu",
        },
    )
