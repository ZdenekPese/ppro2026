from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Warehouse


class WarehouseRepository:
    """Repozitář pro přístup ke skladům v databázi PostgreSQL."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> List[Warehouse]:
        """Vrátí všechny evidované sklady seřazené (primární sklad jako první)."""
        stmt = select(Warehouse).order_by(Warehouse.is_primary.desc(), Warehouse.name.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, warehouse_id: UUID) -> Optional[Warehouse]:
        """Vyhledání skladu podle primárního klíče UUID."""
        return self.db.get(Warehouse, warehouse_id)

    def get_by_code(self, code: str) -> Optional[Warehouse]:
        """Vyhledání skladu podle kódu (např. WH-HK)."""
        stmt = select(Warehouse).where(Warehouse.code == code.strip().upper())
        return self.db.scalars(stmt).first()

    def get_primary(self) -> Optional[Warehouse]:
        """Vrátí primární sklad určený pro standardní expedici."""
        stmt = select(Warehouse).where(Warehouse.is_primary == True)
        return self.db.scalars(stmt).first()

    def create(self, warehouse: Warehouse) -> Warehouse:
        """Uložení nového skladu."""
        try:
            self.db.add(warehouse)
            self.db.commit()
            self.db.refresh(warehouse)
            return warehouse
        except Exception:
            self.db.rollback()
            raise

    def update(self, warehouse: Warehouse) -> Warehouse:
        """Uložení změn skladu."""
        try:
            self.db.commit()
            self.db.refresh(warehouse)
            return warehouse
        except Exception:
            self.db.rollback()
            raise

    def delete(self, warehouse: Warehouse) -> None:
        """Smazání skladu."""
        try:
            self.db.delete(warehouse)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
