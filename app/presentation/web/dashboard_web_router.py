from pathlib import Path
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.services.warehouse_service import WarehouseService
from app.infrastructure.db.models import User
from app.infrastructure.repositories.category_repository import CategoryRepository
from app.presentation.dependencies import require_web_user
from app.presentation.utils import parse_optional_uuid

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
    category_id: Optional[str] = None,
    only_critical: bool = False,
    db: Session = Depends(get_db),
    service: WarehouseService = Depends(get_warehouse_service),
    current_user: User = Depends(require_web_user),
):
    """Barevný dashboard skladu s indikací položek pod minimem („co hoří“) a rozpadem skladů."""
    clean_category_id = parse_optional_uuid(category_id)
    summary = service.get_dashboard_summary()
    stocks_overview = service.get_products_stock_overview(
        search=search,
        category_id=clean_category_id,
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
            "selected_category_id": clean_category_id,
            "search": search or "",
            "only_critical": only_critical,
            "title": "Přehled skladu & Dashboard - Dřevěnka s.r.o.",
        },
    )
