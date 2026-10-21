from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.infrastructure.db.models import Customer


class CustomerRepository:
    """Repozitář pro správu zákazníků v PostgreSQL databázi."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(
        self,
        search: Optional[str] = None,
        only_active: bool = False,
        limit: int = 100,
    ) -> List[Customer]:
        """Získání seznamu zákazníků s volitelným vyhledáváním a filtrem aktivity."""
        query = self.db.query(Customer)
        if only_active:
            query = query.filter(Customer.is_active.is_(True))

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Customer.first_name.ilike(term),
                    Customer.last_name.ilike(term),
                    Customer.email.ilike(term),
                    Customer.phone.ilike(term),
                )
            )

        return query.order_by(Customer.last_name.asc(), Customer.first_name.asc()).limit(limit).all()

    def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        """Vyhledání zákazníka dle primárního klíče UUID."""
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def get_by_email(self, email: str) -> Optional[Customer]:
        """Vyhledání zákazníka dle e-mailu."""
        return self.db.query(Customer).filter(Customer.email.ilike(email.strip())).first()

    def create(self, customer: Customer) -> Customer:
        """Uložení nového zákazníka do databáze."""
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def update(self, customer: Customer) -> Customer:
        """Uložení změn stávajícího zákazníka."""
        self.db.commit()
        self.db.refresh(customer)
        return customer

    def deactivate(self, customer_id: UUID) -> Optional[Customer]:
        """Deaktivace zákazníka (měkké smazání bez ztráty historie dle zadání B)."""
        customer = self.get_by_id(customer_id)
        if customer:
            customer.is_active = False
            self.db.commit()
            self.db.refresh(customer)
        return customer
