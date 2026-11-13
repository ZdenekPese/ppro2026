from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote
from uuid import UUID
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.models.stock_movement import StockReceiptCreate, StockTransferCreate
from app.domain.services.stock_movement_service import StockMovementService
from app.domain.services.warehouse_service import WarehouseService
from app.infrastructure.db.models import User
from app.infrastructure.repositories.category_repository import CategoryRepository
from app.infrastructure.repositories.product_repository import ProductRepository
from app.presentation.dependencies import require_web_user
from app.presentation.utils import parse_optional_uuid

router = APIRouter(tags=["Web Dashboard"])

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_warehouse_service(db: Session = Depends(get_db)) -> WarehouseService:
    return WarehouseService(db)


def _render_dashboard(
    request: Request,
    db: Session,
    service: WarehouseService,
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    only_critical: bool = False,
    action_ok: Optional[str] = None,
    action_qty: Optional[int] = None,
    action_sku: Optional[str] = None,
    action_ref: Optional[str] = None,
    action_error: Optional[str] = None,
    status_code: int = status.HTTP_200_OK,
):
    clean_category_id = parse_optional_uuid(category_id)
    summary = service.get_dashboard_summary()
    stocks_overview = service.get_products_stock_overview(
        search=search,
        category_id=clean_category_id,
        only_critical=only_critical,
    )
    categories = CategoryRepository(db).list_all()
    warehouses = service.list_warehouses()
    hk_warehouse = next((w for w in warehouses if w.code == "WH-HK"), None) or next(
        (w for w in warehouses if w.is_primary), None
    )
    treb_warehouse = next((w for w in warehouses if w.code == "WH-TREB"), None) or next(
        (w for w in warehouses if not w.is_primary), None
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "summary": summary,
            "stocks": stocks_overview,
            "warehouses": warehouses,
            "hk_warehouse": hk_warehouse,
            "treb_warehouse": treb_warehouse,
            "categories": categories,
            "selected_category_id": clean_category_id,
            "search": search or "",
            "only_critical": only_critical,
            "action_ok": action_ok,
            "action_qty": action_qty,
            "action_sku": action_sku,
            "action_ref": action_ref,
            "action_error": action_error,
            "title": "Přehled skladu & Dashboard - Dřevěnka s.r.o.",
        },
        status_code=status_code,
    )


@router.get("/", response_class=HTMLResponse)
def dashboard_view(
    request: Request,
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    only_critical: bool = False,
    action_ok: Optional[str] = None,
    action_qty: Optional[int] = None,
    action_sku: Optional[str] = None,
    action_ref: Optional[str] = None,
    db: Session = Depends(get_db),
    service: WarehouseService = Depends(get_warehouse_service),
    current_user: User = Depends(require_web_user),
):
    """Barevný dashboard skladu s indikací položek pod minimem („co hoří“) a rozpadem skladů."""
    return _render_dashboard(
        request=request,
        db=db,
        service=service,
        search=search,
        category_id=category_id,
        only_critical=only_critical,
        action_ok=action_ok,
        action_qty=action_qty,
        action_sku=action_sku,
        action_ref=action_ref,
    )


@router.post("/quick-action", response_class=HTMLResponse)
def dashboard_quick_action(
    request: Request,
    action_type: str = Form(...),
    product_id: UUID = Form(...),
    quantity: int = Form(...),
    warehouse_id: Optional[UUID] = Form(None),
    source_warehouse_id: Optional[UUID] = Form(None),
    destination_warehouse_id: Optional[UUID] = Form(None),
    reference_code: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
    confirmed: bool = Form(False),
    db: Session = Depends(get_db),
    service: WarehouseService = Depends(get_warehouse_service),
    current_user: User = Depends(require_web_user),
):
    """Rychlé doplnění nebo meziskladový přesun z upozornění docházejícího zboží s vědomým potvrzením."""
    if not confirmed:
        return _render_dashboard(
            request=request,
            db=db,
            service=service,
            action_error="Operace nebyla provedena — je nutné zaškrtnout vědomé potvrzení změny skladových zásob.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    warehouses = service.list_warehouses()
    hk_warehouse = next((w for w in warehouses if w.code == "WH-HK"), None) or next(
        (w for w in warehouses if w.is_primary), None
    )
    treb_warehouse = next((w for w in warehouses if w.code == "WH-TREB"), None) or next(
        (w for w in warehouses if not w.is_primary), None
    )
    product = ProductRepository(db).get_by_id(product_id)
    sku_label = product.code if product else ""
    movement_service = StockMovementService(db)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    cleaned_ref = (reference_code or "").strip()

    try:
        if action_type == "receipt":
            target_wh_id = warehouse_id or (hk_warehouse.id if hk_warehouse else None)
            if not target_wh_id:
                raise ValueError("Nebyl nalezen cílový sklad pro naskladnění.")
            doc_ref = cleaned_ref or f"DL-{stamp}"
            dto = StockReceiptCreate(
                warehouse_id=target_wh_id,
                product_id=product_id,
                quantity=quantity,
                reference_code=doc_ref,
                note=(note or "").strip() or "Rychlé doplnění docházející položky z přehledu skladu",
            )
            movement_service.record_receipt(dto, performed_by=current_user.full_name)
        elif action_type == "transfer":
            src_id = source_warehouse_id or (treb_warehouse.id if treb_warehouse else None)
            dst_id = destination_warehouse_id or (hk_warehouse.id if hk_warehouse else None)
            if not src_id or not dst_id:
                raise ValueError("Nebyly nalezeny oba sklady pro meziskladový přesun.")
            doc_ref = cleaned_ref or f"PREV-{stamp}"
            dto = StockTransferCreate(
                source_warehouse_id=src_id,
                destination_warehouse_id=dst_id,
                product_id=product_id,
                quantity=quantity,
                reference_code=doc_ref,
                note=(note or "").strip() or "Rychlý přesun docházející položky z garáže do Hradce",
            )
            movement_service.record_transfer(dto, performed_by=current_user.full_name)
        else:
            raise ValueError("Neplatný typ rychlé skladové operace.")

        sku_param = quote(sku_label, safe="")
        ref_param = quote(doc_ref, safe="")
        return RedirectResponse(
            url=f"/?action_ok={action_type}&action_qty={quantity}&action_sku={sku_param}&action_ref={ref_param}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:
        return _render_dashboard(
            request=request,
            db=db,
            service=service,
            action_error=str(exc),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
