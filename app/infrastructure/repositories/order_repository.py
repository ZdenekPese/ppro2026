from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.infrastructure.db.models import Order, Customer


class OrderRepository:
    """Repozitář pro správu objednávek v PostgreSQL databázi."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(
        self,
        status: Optional[str] = None,
        customer_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[Order]:
        """Získání seznamu objednávek s aplikovanými filtry."""
        query = self.db.query(Order).join(Customer)

        if status:
            query = query.filter(Order.status == status)
        if customer_id:
            query = query.filter(Order.customer_id == customer_id)
        if warehouse_id:
            query = query.filter(Order.warehouse_id == warehouse_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Order.order_number.ilike(term),
                    Customer.first_name.ilike(term),
                    Customer.last_name.ilike(term),
                    Customer.email.ilike(term),
                )
            )

        return query.order_by(Order.created_at.desc()).limit(limit).all()

    def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """Získání detailu objednávky dle ID."""
        return self.db.query(Order).filter(Order.id == order_id).first()

    def get_by_order_number(self, order_number: str) -> Optional[Order]:
        """Vyhledání objednávky dle unikátního čísla."""
        return self.db.query(Order).filter(Order.order_number.ilike(order_number.strip())).first()

    def generate_next_order_number(self) -> str:
        """Vygenerování dalšího unikátního čísla objednávky (např. OBJ-2026-0001)."""
        current_year = datetime.now().year
        prefix = f"OBJ-{current_year}-"
        count = self.db.query(func.count(Order.id)).filter(Order.order_number.like(f"{prefix}%")).scalar() or 0
        seq = count + 1
        
        # Pojistka pro unikátnost
        while True:
            candidate = f"{prefix}{seq:04d}"
            if not self.get_by_order_number(candidate):
                return candidate
            seq += 1

    def create(self, order: Order) -> Order:
        """Uložení nové objednávky včetně položek."""
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def update(self, order: Order) -> Order:
        """Uložení změn objednávky (např. po expedici či stornu)."""
        self.db.commit()
        self.db.refresh(order)
        return order
