from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.domain.exceptions import CustomerDeletionForbiddenError, CustomerNotFoundError
from app.domain.models.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.infrastructure.db.models import Customer
from app.infrastructure.repositories.customer_repository import CustomerRepository


class CustomerService:
    """Aplikační služba pro správu zákazníků e-shopu Dřevěnka s.r.o. (Fáze 6)."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = CustomerRepository(db)

    def _format_customer(self, customer: Customer) -> CustomerResponse:
        """Převedení ORM entity na DTO response včetně počtu objednávek."""
        orders_count = len(customer.orders) if customer.orders else 0
        return CustomerResponse(
            id=customer.id,
            first_name=customer.first_name,
            last_name=customer.last_name,
            full_name=customer.full_name,
            email=customer.email,
            phone=customer.phone,
            address=customer.address,
            is_active=customer.is_active,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            orders_count=orders_count,
        )

    def list_customers(
        self,
        search: Optional[str] = None,
        only_active: bool = False,
        limit: int = 100,
    ) -> List[CustomerResponse]:
        """Získání seznamu zákazníků."""
        customers = self.repository.list_all(search=search, only_active=only_active, limit=limit)
        return [self._format_customer(c) for c in customers]

    def get_customer(self, customer_id: UUID) -> Customer:
        """Získání ORM entity zákazníka s kontrolou existence."""
        customer = self.repository.get_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundError(str(customer_id))
        return customer

    def get_customer_response(self, customer_id: UUID) -> CustomerResponse:
        """Získání DTO detailu zákazníka."""
        customer = self.get_customer(customer_id)
        return self._format_customer(customer)

    def create_customer(self, dto: CustomerCreate) -> CustomerResponse:
        """Založení nového zákazníka."""
        customer = Customer(
            first_name=dto.first_name.strip(),
            last_name=dto.last_name.strip(),
            email=dto.email.strip().lower(),
            phone=dto.phone.strip() if dto.phone else None,
            address=dto.address.strip(),
            is_active=True,
        )
        saved = self.repository.create(customer)
        return self._format_customer(saved)

    def update_customer(self, customer_id: UUID, dto: CustomerUpdate) -> CustomerResponse:
        """Úprava údajů zákazníka."""
        customer = self.get_customer(customer_id)
        if dto.first_name is not None:
            customer.first_name = dto.first_name.strip()
        if dto.last_name is not None:
            customer.last_name = dto.last_name.strip()
        if dto.email is not None:
            customer.email = dto.email.strip().lower()
        if dto.phone is not None:
            customer.phone = dto.phone.strip() if dto.phone else None
        if dto.address is not None:
            customer.address = dto.address.strip()
        if dto.is_active is not None:
            customer.is_active = dto.is_active

        updated = self.repository.update(customer)
        return self._format_customer(updated)

    def delete_customer(self, customer_id: UUID, force_deactivate: bool = True) -> CustomerResponse:
        """
        Zákaz mazání zákazníků (Zadání B).
        Fyzické smazání je zakázáno pro zachování historie reklamací a dokladů.
        Zákazník se pouze označí jako neaktivní (soft-delete).
        """
        customer = self.get_customer(customer_id)
        if not force_deactivate:
            raise CustomerDeletionForbiddenError(
                str(customer_id),
                reason="Dle zadání klienta se zákaznické karty nesmí fyzicky mazat z databáze.",
            )

        customer.is_active = False
        updated = self.repository.update(customer)
        return self._format_customer(updated)
