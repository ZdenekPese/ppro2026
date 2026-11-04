from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
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
    StockReceiptCreate,
    StockTransferCreate,
)
from app.domain.services.stock_movement_service import StockMovementService
from app.presentation.utils import parse_optional_uuid

router = APIRouter(prefix="/movements", tags=["Pohyby a Audit (Sklad)"])


def get_movement_service(db: Session = Depends(get_db)) -> StockMovementService:
    """Dependency injection pro StockMovementService."""
    return StockMovementService(db)


@router.get("", response_model=List[StockMovementResponse])
def list_movements(
    product_id: Optional[str] = Query(None, description="Filtrovat podle produktu"),
    warehouse_id: Optional[str] = Query(None, description="Filtrovat podle skladu"),
    movement_type: Optional[str] = Query(None, description="Filtrovat podle typu pohybu"),
    limit: int = Query(100, ge=1, le=500, description="Maximální počet záznamů"),
    service: StockMovementService = Depends(get_movement_service),
):
    """Získání auditní stopy všech skladových pohybů."""
    clean_prod_id = parse_optional_uuid(product_id)
    clean_wh_id = parse_optional_uuid(warehouse_id)
    clean_mov_type = movement_type.strip() if movement_type and movement_type.strip() else None
    return service.list_movements(
        product_id=clean_prod_id,
        warehouse_id=clean_wh_id,
        movement_type=clean_mov_type,
        limit=limit,
    )


@router.post("/receipt", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
def record_receipt(
    dto: StockReceiptCreate,
    service: StockMovementService = Depends(get_movement_service),
):
    """Příjem zboží od dodavatele nebo z výroby."""
    try:
        return service.record_receipt(dto)
    except (WarehouseNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/dispatch", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
def record_dispatch(
    dto: StockDispatchCreate,
    service: StockMovementService = Depends(get_movement_service),
):
    """Výdej zboží ze skladu se zákazem záporu."""
    try:
        return service.record_dispatch(dto)
    except (WarehouseNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (InsufficientStockError, NegativeStockError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/transfer", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
def record_transfer(
    dto: StockTransferCreate,
    service: StockMovementService = Depends(get_movement_service),
):
    """Vnitroskladový převoz (např. ze sezónní garáže v Třebechovicích do HK)."""
    try:
        return service.record_transfer(dto)
    except (WarehouseNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (InsufficientStockError, NegativeStockError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post(
    "/inventory-adjustment",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_inventory_adjustment(
    dto: InventoryAdjustmentCreate,
    service: StockMovementService = Depends(get_movement_service),
):
    """Inventurní vyrovnání skladu s plnou auditní stopou."""
    try:
        return service.record_inventory_adjustment(dto)
    except (WarehouseNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (InsufficientStockError, NegativeStockError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
