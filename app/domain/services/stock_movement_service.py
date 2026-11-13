from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.domain.exceptions import (
    InsufficientStockError,
    NegativeStockError,
    ProductNotFoundError,
    WarehouseNotFoundError,
)
from app.domain.models.stock_movement import (
    InventoryAdjustmentCreate,
    StockDispatchCreate,
    StockMovementResponse,
    StockMovementType,
    StockReceiptCreate,
    StockTransferCreate,
)
from app.infrastructure.db.models import Product, StockMovement, Warehouse
from app.infrastructure.repositories.product_repository import ProductRepository
from app.infrastructure.repositories.stock_movement_repository import StockMovementRepository
from app.infrastructure.repositories.warehouse_repository import WarehouseRepository
from app.infrastructure.repositories.warehouse_stock_repository import WarehouseStockRepository


class StockMovementService:
    """Aplikační služba pro evidenci pohybů a auditní stopu zásob (Fáze 5)."""

    def __init__(self, db: Session):
        self.db = db
        self.movement_repo = StockMovementRepository(db)
        self.stock_repo = WarehouseStockRepository(db)
        self.warehouse_repo = WarehouseRepository(db)
        self.product_repo = ProductRepository(db)

    def _format_movement_response(self, movement: StockMovement) -> StockMovementResponse:
        """Formátování ORM entity StockMovement na DTO response včetně názvů."""
        product = self.product_repo.get_by_id(movement.product_id)
        prod_code = product.code if product else "N/A"
        prod_name = product.name if product else "Neznámý produkt"

        src_wh = self.warehouse_repo.get_by_id(movement.source_warehouse_id) if movement.source_warehouse_id else None
        dst_wh = self.warehouse_repo.get_by_id(movement.destination_warehouse_id) if movement.destination_warehouse_id else None

        return StockMovementResponse(
            id=movement.id,
            product_id=movement.product_id,
            product_code=prod_code,
            product_name=prod_name,
            source_warehouse_id=movement.source_warehouse_id,
            source_warehouse_code=src_wh.code if src_wh else None,
            source_warehouse_name=src_wh.name if src_wh else None,
            destination_warehouse_id=movement.destination_warehouse_id,
            destination_warehouse_code=dst_wh.code if dst_wh else None,
            destination_warehouse_name=dst_wh.name if dst_wh else None,
            movement_type=movement.movement_type,
            quantity=movement.quantity,
            note=movement.note,
            reference_code=movement.reference_code,
            performed_by=movement.performed_by,
            created_at=movement.created_at,
        )

    def record_receipt(self, dto: StockReceiptCreate, performed_by: Optional[str] = None) -> StockMovementResponse:
        """Příjem zboží od dodavatele nebo z dílny do skladu."""
        warehouse = self.warehouse_repo.get_by_id(dto.warehouse_id)
        if not warehouse:
            raise WarehouseNotFoundError(str(dto.warehouse_id))

        product = self.product_repo.get_by_id(dto.product_id)
        if not product:
            raise ProductNotFoundError(str(dto.product_id))

        stock = self.stock_repo.get_or_create(dto.warehouse_id, dto.product_id)
        stock.physical_quantity += dto.quantity
        self.stock_repo.update(stock)

        movement = StockMovement(
            product_id=dto.product_id,
            source_warehouse_id=None,
            destination_warehouse_id=dto.warehouse_id,
            movement_type=StockMovementType.RECEIPT.value,
            quantity=dto.quantity,
            note=dto.note,
            reference_code=dto.reference_code,
            performed_by=performed_by,
        )
        saved = self.movement_repo.create(movement)
        return self._format_movement_response(saved)

    def record_dispatch(self, dto: StockDispatchCreate, performed_by: Optional[str] = None) -> StockMovementResponse:
        """Výdej zboží ze skladu (expedice zákazníkovi) se zákazem záporu."""
        warehouse = self.warehouse_repo.get_by_id(dto.warehouse_id)
        if not warehouse:
            raise WarehouseNotFoundError(str(dto.warehouse_id))

        product = self.product_repo.get_by_id(dto.product_id)
        if not product:
            raise ProductNotFoundError(str(dto.product_id))

        stock = self.stock_repo.get_or_create(dto.warehouse_id, dto.product_id)
        if stock.physical_quantity < dto.quantity:
            raise InsufficientStockError(available=stock.physical_quantity, requested=dto.quantity)

        stock.physical_quantity -= dto.quantity
        self.stock_repo.update(stock)

        movement = StockMovement(
            product_id=dto.product_id,
            source_warehouse_id=dto.warehouse_id,
            destination_warehouse_id=None,
            movement_type=StockMovementType.DISPATCH.value,
            quantity=dto.quantity,
            note=dto.note,
            reference_code=dto.reference_code,
            performed_by=performed_by,
        )
        saved = self.movement_repo.create(movement)
        return self._format_movement_response(saved)

    def record_transfer(self, dto: StockTransferCreate, performed_by: Optional[str] = None) -> StockMovementResponse:
        """Meziskladový převoz (např. ze sezónní garáže v Třebechovicích do Hradce)."""
        if dto.source_warehouse_id == dto.destination_warehouse_id:
            raise ValueError("Zdrojový a cílový sklad musí být různé.")

        src_wh = self.warehouse_repo.get_by_id(dto.source_warehouse_id)
        if not src_wh:
            raise WarehouseNotFoundError(str(dto.source_warehouse_id))

        dst_wh = self.warehouse_repo.get_by_id(dto.destination_warehouse_id)
        if not dst_wh:
            raise WarehouseNotFoundError(str(dto.destination_warehouse_id))

        product = self.product_repo.get_by_id(dto.product_id)
        if not product:
            raise ProductNotFoundError(str(dto.product_id))

        src_stock = self.stock_repo.get_or_create(dto.source_warehouse_id, dto.product_id)
        avail = src_stock.available_quantity
        if avail < dto.quantity:
            raise InsufficientStockError(available=avail, requested=dto.quantity)

        dst_stock = self.stock_repo.get_or_create(dto.destination_warehouse_id, dto.product_id)

        # Provedení přesunu v rámci jedné transakce
        src_stock.physical_quantity -= dto.quantity
        dst_stock.physical_quantity += dto.quantity
        self.stock_repo.update(src_stock)
        self.stock_repo.update(dst_stock)

        movement = StockMovement(
            product_id=dto.product_id,
            source_warehouse_id=dto.source_warehouse_id,
            destination_warehouse_id=dto.destination_warehouse_id,
            movement_type=StockMovementType.TRANSFER.value,
            quantity=dto.quantity,
            note=dto.note or f"Meziskladový převoz {src_wh.code} -> {dst_wh.code}",
            reference_code=dto.reference_code,
            performed_by=performed_by,
        )
        saved = self.movement_repo.create(movement)
        return self._format_movement_response(saved)

    def record_inventory_adjustment(
        self, dto: InventoryAdjustmentCreate, performed_by: Optional[str] = None
    ) -> StockMovementResponse:
        """Inventurní vyrovnání skladu (vyřešení rozporů v garáži či HK se 100% auditní stopou)."""
        warehouse = self.warehouse_repo.get_by_id(dto.warehouse_id)
        if not warehouse:
            raise WarehouseNotFoundError(str(dto.warehouse_id))

        product = self.product_repo.get_by_id(dto.product_id)
        if not product:
            raise ProductNotFoundError(str(dto.product_id))

        stock = self.stock_repo.get_or_create(dto.warehouse_id, dto.product_id)
        diff = dto.actual_quantity - stock.physical_quantity

        if dto.actual_quantity < stock.reserved_quantity:
            raise InsufficientStockError(
                available=dto.actual_quantity,
                requested=stock.reserved_quantity,
            )

        if diff < 0:
            # Manko
            qty = abs(diff)
            note = f"Inventurní manko (-{qty} ks): {dto.note}"
            src_wh_id = dto.warehouse_id
            dst_wh_id = None
        elif diff > 0:
            # Přebytek
            qty = diff
            note = f"Inventurní přebytek (+{qty} ks): {dto.note}"
            src_wh_id = None
            dst_wh_id = dto.warehouse_id
        else:
            # Žádná změna
            qty = 1
            note = f"Inventurní potvrzení stavu ({dto.actual_quantity} ks bez rozdílu): {dto.note}"
            src_wh_id = dto.warehouse_id
            dst_wh_id = dto.warehouse_id

        stock.physical_quantity = dto.actual_quantity
        self.stock_repo.update(stock)

        movement = StockMovement(
            product_id=dto.product_id,
            source_warehouse_id=src_wh_id,
            destination_warehouse_id=dst_wh_id,
            movement_type=StockMovementType.INVENTORY_ADJUSTMENT.value,
            quantity=qty,
            note=note,
            reference_code="INVENTURA",
            performed_by=performed_by,
        )
        saved = self.movement_repo.create(movement)
        return self._format_movement_response(saved)

    def list_movements(
        self,
        product_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
        movement_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[StockMovementResponse]:
        """Získání seznamu auditních záznamů s aplikovanými filtry."""
        movements = self.movement_repo.list_all(
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            limit=limit,
        )
        return [self._format_movement_response(m) for m in movements]
