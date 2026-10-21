from decimal import Decimal
from app.core.database import SessionLocal
from app.infrastructure.db.models import Product, Category, Warehouse, WarehouseStock

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
        print(
            f"[SEED] Úspěšně vloženo {inserted_count} hraček, "
            f"aktualizováno {updated_count} hraček, zkontrolováno {stocks_seeded} zásob."
        )
    except Exception as exc:
        db.rollback()
        print(f"[SEED ERROR] Chyba při seedování: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
