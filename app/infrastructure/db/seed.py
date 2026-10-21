from decimal import Decimal
from app.core.database import SessionLocal
from app.infrastructure.db.models import Product, Category

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

SAMPLE_PRODUCTS = [
    {
        "code": "KAC-001",
        "name": "Dřevěná káča buková",
        "description": "Tradiční ručně soustružená buková káča s precizním vyvážením a hladkou povrchovou úpravou voskem.",
        "purchase_price": Decimal("45.00"),
        "selling_price": Decimal("120.00"),
        "min_stock_level": 10,
        "categories": ["Pro batolata", "Dárky do 500 Kč", "Tradiční hračky"],
    },
    {
        "code": "VLK-001",
        "name": "Dřevěný vláček se zvířátky",
        "description": "Barevný vláček s lokomotivou a třemi odpojitelnými vagónky vezoucími dřevěné figurky zvířátek.",
        "purchase_price": Decimal("180.00"),
        "selling_price": Decimal("450.00"),
        "min_stock_level": 5,
        "categories": ["Pro batolata", "Dopravní prostředky", "Dárky do 500 Kč"],
    },
    {
        "code": "KAC-002",
        "name": "Tahací kačer na provázku",
        "description": "Klasická tahací hračka pro batolata. Při jízdě kačer klape zobáčkem a hýbe křídly.",
        "purchase_price": Decimal("95.00"),
        "selling_price": Decimal("250.00"),
        "min_stock_level": 8,
        "categories": ["Pro batolata", "Dárky do 500 Kč", "Tradiční hračky"],
    },
    {
        "code": "KON-001",
        "name": "Houpací koník Masiv",
        "description": "Robustní ručně vyráběný houpací kůň ze smrkového a bukového masivu s bavlněnou hřívou.",
        "purchase_price": Decimal("650.00"),
        "selling_price": Decimal("1490.00"),
        "min_stock_level": 3,
        "categories": ["Pro batolata", "Tradiční hračky"],
    },
    {
        "code": "KOS-001",
        "name": "Sada dřevěných kostek (50 ks)",
        "description": "Stavební kostky z tvrdého dřeva v plátěném pytlíku. Různé tvary pro rozvoj jemné motoriky.",
        "purchase_price": Decimal("130.00"),
        "selling_price": Decimal("320.00"),
        "min_stock_level": 12,
        "categories": ["Stavebnice a hlavolamy", "Dárky do 500 Kč", "Pro batolata"],
    },
]


def seed_database() -> None:
    """Naplnění databáze vzorovými kategoriemi a produkty pro Dřevěnka s.r.o."""
    db = SessionLocal()
    try:
        # 1. Seed kategorií
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

        # 2. Seed produktů a přiřazení kategorií (M:N)
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
                inserted_count += 1
            else:
                # Pokud již produkt existuje, přiřadíme mu kategorie, pokud je dosud nemá
                if not product.categories:
                    product.categories = cat_objs
                    updated_count += 1

        db.commit()
        print(f"[SEED] Úspěšně vloženo {inserted_count} nových hraček, aktualizováno {updated_count} hraček.")
    except Exception as exc:
        db.rollback()
        print(f"[SEED ERROR] Chyba při seedování: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
