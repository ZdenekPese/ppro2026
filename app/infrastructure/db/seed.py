from decimal import Decimal
from datetime import datetime
from app.core.database import SessionLocal
from app.infrastructure.db.models import (
    Product,
    Category,
    Warehouse,
    WarehouseStock,
    StockMovement,
    Customer,
    Order,
    OrderItem,
)

SAMPLE_CATEGORIES = [
    {
        "name": "Pro batolata",
        "description": "Bezpečné hračky pro nejmenší děti se zaoblenými hranami a netoxickými povrchy.",
    },
    {
        "name": "Dárky do 500 Kč",
        "description": "Cenově dostupné a oblíbené drobnosti a hračky vhodné jako dárek.",
    },
    {
        "name": "Dopravní prostředky",
        "description": "Vláčky, autíčka a další vozítka z masivního dřeva s funkčními kolečky.",
    },
    {
        "name": "Stavebnice a hlavolamy",
        "description": "Dřevěné kostky, skládačky a hlavolamy pro rozvoj logiky a prostorové představivosti.",
    },
    {
        "name": "Tradiční hračky",
        "description": "Klasické léty prověřené české hračky naší truhlářské dílny.",
    },
]

SAMPLE_WAREHOUSES = [
    {
        "code": "WH-HK",
        "name": "Centrální sklad Hradec Králové",
        "location": "Bratří Čapků 450, 500 02 Hradec Králové",
        "is_primary": True,
    },
    {
        "code": "WH-TREB",
        "name": "Skladová garáž Třebechovice pod Orebem",
        "location": "Palackého 12, 503 46 Třebechovice pod Orebem",
        "is_primary": False,
    },
]

SAMPLE_PRODUCTS = [
    {
        "code": "KAC-001",
        "name": "Dřevěná káča buková",
        "description": "Tradiční ručně soustružená buková káča s precizním vyvážením a hladkou povrchovou úpravou voskem.",
        "purchase_price": Decimal("45.00"),
        "selling_price": Decimal("120.00"),
        "min_stock_level": 10,
        "categories": ["Pro batolata", "Dárky do 500 Kč", "Tradiční hračky"],
        "stocks": {
            "WH-HK": {"physical": 4, "reserved": 1},      # 3 volné
            "WH-TREB": {"physical": 12, "reserved": 0},  # 12 volných => celkem 15 >= 10 (OK)
        },
    },
    {
        "code": "VLK-001",
        "name": "Dřevěný vláček se zvířátky",
        "description": "Barevný vláček s lokomotivou a třemi odpojitelnými vagónky vezoucími dřevěné figurky zvířátek.",
        "purchase_price": Decimal("180.00"),
        "selling_price": Decimal("450.00"),
        "min_stock_level": 5,
        "categories": ["Pro batolata", "Dopravní prostředky", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 2, "reserved": 0},      # 2 volné
            "WH-TREB": {"physical": 1, "reserved": 0},    # 1 volný => celkem 3 < 5 (DANGER - HOŘÍ)
        },
    },
    {
        "code": "KAC-002",
        "name": "Tahací kačer na provázku",
        "description": "Klasická tahací hračka pro batolata. Při jízdě kačer klape zobáčkem a hýbe křídly.",
        "purchase_price": Decimal("95.00"),
        "selling_price": Decimal("250.00"),
        "min_stock_level": 8,
        "categories": ["Pro batolata", "Dárky do 500 Kč", "Tradiční hračky"],
        "stocks": {
            "WH-HK": {"physical": 5, "reserved": 1},      # 4 volné
            "WH-TREB": {"physical": 2, "reserved": 0},    # 2 volné => celkem 6 < 8 (DANGER - HOŘÍ)
        },
    },
    {
        "code": "KON-001",
        "name": "Houpací koník Masiv",
        "description": "Robustní ručně vyráběný houpací kůň ze smrkového a bukového masivu s bavlněnou hřívou.",
        "purchase_price": Decimal("650.00"),
        "selling_price": Decimal("1490.00"),
        "min_stock_level": 3,
        "categories": ["Pro batolata", "Tradiční hračky"],
        "stocks": {
            "WH-HK": {"physical": 4, "reserved": 0},      # 4 volné
            "WH-TREB": {"physical": 0, "reserved": 0},    # 0 volných => celkem 4 >= 3 (OK)
        },
    },
    {
        "code": "KOS-001",
        "name": "Sada dřevěných kostek (50 ks)",
        "description": "Stavební kostky z tvrdého dřeva v plátěném pytlíku. Různé tvary pro rozvoj jemné motoriky.",
        "purchase_price": Decimal("130.00"),
        "selling_price": Decimal("320.00"),
        "min_stock_level": 12,
        "categories": ["Stavebnice a hlavolamy", "Dárky do 500 Kč", "Pro batolata"],
        "stocks": {
            "WH-HK": {"physical": 8, "reserved": 0},      # 8 volných
            "WH-TREB": {"physical": 10, "reserved": 0},   # 10 volných => celkem 18 >= 12 (OK)
        },
    },
]


