from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.exceptions import (
    CustomerNotFoundError,
    InsufficientStockError,
    InvalidOrderStatusError,
    NegativeStockError,
    OrderNotFoundError,
    ProductNotFoundError,
    WarehouseNotFoundError,
)
from app.domain.models.order import OrderCreate, OrderResponse
from app.domain.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Objednávky (E-shop)"])


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    return OrderService(db)


@router.get("", response_model=List[OrderResponse])
def list_orders(
    status_filter: Optional[str] = Query(None, alias="status", description="Filtrovat podle stavu (NEW, RESERVED, DISPATCHED, CANCELLED)"),
    customer_id: Optional[UUID] = Query(None, description="Filtrovat podle zákazníka"),
    warehouse_id: Optional[UUID] = Query(None, description="Filtrovat podle skladu"),
    search: Optional[str] = Query(None, description="Hledat podle čísla objednávky nebo jména zákazníka"),
    limit: int = Query(100, ge=1, le=500),
    service: OrderService = Depends(get_order_service),
):
    """Získání seznamu objednávek."""
    return service.list_orders(
        status=status_filter,
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        search=search,
        limit=limit,
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: UUID,
    service: OrderService = Depends(get_order_service),
):
    """Detail konkrétní objednávky včetně položek a kalkulací."""
    try:
        return service.get_order_response(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    dto: OrderCreate,
    service: OrderService = Depends(get_order_service),
):
    """
    Příjem nové objednávky z e-shopu s okamžitou rezervací kusů.
    Zabraňuje přeprodeji zboží a fixuje prodejní ceny.
    """
    try:
        return service.create_order(dto)
    except (CustomerNotFoundError, WarehouseNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (InsufficientStockError, NegativeStockError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/{order_id}/dispatch", response_model=OrderResponse)
def dispatch_order(
    order_id: UUID,
    service: OrderService = Depends(get_order_service),
):
    """
    Fyzická expedice objednávky.
    Provede fyzický odpis z regálu, uvolní rezervaci a zapíše auditní pohyb do StockMovement.
    """
    try:
        return service.dispatch_order(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidOrderStatusError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InsufficientStockError, NegativeStockError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: UUID,
    service: OrderService = Depends(get_order_service),
):
    """
    Storno objednávky.
    Uvolní zarezervované kusy zpět do disponibilního prodeje.
    """
    try:
        return service.cancel_order(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidOrderStatusError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
