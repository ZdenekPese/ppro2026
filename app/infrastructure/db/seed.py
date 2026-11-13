from decimal import Decimal
from datetime import datetime
from typing import Dict, List, TypedDict
from app.core.config import settings
from app.core.database import SessionLocal
from app.domain.services.auth_service import hash_password
from app.infrastructure.db.models import (
    Product,
    Category,
    Warehouse,
    WarehouseStock,
    StockMovement,
    Customer,
    Order,
    OrderItem,
    User,
    product_categories,
)


class StockQuant(TypedDict):
    physical: int
    reserved: int


class SampleProductDict(TypedDict):
    code: str
    name: str
    description: str
    purchase_price: Decimal
    selling_price: Decimal
    min_stock_level: int
    categories: List[str]
    stocks: Dict[str, StockQuant]


class SampleCategoryDict(TypedDict):
    name: str
    description: str


class SampleWarehouseDict(TypedDict):
    code: str
    name: str
    location: str
    is_primary: bool


SAMPLE_CATEGORIES: List[SampleCategoryDict] = [
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

SAMPLE_WAREHOUSES: List[SampleWarehouseDict] = [
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
    {
        "code": "WH-DILNA",
        "name": "Truhlářská dílna a mezisklad výroby",
        "location": "V Domkách 88, 500 09 Hradec Králové",
        "is_primary": False,
    },
]

# Přesně 25 pečlivě vybraných, reálných a tradičních dřevěných hraček Dřevěnky s.r.o.
SAMPLE_PRODUCTS: List[SampleProductDict] = [
    # 1. Káči a tahací hračky
    {
        "code": "KAC-001",
        "name": "Dřevěná káča buková",
        "description": "Tradiční ručně soustružená buková káča s precizním vyvážením a hladkou voskovou úpravou.",
        "purchase_price": Decimal("45.00"),
        "selling_price": Decimal("120.00"),
        "min_stock_level": 10,
        "categories": ["Pro batolata", "Dárky do 500 Kč", "Tradiční hračky"],
        "stocks": {
            "WH-HK": {"physical": 4, "reserved": 1},      # 3 volné
            "WH-TREB": {"physical": 12, "reserved": 0},  # 12 volných (převoz z garáže)
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
            "WH-TREB": {"physical": 2, "reserved": 0},    # 2 volné => celkem 6 < 8 (výroba)
        },
    },
    # 2. Vláčky a lokomotivy
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
            "WH-TREB": {"physical": 1, "reserved": 0},    # 1 volný => celkem 3 < 5
        },
    },
    {
        "code": "VLK-002",
        "name": "Parní lokomotiva Masiv",
        "description": "Detailně vypracovaná velká dřevěná lokomotiva z bukového dřeva s točícími se koly.",
        "purchase_price": Decimal("240.00"),
        "selling_price": Decimal("590.00"),
        "min_stock_level": 4,
        "categories": ["Dopravní prostředky", "Tradiční hračky"],
        "stocks": {
            "WH-HK": {"physical": 3, "reserved": 0},
            "WH-TREB": {"physical": 3, "reserved": 0},
        },
    },
    # 3. Koníci
    {
        "code": "KON-001",
        "name": "Houpací koník Masiv",
        "description": "Robustní ručně vyráběný houpací kůň ze smrkového a bukového masivu s bavlněnou hřívou.",
        "purchase_price": Decimal("650.00"),
        "selling_price": Decimal("1490.00"),
        "min_stock_level": 3,
        "categories": ["Pro batolata", "Tradiční hračky"],
        "stocks": {
            "WH-HK": {"physical": 4, "reserved": 0},
            "WH-TREB": {"physical": 0, "reserved": 0},
        },
    },
    {
        "code": "KON-002",
        "name": "Malý koník na kolečkách",
        "description": "Tradiční jezdící koník se zaoblenými tvary ideální pro první krůčky batolat.",
        "purchase_price": Decimal("110.00"),
        "selling_price": Decimal("280.00"),
        "min_stock_level": 6,
        "categories": ["Pro batolata", "Dárky do 500 Kč", "Tradiční hračky"],
        "stocks": {
            "WH-HK": {"physical": 6, "reserved": 0},
            "WH-TREB": {"physical": 4, "reserved": 0},
        },
    },
    # 4. Kostky a stavebnice
    {
        "code": "KOS-001",
        "name": "Sada dřevěných kostek (50 ks)",
        "description": "Stavební kostky z tvrdého dřeva v plátěném pytlíku. Různé tvary pro rozvoj jemné motoriky.",
        "purchase_price": Decimal("130.00"),
        "selling_price": Decimal("320.00"),
        "min_stock_level": 12,
        "categories": ["Stavebnice a hlavolamy", "Dárky do 500 Kč", "Pro batolata"],
        "stocks": {
            "WH-HK": {"physical": 8, "reserved": 0},
            "WH-TREB": {"physical": 10, "reserved": 0},
        },
    },
    {
        "code": "KOS-002",
        "name": "Velká stavitelská sada (100 ks)",
        "description": "Komplexní sada přírodních a barevných dřevěných dílů pro stavbu hradů a domečků.",
        "purchase_price": Decimal("260.00"),
        "selling_price": Decimal("650.00"),
        "min_stock_level": 5,
        "categories": ["Stavebnice a hlavolamy"],
        "stocks": {
            "WH-HK": {"physical": 3, "reserved": 0},
            "WH-TREB": {"physical": 4, "reserved": 0},
        },
    },
    # 5. Autíčka a vozidla
    {
        "code": "AUT-001",
        "name": "Dřevěné autíčko Retro Brouk",
        "description": "Stylové dřevěné autíčko se zaoblenou karoserií a tichými dřevěnými koly.",
        "purchase_price": Decimal("85.00"),
        "selling_price": Decimal("220.00"),
        "min_stock_level": 8,
        "categories": ["Dopravní prostředky", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 7, "reserved": 0},
            "WH-TREB": {"physical": 5, "reserved": 0},
        },
    },
    {
        "code": "AUT-002",
        "name": "Nákladní automobil s korbou",
        "description": "Masivní dřevěný náklaďák se sklápěcí korbou pro převoz kostek a drobností.",
        "purchase_price": Decimal("160.00"),
        "selling_price": Decimal("390.00"),
        "min_stock_level": 6,
        "categories": ["Dopravní prostředky", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 4, "reserved": 0},
            "WH-TREB": {"physical": 6, "reserved": 0},
        },
    },
    {
        "code": "AUT-003",
        "name": "Hasičský vůz s žebříkem",
        "description": "Červený dřevěný hasičský vůz s otočným a výsuvným žebříkem.",
        "purchase_price": Decimal("210.00"),
        "selling_price": Decimal("520.00"),
        "min_stock_level": 4,
        "categories": ["Dopravní prostředky"],
        "stocks": {
            "WH-HK": {"physical": 2, "reserved": 0},
            "WH-TREB": {"physical": 3, "reserved": 0},
        },
    },
    {
        "code": "AUT-004",
        "name": "Policejní hlídkové autíčko",
        "description": "Kompaktní dřevěné auto s majáčkem z přírodního lakovaného jasanu.",
        "purchase_price": Decimal("90.00"),
        "selling_price": Decimal("230.00"),
        "min_stock_level": 7,
        "categories": ["Dopravní prostředky", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 5, "reserved": 0},
            "WH-TREB": {"physical": 5, "reserved": 0},
        },
    },
    # 6. Hlavolamy a logické hračky
    {
        "code": "HLV-001",
        "name": "Dřevěný Ježek v kleci",
        "description": "Legendární český hlavolam z bukového dřeva s vytahovacím ježkem s ostny.",
        "purchase_price": Decimal("120.00"),
        "selling_price": Decimal("290.00"),
        "min_stock_level": 10,
        "categories": ["Stavebnice a hlavolamy", "Dárky do 500 Kč", "Tradiční hračky"],
        "stocks": {
            "WH-HK": {"physical": 8, "reserved": 0},
            "WH-TREB": {"physical": 8, "reserved": 0},
        },
    },
    {
        "code": "HLV-002",
        "name": "Skládací věž s kroužky",
        "description": "Barevná dřevěná pyramidová věž s navlékacími kroužky různých průměrů.",
        "purchase_price": Decimal("95.00"),
        "selling_price": Decimal("240.00"),
        "min_stock_level": 8,
        "categories": ["Pro batolata", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 6, "reserved": 0},
            "WH-TREB": {"physical": 6, "reserved": 0},
        },
    },
    {
        "code": "HLV-003",
        "name": "Provlékací sýr s myškou",
        "description": "Dřevěný žlutý sýr s otvory a dřevěnou myškou na šňůrce pro trénink zručnosti.",
        "purchase_price": Decimal("75.00"),
        "selling_price": Decimal("190.00"),
        "min_stock_level": 8,
        "categories": ["Pro batolata", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 5, "reserved": 0},
            "WH-TREB": {"physical": 7, "reserved": 0},
        },
    },
    # 7. Stolní hry a puzzle
    {
        "code": "DOM-001",
        "name": "Obrázkové dřevěné domino",
        "description": "Klasické domino z bukových destiček s vypalovanými motivy lesních zvířátek.",
        "purchase_price": Decimal("110.00"),
        "selling_price": Decimal("260.00"),
        "min_stock_level": 6,
        "categories": ["Stavebnice a hlavolamy", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 4, "reserved": 0},
            "WH-TREB": {"physical": 4, "reserved": 0},
        },
    },
    {
        "code": "PUZ-001",
        "name": "Vkládací puzzle Farma",
        "description": "Dřevěná vkládačka s úchyty pro snadné uchopení malou dětskou ručičkou.",
        "purchase_price": Decimal("105.00"),
        "selling_price": Decimal("250.00"),
        "min_stock_level": 7,
        "categories": ["Pro batolata", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 5, "reserved": 0},
            "WH-TREB": {"physical": 5, "reserved": 0},
        },
    },
    {
        "code": "PUZ-002",
        "name": "Dřevěný tangram v krabičce",
        "description": "Staročínský geometrický hlavolam z mořeného dřeva v praktické dřevěné kazetě.",
        "purchase_price": Decimal("80.00"),
        "selling_price": Decimal("195.00"),
        "min_stock_level": 6,
        "categories": ["Stavebnice a hlavolamy", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 6, "reserved": 0},
            "WH-TREB": {"physical": 4, "reserved": 0},
        },
    },
    # 8. Letadla a lodě
    {
        "code": "LET-001",
        "name": "Dřevěný dvouplošník",
        "description": "Klasické letadélko s točící se vrtulí a koly pro malé i velké piloty.",
        "purchase_price": Decimal("140.00"),
        "selling_price": Decimal("340.00"),
        "min_stock_level": 5,
        "categories": ["Dopravní prostředky", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 3, "reserved": 0},
            "WH-TREB": {"physical": 4, "reserved": 0},
        },
    },
    {
        "code": "LOD-001",
        "name": "Dřevěná plachetnice",
        "description": "Plachetnice s látkovými plachtami z bavlněného plátna a hladkým trupem.",
        "purchase_price": Decimal("125.00"),
        "selling_price": Decimal("290.00"),
        "min_stock_level": 5,
        "categories": ["Dopravní prostředky", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 4, "reserved": 0},
            "WH-TREB": {"physical": 3, "reserved": 0},
        },
    },
    # 9. Mechanické a tradiční hračky
    {
        "code": "MECH-001",
        "name": "Klapající datel na tyči",
        "description": "Klasická gravitační hračka. Datel kmitá a sjíždí po kovové tyčce dolů za klapavého zvuku.",
        "purchase_price": Decimal("70.00"),
        "selling_price": Decimal("175.00"),
        "min_stock_level": 8,
        "categories": ["Tradiční hračky", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 6, "reserved": 0},
            "WH-TREB": {"physical": 6, "reserved": 0},
        },
    },
    {
        "code": "MECH-002",
        "name": "Zobající slepičky na podložce",
        "description": "Dřevěná deska se slepičkami, které kmitáním závaží na šňůrkách zobají zrní.",
        "purchase_price": Decimal("90.00"),
        "selling_price": Decimal("225.00"),
        "min_stock_level": 7,
        "categories": ["Tradiční hračky", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 5, "reserved": 0},
            "WH-TREB": {"physical": 5, "reserved": 0},
        },
    },
    # 10. Hudební hračky a loutky
    {
        "code": "HUD-001",
        "name": "Dřevěný dětský xylofon",
        "description": "Laděný dřevěný xylofon s osmi tóny z javorového dřeva a dvěma paličkami.",
        "purchase_price": Decimal("150.00"),
        "selling_price": Decimal("380.00"),
        "min_stock_level": 6,
        "categories": ["Pro batolata", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 4, "reserved": 0},
            "WH-TREB": {"physical": 5, "reserved": 0},
        },
    },
    {
        "code": "HUD-002",
        "name": "Dřevěné rumba koule (pár)",
        "description": "Přírodní chrastítka pro batolata s jemným příjemným zvukem dřevěných kuliček.",
        "purchase_price": Decimal("60.00"),
        "selling_price": Decimal("150.00"),
        "min_stock_level": 10,
        "categories": ["Pro batolata", "Dárky do 500 Kč"],
        "stocks": {
            "WH-HK": {"physical": 7, "reserved": 0},
            "WH-TREB": {"physical": 8, "reserved": 0},
        },
    },
    {
        "code": "LOU-001",
        "name": "Dřevěné loutkové divadélko",
        "description": "Stolní divadélko s malovanou oponou, kulisami lesa a loutkami Kašpárka a krále.",
        "purchase_price": Decimal("480.00"),
        "selling_price": Decimal("1190.00"),
        "min_stock_level": 3,
        "categories": ["Tradiční hračky"],
        "stocks": {
            "WH-HK": {"physical": 2, "reserved": 0},
            "WH-TREB": {"physical": 2, "reserved": 0},
        },
    },
]


