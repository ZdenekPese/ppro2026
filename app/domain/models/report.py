from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class RestockActionType(str, Enum):
    """Typ doporučené logistické akce pro doplnění stavu hraček."""

    TRANSFER_FROM_GARAGE = "TRANSFER_FROM_GARAGE"  # Převoz ze sezónní garáže Třebechovice do centrály HK (ADR 1)
    PRODUCE_IN_WORKSHOP = "PRODUCE_IN_WORKSHOP"    # Zadání výroby v truhlárně / nákup od dodavatele
    TRANSFER_AND_PRODUCE = "TRANSFER_AND_PRODUCE"  # Částečný převoz z garáže + doobjednání zbytku


class RestockUrgency(str, Enum):
    """Naléhavost doplnění zásob."""

    CRITICAL = "CRITICAL"  # Skladem je 0 ks disponibilně (okamžité riziko přeprodeje)
    HIGH = "HIGH"          # Skladem je méně než 50 % minimální hladiny
    MEDIUM = "MEDIUM"      # Skladem je pod minimální hladinou


class CategoryTurnoverItem(BaseModel):
    """Agregovaný obrat a ziskovost pro jednu kategorii hraček za zvolené období."""

    category_id: UUID
    category_name: str
    items_sold_count: int = Field(default=0, description="Celkový počet prodaných kusů hraček z této kategorie")
    orders_count: int = Field(default=0, description="Počet objednávek obsahujících produkty z této kategorie")
    total_revenue: Decimal = Field(default=Decimal("0.00"), description="Celkové tržby v Kč (z fixovaných cen položek)")
    total_cost: Decimal = Field(default=Decimal("0.00"), description="Celkové nákupní náklady v Kč")
    gross_profit: Decimal = Field(default=Decimal("0.00"), description="Hrubý zisk v Kč (tržby - nákupní náklady)")
    margin_percentage: Decimal = Field(default=Decimal("0.00"), description="Hrubá marže v %")
    revenue_share_percentage: Decimal = Field(default=Decimal("0.00"), description="Podíl kategorie na tržbách v %")


class FinancialSummary(BaseModel):
    """Celkový finanční a provozní přehled e-shopu Dřevěnka s.r.o. za vybrané období."""

    period_label: str
    year: Optional[int] = None
    month: Optional[int] = None
    total_dispatched_orders: int = 0
    total_reserved_orders: int = 0
    total_items_sold: int = 0
    total_revenue: Decimal = Decimal("0.00")
    total_cost: Decimal = Decimal("0.00")
    total_gross_profit: Decimal = Decimal("0.00")
    average_margin_percentage: Decimal = Decimal("0.00")
    average_order_value: Decimal = Decimal("0.00")


class RestockRecommendationItem(BaseModel):
    """Automatické doporučení pro doplnění zásob dřevěných hraček (ADR 1 & Zadání B)."""

    product_id: UUID
    product_code: str
    product_name: str
    min_stock_level: int
    total_physical: int
    total_reserved: int
    total_available: int
    hk_available: int
    treb_available: int
    recommended_quantity: int
    action_type: RestockActionType
    action_title: str
    action_description: str
    urgency: RestockUrgency
    direct_action_url: str


class TopSellingProductItem(BaseModel):
    """Statistika prodeje konkrétní dřevěné hračky za vybrané období."""

    product_id: UUID
    product_code: str
    product_name: str
    category_names: list[str] = []
    units_sold: int = 0
    total_revenue: Decimal = Decimal("0.00")
    total_cost: Decimal = Decimal("0.00")
    gross_profit: Decimal = Decimal("0.00")
    margin_percentage: Decimal = Decimal("0.00")


class ComprehensiveReportResponse(BaseModel):
    """Komplexní manažerský report obsahující finance, kategorie, doporučení a prodeje."""

    summary: FinancialSummary
    categories: list[CategoryTurnoverItem]
    top_products: list[TopSellingProductItem]
    restock_recommendations: list[RestockRecommendationItem]
