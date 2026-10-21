from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import WarehouseStock


class WarehouseStockRepository:
    """Repozitář pro správu skladových zásob produktů v jednotlivých skladech."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, stock_id: UUID) -> Optional[WarehouseStock]:
        """Vyhledání záznamu zásoby podle UUID."""
        return self.db.get(WarehouseStock, stock_id)

    def get_by_warehouse_and_product(
        self,
        warehouse_id: UUID,
        product_id: UUID,
    ) -> Optional[WarehouseStock]:
        """Vyhledání zásoby konkrétního produktu na daném skladě."""
        stmt = (
            select(WarehouseStock)
            .where(WarehouseStock.warehouse_id == warehouse_id)
            .where(WarehouseStock.product_id == product_id)
        )
        return self.db.scalars(stmt).first()

    def list_by_warehouse(self, warehouse_id: UUID) -> List[WarehouseStock]:
        """Vrátí všechny zásoby pro daný sklad."""
        stmt = select(WarehouseStock).where(WarehouseStock.warehouse_id == warehouse_id)
        return list(self.db.scalars(stmt).all())

    def list_by_product(self, product_id: UUID) -> List[WarehouseStock]:
        """Vrátí rozpad zásob daného produktu napříč všemi sklady."""
        stmt = select(WarehouseStock).where(WarehouseStock.product_id == product_id)
        return list(self.db.scalars(stmt).all())

    def list_all(self) -> List[WarehouseStock]:
        """Vrátí všechny skladové zásoby v systému."""
        stmt = select(WarehouseStock)
        return list(self.db.scalars(stmt).all())

    def create(self, stock: WarehouseStock) -> WarehouseStock:
        """Vytvoření nového záznamu zásoby."""
        try:
            self.db.add(stock)
            self.db.commit()
            self.db.refresh(stock)
            return stock
        except Exception:
            self.db.rollback()
            raise

    def update(self, stock: WarehouseStock) -> WarehouseStock:
        """Uložení změn v zásobě."""
        try:
            self.db.commit()
            self.db.refresh(stock)
            return stock
        except Exception:
            self.db.rollback()
            raise

    def get_or_create(self, warehouse_id: UUID, product_id: UUID) -> WarehouseStock:
        """Vrátí existující zásobu nebo inicializuje novou s nulovým počtem kusů."""
        stock = self.get_by_warehouse_and_product(warehouse_id, product_id)
        if not stock:
            stock = WarehouseStock(
                warehouse_id=warehouse_id,
                product_id=product_id,
                physical_quantity=0,
                reserved_quantity=0,
            )
            stock = self.create(stock)
        return stock
