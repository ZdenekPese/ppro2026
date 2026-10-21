from pathlib import Path
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.services.warehouse_service import WarehouseService
from app.infrastructure.repositories.category_repository import CategoryRepository

router = APIRouter(tags=["Web Dashboard"])

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_warehouse_service(db: Session = Depends(get_db)) -> WarehouseService:
    return WarehouseService(db)


@router.get("/", response_class=HTMLResponse)
def dashboard_view(
    request: Request,
    search: Optional[str] = None,
    category_id: Optional[UUID] = None,
    only_critical: bool = False,
    db: Session = Depends(get_db),
    service: WarehouseService = Depends(get_warehouse_service),
):
    """Barevný dashboard skladu s indikací položek pod minimem („co hoří“) a rozpadem skladů."""
    summary = service.get_dashboard_summary()
    stocks_overview = service.get_products_stock_overview(
        search=search,
        category_id=category_id,
        only_critical=only_critical,
    )
    categories = CategoryRepository(db).list_all()
    warehouses = service.list_warehouses()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "summary": summary,
            "stocks": stocks_overview,
            "warehouses": warehouses,
            "categories": categories,
            "selected_category_id": category_id,
            "search": search or "",
            "only_critical": only_critical,
            "title": "Přehled skladu & Dashboard - Dřevěnka s.r.o.",
        },
    )
