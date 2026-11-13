from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.services.report_service import CZECH_MONTHS, ReportService
from app.infrastructure.db.models import User
from app.presentation.dependencies import require_manager_user
from app.presentation.utils import get_templates

router = APIRouter(tags=["Web Reporty a Analytika"])

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = get_templates(TEMPLATES_DIR)


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)


@router.get("/reports", response_class=HTMLResponse)
def reports_dashboard_view(
    request: Request,
    year: Optional[int] = None,
    month: Optional[int] = None,
    include_reserved: Optional[str] = None,
    db: Session = Depends(get_db),
    service: ReportService = Depends(get_report_service),
    current_user: User = Depends(require_manager_user),
):
    """
    Manažerský reportovací a analytický dashboard pro pana Petra Doležala.
    Zahrnuje obrat po kategoriích, přehled ziskovosti a doporučení k doobjednání / plánování výroby.
    """
    now = datetime.now()
    # Výchozí hodnoty: aktuální rok 2026 a aktuální měsíc
    selected_year = year if year is not None else now.year
    selected_month = month if (month is not None and month > 0) else (None if month == 0 else now.month)
    is_reserved = True if include_reserved in ("on", "true", "1") else False

    report_data = service.get_comprehensive_report(
        year=selected_year if selected_year and selected_year > 0 else None,
        month=selected_month,
        include_reserved=is_reserved,
    )

    available_years = [2026, 2025, 2024]
    months_options = [{"value": m_num, "name": m_name} for m_num, m_name in CZECH_MONTHS.items()]

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "summary": report_data.summary,
            "categories": report_data.categories,
            "top_products": report_data.top_products,
            "restock_recommendations": report_data.restock_recommendations,
            "selected_year": selected_year,
            "selected_month": selected_month,
            "include_reserved": is_reserved,
            "available_years": available_years,
            "months_options": months_options,
            "critical_restock_count": sum(
                1 for r in report_data.restock_recommendations if r.urgency == "CRITICAL"
            ),
            "transfer_count": sum(
                1
                for r in report_data.restock_recommendations
                if r.action_type in ("TRANSFER_FROM_GARAGE", "TRANSFER_AND_PRODUCE")
            ),
        },
    )
