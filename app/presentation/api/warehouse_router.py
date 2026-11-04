from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.exceptions import (
    DuplicateWarehouseCodeError,
    InsufficientStockError,
    NegativeStockError,
    ProductNotFoundError,
    WarehouseNotFoundError,
)
from app.domain.models.warehouse import (
    DashboardSummary,
    ProductStockDetail,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseStockResponse,
    WarehouseStockUpdate,
    WarehouseUpdate,
)
from app.domain.services.warehouse_service import WarehouseService
from app.presentation.utils import parse_optional_uuid

router = APIRouter(prefix="", tags=["Sklady a Zásoby"])


def get_warehouse_service(db: Session = Depends(get_db)) -> WarehouseService:
    """Dependency injection pro WarehouseService."""
    return WarehouseService(db)


# ==================== REST Endpointy: Sklady ====================

@router.get("/warehouses", response_model=List[WarehouseResponse])
def list_warehouses(
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Získání seznamu všech skladů (Hradec Králové, Třebechovice, dílna)."""
    return service.list_warehouses()


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    dto: WarehouseCreate,
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Vytvoření nového skladu."""
    try:
        return service.create_warehouse(dto)
    except DuplicateWarehouseCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(
    warehouse_id: UUID,
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Detail konkrétního skladu."""
    try:
        wh = service.get_warehouse(warehouse_id)
        return WarehouseResponse.model_validate(wh)
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: UUID,
    dto: WarehouseUpdate,
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Úprava parametrů skladu."""
    try:
        return service.update_warehouse(warehouse_id, dto)
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/warehouses/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_warehouse(
    warehouse_id: UUID,
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Smazání skladu."""
    try:
        service.delete_warehouse(warehouse_id)
    except WarehouseNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ==================== REST Endpointy: Zásoby ====================

@router.get("/stocks", response_model=List[ProductStockDetail])
def list_stocks_overview(
    search: Optional[str] = Query(None, description="Hledat podle kódu nebo názvu"),
    category_id: Optional[str] = Query(None, description="Filtrovat podle kategorie"),
    only_critical: bool = Query(False, description="Zobrazit pouze položky pod minimem"),
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Získání přehledu skladových zásob rozpadlých po skladech s indikací stavu pod minimem."""
    clean_category_id = parse_optional_uuid(category_id)
    return service.get_products_stock_overview(
        search=search,
        category_id=clean_category_id,
        only_critical=only_critical,
    )


@router.get("/warehouses/{warehouse_id}/stocks/{product_id}", response_model=WarehouseStockResponse)
def get_warehouse_stock(
    warehouse_id: UUID,
    product_id: UUID,
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Získání stavu zásoby konkrétního produktu na daném skladě."""
    try:
        stock = service.get_stock(warehouse_id, product_id)
        return WarehouseStockResponse.model_validate(stock)
    except (WarehouseNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/warehouses/{warehouse_id}/stocks/{product_id}", response_model=WarehouseStockResponse)
def update_warehouse_stock(
    warehouse_id: UUID,
    product_id: UUID,
    dto: WarehouseStockUpdate,
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Úprava / inventurní korekce skladové zásoby."""
    try:
        return service.update_stock(warehouse_id, product_id, dto)
    except (WarehouseNotFoundError, ProductNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except (NegativeStockError, InsufficientStockError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ==================== REST Endpointy: Dashboard ====================

@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Získání kompletních agregovaných dat pro úvodní dashboard skladu."""
    return service.get_dashboard_summary()
