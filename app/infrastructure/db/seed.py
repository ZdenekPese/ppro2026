from decimal import Decimal
from app.core.database import SessionLocal
from app.infrastructure.db.models import Product

SAMPLE_PRODUCTS = [
    {
        "code": "KAC-001",
        "name": "Dřevěná káča buková",
        "description": "Tradiční ručně soustružená buková káča s precizním vyvážením a hladkou povrchovou úpravou voskem.",
        "purchase_price": Decimal("45.00"),
        "selling_price": Decimal("120.00"),
        "min_stock_level": 10,
    },
    {
        "code": "VLK-001",
        "name": "Dřevěný vláček se zvířátky",
        "description": "Barevný vláček s lokomotivou a třemi odpojitelnými vagónky vezoucími dřevěné figurky zvířátek.",
        "purchase_price": Decimal("180.00"),
        "selling_price": Decimal("450.00"),
        "min_stock_level": 5,
    },
    {
        "code": "KAC-002",
        "name": "Tahací kačer na provázku",
        "description": "Klasická tahací hračka pro batolata. Při jízdě kačer klape zobáčkem a hýbe křídly.",
        "purchase_price": Decimal("95.00"),
        "selling_price": Decimal("250.00"),
        "min_stock_level": 8,
    },
    {
        "code": "KON-001",
        "name": "Houpací koník Masiv",
        "description": "Robustní ručně vyráběný houpací kůň ze smrkového a bukového masivu s bavlněnou hřívou.",
        "purchase_price": Decimal("650.00"),
        "selling_price": Decimal("1490.00"),
        "min_stock_level": 3,
    },
    {
        "code": "KOS-001",
        "name": "Sada dřevěných kostek (50 ks)",
        "description": "Stavební kostky z tvrdého dřeva v plátěném pytlíku. Různé tvary pro rozvoj jemné motoriky.",
        "purchase_price": Decimal("130.00"),
        "selling_price": Decimal("320.00"),
        "min_stock_level": 12,
    },
]


def seed_products() -> None:
    """Naplnění databáze vzorovými dřevěnými hračkami Dřevěnka s.r.o."""
    db = SessionLocal()
    try:
        inserted_count = 0
        for item in SAMPLE_PRODUCTS:
            existing = db.query(Product).filter(Product.code == item["code"]).first()
            if not existing:
                product = Product(
                    code=item["code"],
                    name=item["name"],
                    description=item["description"],
                    purchase_price=item["purchase_price"],
                    selling_price=item["selling_price"],
                    min_stock_level=item["min_stock_level"],
                    is_active=True,
                )
                db.add(product)
                inserted_count += 1

        db.commit()
        print(f"[SEED] Úspěšně vloženo {inserted_count} nových hraček do databáze.")
    except Exception as exc:
        db.rollback()
        print(f"[SEED ERROR] Chyba při seedování: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_products()
