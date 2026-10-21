from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.exceptions import CustomerDeletionForbiddenError, CustomerNotFoundError
from app.domain.models.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.domain.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Zákazníci (E-shop)"])


def get_customer_service(db: Session = Depends(get_db)) -> CustomerService:
    return CustomerService(db)


@router.get("", response_model=List[CustomerResponse])
def list_customers(
    search: Optional[str] = Query(None, description="Hledat podle jména, příjmení, e-mailu či telefonu"),
    only_active: bool = Query(False, description="Zobrazit pouze aktivní zákazníky"),
    limit: int = Query(100, ge=1, le=500),
    service: CustomerService = Depends(get_customer_service),
):
    """Získání seznamu zákazníků e-shopu."""
    return service.list_customers(search=search, only_active=only_active, limit=limit)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    service: CustomerService = Depends(get_customer_service),
):
    """Detail konkrétního zákazníka."""
    try:
        return service.get_customer_response(customer_id)
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    dto: CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
):
    """Založení nového zákazníka."""
    return service.create_customer(dto)


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    dto: CustomerUpdate,
    service: CustomerService = Depends(get_customer_service),
):
    """Úprava údajů zákazníka."""
    try:
        return service.update_customer(customer_id, dto)
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/{customer_id}", response_model=CustomerResponse)
def delete_customer(
    customer_id: UUID,
    service: CustomerService = Depends(get_customer_service),
):
    """
    Deaktivace zákazníka (zákaz fyzického smazání dle zadání B).
    Zákaznická karta zůstává pro potřeby reklamací zachována v databázi.
    """
    try:
        return service.delete_customer(customer_id, force_deactivate=True)
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except CustomerDeletionForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
