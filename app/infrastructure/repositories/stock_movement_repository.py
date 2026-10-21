from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.infrastructure.db.models import StockMovement


class StockMovementRepository:
    """Repozitář pro ukládání a auditní vyhledávání skladových pohybů."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, movement: StockMovement) -> StockMovement:
        """Záznam nového skladového pohybu do auditní stopy."""
        try:
            self.db.add(movement)
            self.db.commit()
            self.db.refresh(movement)
            return movement
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, movement_id: UUID) -> Optional[StockMovement]:
        """Získání detailu pohybu podle UUID."""
        return self.db.get(StockMovement, movement_id)

    def list_all(
        self,
        product_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
        movement_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[StockMovement]:
        """Získání seznamu pohybů seřazených od nejnovějšího s volitelnými filtry."""
        stmt = select(StockMovement)

        if product_id is not None:
            stmt = stmt.where(StockMovement.product_id == product_id)

        if warehouse_id is not None:
            stmt = stmt.where(
                or_(
                    StockMovement.source_warehouse_id == warehouse_id,
                    StockMovement.destination_warehouse_id == warehouse_id,
                )
            )

        if movement_type is not None:
            stmt = stmt.where(StockMovement.movement_type == movement_type)

        stmt = stmt.order_by(StockMovement.created_at.desc()).limit(limit)
        return list(self.db.scalars(stmt).all())
