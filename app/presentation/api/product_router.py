from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.exceptions import (
    DuplicateProductCodeError,
    ProductNotFoundError,
    InvalidPriceError,
)
from app.domain.models.product import ProductCreate, ProductUpdate, ProductResponse
from app.domain.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Produkty (Hračky)"])


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    """Dependency injection pro ProductService."""
    return ProductService(db)


@router.get("", response_model=List[ProductResponse])
def list_products(
    search: Optional[str] = Query(None, description="Hledat podle kódu, názvu nebo popisu"),
    is_active: Optional[bool] = Query(None, description="Filtrovat podle aktivity"),
    category_id: Optional[UUID] = Query(None, description="Filtrovat podle kategorie"),
    service: ProductService = Depends(get_product_service),
):
    """Získání seznamu produktů (dřevěných hraček) s možností filtrování dle kategorie."""
    return service.list_products(search=search, is_active=is_active, category_id=category_id)



@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    service: ProductService = Depends(get_product_service),
):
    """Detail konkrétního produktu."""
    try:
        return service.get_product(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    dto: ProductCreate,
    service: ProductService = Depends(get_product_service),
):
    """Založení nového produktu do katalogu."""
    try:
        return service.create_product(dto)
    except DuplicateProductCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InvalidPriceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    dto: ProductUpdate,
    service: ProductService = Depends(get_product_service),
):
    """Úprava existujícího produktu."""
    try:
        return service.update_product(product_id, dto)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidPriceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.patch("/{product_id}/toggle-active", response_model=ProductResponse)
def toggle_product_active(
    product_id: UUID,
    service: ProductService = Depends(get_product_service),
):
    """Aktivace nebo deaktivace produktu."""
    try:
        return service.toggle_active(product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
