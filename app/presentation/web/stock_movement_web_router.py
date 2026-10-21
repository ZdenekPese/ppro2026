from pathlib import Path
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
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
    StockMovementType,
    StockReceiptCreate,
    StockTransferCreate,
)
from app.domain.services.stock_movement_service import StockMovementService
from app.infrastructure.repositories.product_repository import ProductRepository
from app.infrastructure.repositories.warehouse_repository import WarehouseRepository

router = APIRouter(prefix="/movements", tags=["Web Pohyby a Audit"])

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_movement_service(db: Session = Depends(get_db)) -> StockMovementService:
    return StockMovementService(db)


@router.get("", response_class=HTMLResponse)
def movements_list_view(
    request: Request,
    product_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    movement_type: Optional[str] = None,
    db: Session = Depends(get_db),
    service: StockMovementService = Depends(get_movement_service),
):
    """Zobrazení auditního deníku skladových pohybů s filtry."""
    movements = service.list_movements(
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
    )
    products = ProductRepository(db).list_all()
    warehouses = WarehouseRepository(db).list_all()

    return templates.TemplateResponse(
        request=request,
        name="stock_movements.html",
        context={
            "movements": movements,
            "products": products,
            "warehouses": warehouses,
            "selected_product_id": product_id,
            "selected_warehouse_id": warehouse_id,
            "selected_movement_type": movement_type,
            "title": "Auditní deník skladových pohybů - Dřevěnka s.r.o.",
        },
    )


@router.get("/new", response_class=HTMLResponse)
def movement_new_view(
    request: Request,
    movement_type: Optional[str] = "receipt",
    product_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
):
    """Zobrazení formuláře pro zadání nového skladového pohybu."""
    products = ProductRepository(db).list_all()
    warehouses = WarehouseRepository(db).list_all()

    return templates.TemplateResponse(
        request=request,
        name="stock_movement_form.html",
        context={
            "products": products,
            "warehouses": warehouses,
            "active_type": movement_type,
            "selected_product_id": product_id,
            "error": None,
            "title": "Nový skladový pohyb - Dřevěnka s.r.o.",
        },
    )


@router.post("/receipt", response_class=HTMLResponse)
def movement_receipt_submit(
    request: Request,
    warehouse_id: UUID = Form(...),
    product_id: UUID = Form(...),
    quantity: int = Form(...),
    note: Optional[str] = Form(None),
    reference_code: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    service: StockMovementService = Depends(get_movement_service),
):
    """Zpracování příjmu zboží na sklad."""
    try:
        dto = StockReceiptCreate(
            warehouse_id=warehouse_id,
            product_id=product_id,
            quantity=quantity,
            note=note,
            reference_code=reference_code,
        )
        service.record_receipt(dto)
        return RedirectResponse(url="/movements", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as exc:
        products = ProductRepository(db).list_all()
        warehouses = WarehouseRepository(db).list_all()
        return templates.TemplateResponse(
            request=request,
            name="stock_movement_form.html",
            context={
                "products": products,
                "warehouses": warehouses,
                "active_type": "receipt",
                "error": str(exc),
                "title": "Chyba při příjmu zboží",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


@router.post("/transfer", response_class=HTMLResponse)
def movement_transfer_submit(
    request: Request,
    source_warehouse_id: UUID = Form(...),
    destination_warehouse_id: UUID = Form(...),
    product_id: UUID = Form(...),
    quantity: int = Form(...),
    note: Optional[str] = Form(None),
    reference_code: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    service: StockMovementService = Depends(get_movement_service),
):
    """Zpracování vnitroskladového přesunu mezi sklady."""
    try:
        dto = StockTransferCreate(
            source_warehouse_id=source_warehouse_id,
            destination_warehouse_id=destination_warehouse_id,
            product_id=product_id,
            quantity=quantity,
            note=note,
            reference_code=reference_code,
        )
        service.record_transfer(dto)
        return RedirectResponse(url="/movements", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as exc:
        products = ProductRepository(db).list_all()
        warehouses = WarehouseRepository(db).list_all()
        return templates.TemplateResponse(
            request=request,
            name="stock_movement_form.html",
            context={
                "products": products,
                "warehouses": warehouses,
                "active_type": "transfer",
                "error": str(exc),
                "title": "Chyba při meziskladovém přesunu",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


@router.post("/inventory-adjustment", response_class=HTMLResponse)
def movement_inventory_adjustment_submit(
    request: Request,
    warehouse_id: UUID = Form(...),
    product_id: UUID = Form(...),
    actual_quantity: int = Form(...),
    note: str = Form(...),
    db: Session = Depends(get_db),
    service: StockMovementService = Depends(get_movement_service),
):
    """Zpracování inventurního vyrovnání."""
    try:
        dto = InventoryAdjustmentCreate(
            warehouse_id=warehouse_id,
            product_id=product_id,
            actual_quantity=actual_quantity,
            note=note,
        )
        service.record_inventory_adjustment(dto)
        return RedirectResponse(url="/movements", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as exc:
        products = ProductRepository(db).list_all()
        warehouses = WarehouseRepository(db).list_all()
        return templates.TemplateResponse(
            request=request,
            name="stock_movement_form.html",
            context={
                "products": products,
                "warehouses": warehouses,
                "active_type": "inventory_adjustment",
                "error": str(exc),
                "title": "Chyba při inventuře",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
