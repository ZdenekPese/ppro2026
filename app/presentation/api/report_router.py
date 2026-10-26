from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.models.report import (
    CategoryTurnoverItem,
    ComprehensiveReportResponse,
    FinancialSummary,
    RestockRecommendationItem,
    TopSellingProductItem,
)
from app.domain.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reporty a Analytika (Fáze 7)"])


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)


@router.get("/category-turnover", response_model=List[CategoryTurnoverItem])
def get_category_turnover(
    year: Optional[int] = Query(None, description="Rok (např. 2026)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Měsíc (1-12)"),
    include_reserved: bool = Query(
        False, description="Zda započítat i rezervované neexpedované objednávky"
    ),
    service: ReportService = Depends(get_report_service),
):
    """
    Měsíční obrat po kategoriích dřevěných hraček.
    Respektuje M:N vazbu (jedna hračka může spadat do více kategorií současně).
    """
    return service.get_monthly_category_turnover(
        year=year, month=month, include_reserved=include_reserved
    )


@router.get("/financial-summary", response_model=FinancialSummary)
def get_financial_summary(
    year: Optional[int] = Query(None, description="Rok (např. 2026)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Měsíc (1-12)"),
    include_reserved: bool = Query(
        False, description="Zda započítat i rezervované neexpedované objednávky"
    ),
    service: ReportService = Depends(get_report_service),
):
    """
    Celkový finanční a provozní přehled e-shopu Dřevěnka s.r.o.
    Tržby, nákupní náklady, hrubý zisk v Kč a průměrná marže dílny.
    """
    return service.get_financial_summary(
        year=year, month=month, include_reserved=include_reserved
    )


@router.get("/top-products", response_model=List[TopSellingProductItem])
def get_top_selling_products(
    year: Optional[int] = Query(None, description="Rok"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Měsíc"),
    limit: int = Query(10, ge=1, le=50, description="Maximální počet vrácených položek"),
    include_reserved: bool = Query(
        False, description="Zda započítat i rezervované objednávky"
    ),
    service: ReportService = Depends(get_report_service),
):
    """Žebříček nejprodávanějších dřevěných hraček za zvolené období."""
    return service.get_top_selling_products(
        year=year, month=month, limit=limit, include_reserved=include_reserved
    )


@router.get("/restock-recommendations", response_model=List[RestockRecommendationItem])
def get_restock_recommendations(
    service: ReportService = Depends(get_report_service),
):
    """
    Automatický seznam položek k doobjednání a plánování výroby (ADR 1).
    Detekuje položky pod minimální zásobou a rozlišuje meziskladový převoz z garáže vs. výrobu v truhlárně.
    """
    return service.get_restock_recommendations()


@router.get("/comprehensive", response_model=ComprehensiveReportResponse)
def get_comprehensive_report(
    year: Optional[int] = Query(None, description="Rok"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Měsíc"),
    include_reserved: bool = Query(
        False, description="Zda započítat i rezervované objednávky"
    ),
    service: ReportService = Depends(get_report_service),
):
    """Kompletní manažerský přehled spojující souhrny, obraty kategorií, TOP produkty i plán nákupů."""
    return service.get_comprehensive_report(
        year=year, month=month, include_reserved=include_reserved
    )