def seed_database() -> None:
    """Naplnění databáze vzorovými sklady, kategoriemi a přesně 25 hračkami Dřevěnky s.r.o."""
    db = SessionLocal()
    try:
        # 1. Odstranění zkušebních skladů mimo povolené (udržení max 5 skladů celkem dle zadání B)
        valid_wh_codes = set(w["code"] for w in SAMPLE_WAREHOUSES)
        extra_warehouses = db.query(Warehouse).filter(~Warehouse.code.in_(valid_wh_codes)).all()
        if extra_warehouses:
            extra_wh_ids = [w.id for w in extra_warehouses]
            # Smazat zásoby a testovací objednávky na tyto zkušební sklady
            db.query(OrderItem).filter(OrderItem.order_id.in_(
                db.query(Order.id).filter(Order.warehouse_id.in_(extra_wh_ids))
            )).delete(synchronize_session=False)
            db.query(Order).filter(Order.warehouse_id.in_(extra_wh_ids)).delete(synchronize_session=False)
            db.query(WarehouseStock).filter(WarehouseStock.warehouse_id.in_(extra_wh_ids)).delete(synchronize_session=False)
            db.commit()
            for ew in extra_warehouses:
                db.delete(ew)
            db.commit()
            print(f"[SEED] Úspěšně odstraněno {len(extra_warehouses)} zkušebních skladů.")

        # Seed skladů (Hradec Králové, Třebechovice, dílna - max 5)
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
            else:
                wh.name = wh_data["name"]
                wh.location = wh_data["location"]
                wh.is_primary = wh_data["is_primary"]
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

        # 3. Odstranění nadbytečných / testovacích produktů mimo 25 oficiálních
        valid_codes = set(item["code"] for item in SAMPLE_PRODUCTS)
        extra_products = db.query(Product).filter(~Product.code.in_(valid_codes)).all()
        if extra_products:
            extra_ids = [p.id for p in extra_products]
            # Smazat položky objednávek, které mají ForeignKey RESTRICT
            db.query(OrderItem).filter(OrderItem.product_id.in_(extra_ids)).delete(synchronize_session=False)
            db.commit()
            for p in extra_products:
                db.delete(p)
            db.commit()
            print(f"[SEED] Úspěšně odstraněno {len(extra_products)} nadbytečných/testovacích produktů.")

        # Vyčištění případných prázdných objednávek po smazání testovacích položek
        empty_orders = db.query(Order).filter(~Order.items.any()).all()
        for eo in empty_orders:
            db.delete(eo)
        db.commit()

        # 4. Seed 25 oficiálních produktů a přiřazení kategorií (M:N)
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
                product.name = item["name"]
                product.description = item["description"]
                product.purchase_price = item["purchase_price"]
                product.selling_price = item["selling_price"]
                product.min_stock_level = item["min_stock_level"]
                product.is_active = True
                product.categories = cat_objs
                updated_count += 1
            products_by_code[product.code] = product

        # 5. Seed skladových zásob (WarehouseStock) pro 25 produktů
        stocks_seeded = 0
        for item in SAMPLE_PRODUCTS:
            product = products_by_code[item["code"]]
            for wh_code, quant_data in item["stocks"].items():
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
                    stock.physical_quantity = quant_data["physical"]
                    stock.reserved_quantity = quant_data["reserved"]

        db.commit()

        # 6. Seed ukázkových skladových pohybů pro auditní deník (Fáze 5)
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
            f"aktualizováno {updated_count} hraček, zkontrolováno {stocks_seeded} zásob. "
            f"Celkový katalog: přesně 25 dřevěných hraček Dřevěnka s.r.o."
        )

        # 7. Seed zákazníků a objednávek (Fáze 6)
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

        # 8. Seed uživatelů pro přihlašovací obrazovku a role (Jednatel vs. Skladník)
        ensure_demo_users(db)

    except Exception as exc:
        db.rollback()
        print(f"[SEED ERROR] Chyba při seedování: {exc}")
    finally:
        db.close()


def ensure_demo_users(db) -> None:
    """Idempotentně založí výchozí demo uživatele dle rolí ze zadání (Jednatel a Skladník)."""
    demo_users = [
        {
            "username": "dolezal",
            "full_name": "Petr Doležal",
            "email": "dolezal@drevenka-hracky.cz",
            "role": "manager",
            "password": settings.DEMO_MANAGER_PASSWORD,
        },
        {
            "username": "skladnik",
            "full_name": "Jan Novák",
            "email": "novak@drevenka-hracky.cz",
            "role": "warehouse",
            "password": settings.DEMO_WAREHOUSE_PASSWORD,
        },
    ]
    created_any = False
    for u_data in demo_users:
        existing = db.query(User).filter(User.username == u_data["username"]).first()
        if not existing:
            user = User(
                username=u_data["username"],
                full_name=u_data["full_name"],
                email=u_data["email"],
                role=u_data["role"],
                password_hash=hash_password(u_data["password"]),
                is_active=True,
            )
            db.add(user)
            created_any = True
    if created_any:
        db.commit()
        print("[SEED] Úspěšně založeny demo uživatelské účty (dolezal, skladnik).")


if __name__ == "__main__":
    seed_database()