def seed_database() -> None:
    """Naplnění databáze vzorovými sklady, kategoriemi, produkty a zásobami."""
    db = SessionLocal()
    try:
        # 1. Seed skladů (Hradec Králové + Třebechovice)
        warehouses_by_code = {}
        for wh_data in SAMPLE_WAREHOUSES:
            wh = db.query(Warehouse).filter(Warehouse.code == wh_data["code"]).first()
            if not wh:
                wh = Warehouse(
                    code=wh_data["code"],
                    name=wh_data["name"],
                    location=wh_data["location"],
                    is_primary=wh_data["is_primary"],
                )
                db.add(wh)
                db.flush()
            warehouses_by_code[wh.code] = wh

        # 2. Seed kategorií
        categories_by_name = {}
        for cat_data in SAMPLE_CATEGORIES:
            cat = db.query(Category).filter(Category.name == cat_data["name"]).first()
            if not cat:
                cat = Category(
                    name=cat_data["name"],
                    description=cat_data["description"],
                )
                db.add(cat)
                db.flush()
            categories_by_name[cat.name] = cat

        # 3. Seed produktů a přiřazení kategorií (M:N)
        products_by_code = {}
        inserted_count = 0
        updated_count = 0
        for item in SAMPLE_PRODUCTS:
            product = db.query(Product).filter(Product.code == item["code"]).first()
            cat_objs = [categories_by_name[c_name] for c_name in item["categories"] if c_name in categories_by_name]

            if not product:
                product = Product(
                    code=item["code"],
                    name=item["name"],
                    description=item["description"],
                    purchase_price=item["purchase_price"],
                    selling_price=item["selling_price"],
                    min_stock_level=item["min_stock_level"],
                    is_active=True,
                    categories=cat_objs,
                )
                db.add(product)
                db.flush()
                inserted_count += 1
            else:
                if not product.categories:
                    product.categories = cat_objs
                    updated_count += 1
            products_by_code[product.code] = product

        # 4. Seed skladových zásob (WarehouseStock)
        stocks_seeded = 0
        for item in SAMPLE_PRODUCTS:
            product = products_by_code[item["code"]]
            for wh_code, quant_data in item.get("stocks", {}).items():
                warehouse = warehouses_by_code.get(wh_code)
                if not warehouse:
                    continue

                stock = (
                    db.query(WarehouseStock)
                    .filter(
                        WarehouseStock.warehouse_id == warehouse.id,
                        WarehouseStock.product_id == product.id,
                    )
                    .first()
                )
                if not stock:
                    stock = WarehouseStock(
                        warehouse_id=warehouse.id,
                        product_id=product.id,
                        physical_quantity=quant_data["physical"],
                        reserved_quantity=quant_data["reserved"],
                    )
                    db.add(stock)
                    stocks_seeded += 1
                else:
                    # Aktualizace stávajícího
                    stock.physical_quantity = quant_data["physical"]
                    stock.reserved_quantity = quant_data["reserved"]

        db.commit()

        # Seed ukázkových skladových pohybů pro auditní deník (Fáze 5)
        movements_count = db.query(StockMovement).count()
        if movements_count == 0:
            hk_wh = db.query(Warehouse).filter(Warehouse.code == "WH-HK").first()
            treb_wh = db.query(Warehouse).filter(Warehouse.code == "WH-TREB").first()
            kac_prod = db.query(Product).filter(Product.code == "KAC-001").first()
            vlk_prod = db.query(Product).filter(Product.code == "VLK-001").first()
            kos_prod = db.query(Product).filter(Product.code == "KOS-001").first()

            sample_movements = []
            if treb_wh and kac_prod:
                sample_movements.append(
                    StockMovement(
                        product_id=kac_prod.id,
                        source_warehouse_id=None,
                        destination_warehouse_id=treb_wh.id,
                        movement_type="receipt",
                        quantity=16,
                        note="Závoz nové série bukových káč z truhlárny pana Doležala",
                        reference_code="DL-2026/012",
                    )
                )
            if hk_wh and treb_wh and kac_prod:
                sample_movements.append(
                    StockMovement(
                        product_id=kac_prod.id,
                        source_warehouse_id=treb_wh.id,
                        destination_warehouse_id=hk_wh.id,
                        movement_type="transfer",
                        quantity=4,
                        note="Pravidelný závoz ze sezónní garáže Třebechovice do centrály v HK",
                        reference_code="PREV-2026/03",
                    )
                )
            if hk_wh and vlk_prod:
                sample_movements.append(
                    StockMovement(
                        product_id=vlk_prod.id,
                        source_warehouse_id=None,
                        destination_warehouse_id=hk_wh.id,
                        movement_type="receipt",
                        quantity=5,
                        note="Příjem 5 ks malovaných vláčků z dílny",
                        reference_code="DL-2026/014",
                    )
                )
                sample_movements.append(
                    StockMovement(
                        product_id=vlk_prod.id,
                        source_warehouse_id=hk_wh.id,
                        destination_warehouse_id=None,
                        movement_type="dispatch",
                        quantity=3,
                        note="Expedice zákazníkovi – objednávka z e-shopu",
                        reference_code="OBJ-2026/101",
                    )
                )
            if treb_wh and kos_prod:
                sample_movements.append(
                    StockMovement(
                        product_id=kos_prod.id,
                        source_warehouse_id=None,
                        destination_warehouse_id=treb_wh.id,
                        movement_type="inventory_adjustment",
                        quantity=2,
                        note="Inventurní přebytek (+2 ks): Nalezeny 2 zapadlé krabice za paletou v garáži",
                        reference_code="INVENTURA",
                    )
                )

            for sm in sample_movements:
                db.add(sm)
            db.commit()
            print(f"[SEED] Úspěšně vloženo {len(sample_movements)} ukázkových pohybů pro auditní deník.")

        print(
            f"[SEED] Úspěšně vloženo {inserted_count} hraček, "
            f"aktualizováno {updated_count} hraček, zkontrolováno {stocks_seeded} zásob."
        )

        # Seed zákazníků a objednávek (Fáze 6)
        if db.query(Customer).count() == 0:
            cust_marie = Customer(
                first_name="Marie",
                last_name="Svobodová",
                email="marie.svobodova@seznam.cz",
                phone="+420 603 112 233",
                address="Smetanovo nábřeží 124, 500 02 Hradec Králové",
                is_active=True,
            )
            cust_petr = Customer(
                first_name="Petr",
                last_name="Černý",
                email="petr.cerny@email.cz",
                phone="+420 774 445 566",
                address="Komenského 88, 530 02 Pardubice",
                is_active=True,
            )
            cust_jana = Customer(
                first_name="Jana",
                last_name="Dvořáková",
                email="jana.dvorakova@post.cz",
                phone="+420 721 998 877",
                address="Lipová 512, 503 46 Třebechovice pod Orebem",
                is_active=True,
            )
            db.add_all([cust_marie, cust_petr, cust_jana])
            db.commit()
            print("[SEED] Úspěšně vloženi 3 demo zákazníci.")

            hk_wh = db.query(Warehouse).filter(Warehouse.code == "WH-HK").first()
            kac_prod = db.query(Product).filter(Product.code == "KAC-001").first()
            vlk_prod = db.query(Product).filter(Product.code == "VLK-001").first()
            kon_prod = db.query(Product).filter(Product.code == "KON-001").first()

            if hk_wh and kac_prod and vlk_prod and kon_prod:
                # Objednávka 1: Expedovaná
                ord1 = Order(
                    order_number="OBJ-2026-0001",
                    customer_id=cust_marie.id,
                    warehouse_id=hk_wh.id,
                    status="DISPATCHED",
                    total_price=Decimal("240.00"),
                    note="Vánoční balení s mašlí",
                    dispatched_at=datetime.now(),
                    items=[
                        OrderItem(
                            product_id=kac_prod.id,
                            quantity=2,
                            unit_price=Decimal("120.00"),
                        )
                    ],
                )

                # Objednávka 2: Rezervovaná (k expedici)
                ord2 = Order(
                    order_number="OBJ-2026-0002",
                    customer_id=cust_petr.id,
                    warehouse_id=hk_wh.id,
                    status="RESERVED",
                    total_price=Decimal("450.00"),
                    note="Doručit na recepci firmy",
                    items=[
                        OrderItem(
                            product_id=vlk_prod.id,
                            quantity=1,
                            unit_price=Decimal("450.00"),
                        )
                    ],
                )

                # Objednávka 3: Rezervovaná (Houpací koník)
                ord3 = Order(
                    order_number="OBJ-2026-0003",
                    customer_id=cust_jana.id,
                    warehouse_id=hk_wh.id,
                    status="RESERVED",
                    total_price=Decimal("1490.00"),
                    note="Dárek pro vnuka k 2. narozeninám",
                    items=[
                        OrderItem(
                            product_id=kon_prod.id,
                            quantity=1,
                            unit_price=Decimal("1490.00"),
                        )
                    ],
                )

                db.add_all([ord1, ord2, ord3])
                db.commit()
                print("[SEED] Úspěšně vloženy 3 demo objednávky.")

    except Exception as exc:
        db.rollback()
        print(f"[SEED ERROR] Chyba při seedování: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
