from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.domain.exceptions import (
    DuplicateWarehouseCodeError,
    InsufficientStockError,
    NegativeStockError,
    ProductNotFoundError,
    WarehouseNotFoundError,
)
from app.domain.models.warehouse import (
    DashboardSummary,
    ProductStockDetail,
    WarehouseCreate,
    WarehouseInventorySummary,
    WarehouseResponse,
    WarehouseStockResponse,
    WarehouseStockUpdate,
    WarehouseUpdate,
)
from app.infrastructure.db.models import Product, Warehouse, WarehouseStock
from app.infrastructure.repositories.product_repository import ProductRepository
from app.infrastructure.repositories.warehouse_repository import WarehouseRepository
from app.infrastructure.repositories.warehouse_stock_repository import WarehouseStockRepository


class WarehouseService:
    """Aplikační služba pro správu skladů a skladových zásob (Fáze 4)."""

    def __init__(self, db: Session):
        self.db = db
        self.warehouse_repo = WarehouseRepository(db)
        self.stock_repo = WarehouseStockRepository(db)
        self.product_repo = ProductRepository(db)

    # ==================== Správa skladů ====================

    def list_warehouses(self) -> List[WarehouseResponse]:
        """Vrátí seznam všech skladů."""
        warehouses = self.warehouse_repo.list_all()
        return [WarehouseResponse.model_validate(w) for w in warehouses]

    def get_warehouse(self, warehouse_id: UUID) -> Warehouse:
        """Získá ORM instanci skladu nebo vyvolá WarehouseNotFoundError."""
        warehouse = self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse:
            raise WarehouseNotFoundError(str(warehouse_id))
        return warehouse

    def create_warehouse(self, data: WarehouseCreate) -> WarehouseResponse:
        """Založí nový sklad s kontrolou unikátnosti kódu."""
        existing = self.warehouse_repo.get_by_code(data.code)
        if existing:
            raise DuplicateWarehouseCodeError(data.code)

        warehouse = Warehouse(
            code=data.code,
            name=data.name,
            location=data.location,
            is_primary=data.is_primary,
        )
        saved = self.warehouse_repo.create(warehouse)
        return WarehouseResponse.model_validate(saved)

    def update_warehouse(self, warehouse_id: UUID, data: WarehouseUpdate) -> WarehouseResponse:
        """Upraví parametry existujícího skladu."""
        warehouse = self.get_warehouse(warehouse_id)

        if data.name is not None:
            warehouse.name = data.name
        if data.location is not None:
            warehouse.location = data.location
        if data.is_primary is not None:
            warehouse.is_primary = data.is_primary

        saved = self.warehouse_repo.update(warehouse)
        return WarehouseResponse.model_validate(saved)

    # ==================== Skladové zásoby ====================

    def get_stock(self, warehouse_id: UUID, product_id: UUID) -> WarehouseStock:
        """Získá záznam zásoby nebo inicializuje nulový záznam."""
        # Ověření existence skladu a produktu
        self.get_warehouse(warehouse_id)
        product = self.product_repo.get_by_id(product_id)
        if not product:
            raise ProductNotFoundError(str(product_id))

        return self.stock_repo.get_or_create(warehouse_id, product_id)

    def update_stock(
        self,
        warehouse_id: UUID,
        product_id: UUID,
        dto: WarehouseStockUpdate,
    ) -> WarehouseStockResponse:
        """Ruční úprava / dorovnání skladové zásoby s validací nezápornosti."""
        stock = self.get_stock(warehouse_id, product_id)

        new_phys = dto.physical_quantity if dto.physical_quantity is not None else stock.physical_quantity
        new_res = dto.reserved_quantity if dto.reserved_quantity is not None else stock.reserved_quantity

        if new_phys < 0:
            raise NegativeStockError("Fyzická zásoba nesmí být záporná.")
        if new_res < 0:
            raise NegativeStockError("Rezervovaná zásoba nesmí být záporná.")
        if new_res > new_phys:
            raise InsufficientStockError(available=new_phys, requested=new_res)

        stock.physical_quantity = new_phys
        stock.reserved_quantity = new_res
        saved = self.stock_repo.update(stock)
        return WarehouseStockResponse.model_validate(saved)

    def reserve_stock(
        self,
        warehouse_id: UUID,
        product_id: UUID,
        quantity: int,
    ) -> WarehouseStockResponse:
        """Rezervace disponibilních kusů při vytvoření objednávky."""
        if quantity <= 0:
            raise ValueError("Počet kusů k rezervaci musí být kladné číslo.")

        stock = self.get_stock(warehouse_id, product_id)
        available = stock.available_quantity
        if available < quantity:
            raise InsufficientStockError(available=available, requested=quantity)

        stock.reserved_quantity += quantity
        saved = self.stock_repo.update(stock)
        return WarehouseStockResponse.model_validate(saved)

    def release_reservation(
        self,
        warehouse_id: UUID,
        product_id: UUID,
        quantity: int,
    ) -> WarehouseStockResponse:
        """Uvolnění rezervace (např. při stornu objednávky)."""
        if quantity <= 0:
            raise ValueError("Počet kusů k uvolnění musí být kladné číslo.")

        stock = self.get_stock(warehouse_id, product_id)
        stock.reserved_quantity = max(0, stock.reserved_quantity - quantity)
        saved = self.stock_repo.update(stock)
        return WarehouseStockResponse.model_validate(saved)

    def dispatch_stock(
        self,
        warehouse_id: UUID,
        product_id: UUID,
        quantity: int,
    ) -> WarehouseStockResponse:
        """Fyzický odpis ze skladu při expedici objednávky."""
        if quantity <= 0:
            raise ValueError("Počet kusů k expedici musí být kladné číslo.")

        stock = self.get_stock(warehouse_id, product_id)
        if stock.physical_quantity < quantity:
            raise InsufficientStockError(available=stock.physical_quantity, requested=quantity)

        stock.physical_quantity -= quantity
        stock.reserved_quantity = max(0, stock.reserved_quantity - quantity)
        saved = self.stock_repo.update(stock)
        return WarehouseStockResponse.model_validate(saved)

    # ==================== Přehledy a Dashboard ====================

    def get_products_stock_overview(
        self,
        search: Optional[str] = None,
        category_id: Optional[UUID] = None,
        only_critical: bool = False,
    ) -> List[ProductStockDetail]:
        """Vrátí rozpad zásob pro všechny hračky s barevným statusem (včetně Garáže i Hradce)."""
        products = self.product_repo.list_all(search=search, category_id=category_id)
        warehouses = self.warehouse_repo.list_all()

        overview: List[ProductStockDetail] = []
        for p in products:
            stocks_dict: Dict[str, WarehouseStockResponse] = {}
            total_phys = 0
            total_res = 0

            # Namapujeme zásoby na existující sklady
            stocks_by_wh_id = {s.warehouse_id: s for s in p.stocks}
            for wh in warehouses:
                st = stocks_by_wh_id.get(wh.id)
                if st:
                    stocks_dict[wh.code] = WarehouseStockResponse.model_validate(st)
                    total_phys += st.physical_quantity
                    total_res += st.reserved_quantity
                else:
                    # Nulová zásoba
                    stocks_dict[wh.code] = WarehouseStockResponse(
                        id=UUID("00000000-0000-0000-0000-000000000000"),
                        warehouse_id=wh.id,
                        product_id=p.id,
                        physical_quantity=0,
                        reserved_quantity=0,
                        available_quantity=0,
                        created_at=p.created_at,
                        updated_at=p.updated_at,
                    )

            total_avail = total_phys - total_res
            is_below = total_avail < p.min_stock_level

            # Barevné vyhodnocení stavu:
            # - danger (červená): disponibilní zásoba klesla pod definované minimum
            # - warning (oranžová): zásoba je těsně nad minimem (do 1.5x limitu)
            # - ok (zelená / modrá): dostatečná bezpečná hladina
            if total_avail < p.min_stock_level:
                status = "danger"
            elif total_avail <= int(p.min_stock_level * 1.5):
                status = "warning"
            else:
                status = "ok"

            if only_critical and not is_below:
                continue

            overview.append(
                ProductStockDetail(
                    product_id=p.id,
                    product_code=p.code,
                    product_name=p.name,
                    min_stock_level=p.min_stock_level,
                    selling_price=p.selling_price,
                    purchase_price=p.purchase_price,
                    is_active=p.is_active,
                    stocks=stocks_dict,
                    total_physical=total_phys,
                    total_reserved=total_res,
                    total_available=total_avail,
                    status=status,
                    is_below_min=is_below,
                )
            )

        return overview

    def get_dashboard_summary(self) -> DashboardSummary:
        """Vypočte kompletní souhrnná data pro úvodní dashboard skladu."""
        warehouses = self.warehouse_repo.list_all()
        products = self.product_repo.list_all()
        all_stocks = self.stock_repo.list_all()

        # Namapování produktů pro rychlé dohledání nákupní ceny
        products_by_id = {p.id: p for p in products}

        total_physical = 0
        total_reserved = 0
        total_value = Decimal("0.00")

        # Souhrny per sklad
        wh_stats: Dict[UUID, Dict] = {
            w.id: {"items": 0, "value": Decimal("0.00")} for w in warehouses
        }

        for st in all_stocks:
            total_physical += st.physical_quantity
            total_reserved += st.reserved_quantity
            prod = products_by_id.get(st.product_id)
            if prod:
                item_val = Decimal(st.physical_quantity) * prod.purchase_price
                total_value += item_val
                if st.warehouse_id in wh_stats:
                    wh_stats[st.warehouse_id]["items"] += st.physical_quantity
                    wh_stats[st.warehouse_id]["value"] += item_val

        total_available = total_physical - total_reserved

        # Vyhodnocení položek pod minimem („co hoří“)
        all_details = self.get_products_stock_overview()
        critical_items = [item for item in all_details if item.is_below_min]

        wh_summaries: List[WarehouseInventorySummary] = []
        for w in warehouses:
            stats = wh_stats.get(w.id, {"items": 0, "value": Decimal("0.00")})
            wh_summaries.append(
                WarehouseInventorySummary(
                    warehouse_id=w.id,
                    warehouse_code=w.code,
                    warehouse_name=w.name,
                    is_primary=w.is_primary,
                    total_items_count=stats["items"],
                    total_value=stats["value"],
                )
            )

        return DashboardSummary(
            total_products_count=len(products),
            total_physical_count=total_physical,
            total_reserved_count=total_reserved,
            total_available_count=total_available,
            total_stock_value=total_value,
            critical_items_count=len(critical_items),
            warehouses=wh_summaries,
            critical_items=critical_items,
        )
