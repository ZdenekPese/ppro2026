from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.domain.models.report import (
    CategoryTurnoverItem,
    ComprehensiveReportResponse,
    FinancialSummary,
    RestockActionType,
    RestockRecommendationItem,
    RestockUrgency,
    TopSellingProductItem,
)
from app.infrastructure.db.models import (
    Category,
    Order,
    OrderItem,
    Product,
    Warehouse,
    WarehouseStock,
    product_categories,
)

CZECH_MONTHS = {
    1: "Leden",
    2: "Únor",
    3: "Březen",
    4: "Duben",
    5: "Květen",
    6: "Červen",
    7: "Červenec",
    8: "Srpen",
    9: "Září",
    10: "Říjen",
    11: "Listopad",
    12: "Prosinec",
}


class ReportService:
    """Aplikační služba pro manažerský reporting a skladovou analytiku (Fáze 7)."""

    def __init__(self, db: Session):
        self.db = db

    def _get_period_label(self, year: Optional[int], month: Optional[int]) -> str:
        """Sestavení lidsky čitelného označení vybraného období."""
        if year and month:
            month_name = CZECH_MONTHS.get(month, f"{month}.")
            return f"{month_name} {year}"
        elif year:
            return f"Rok {year}"
        elif month:
            month_name = CZECH_MONTHS.get(month, f"{month}.")
            return f"{month_name} (všechny roky)"
        return "Celé období"

    def _filter_orders_query(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        include_reserved: bool = False,
    ):
        """Sestaví filtrovaný dotaz na objednávky dle stavu a data."""
        query = self.db.query(Order)
        if include_reserved:
            query = query.filter(Order.status.in_(["DISPATCHED", "RESERVED"]))
        else:
            query = query.filter(Order.status == "DISPATCHED")

        # Filtrování podle data vytvoření/expedice
        if year:
            query = query.filter(extract("year", Order.created_at) == year)
        if month:
            query = query.filter(extract("month", Order.created_at) == month)

        return query

    def get_financial_summary(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        include_reserved: bool = False,
    ) -> FinancialSummary:
        """Vypočte celkový finanční souhrn e-shopu (tržby, náklady, zisk, průměrná marže)."""
        orders = self._filter_orders_query(year, month, include_reserved).all()

        dispatched_count = 0
        reserved_count = 0
        total_items_sold = 0
        total_revenue = Decimal("0.00")
        total_cost = Decimal("0.00")

        for order in orders:
            if order.status == "DISPATCHED":
                dispatched_count += 1
            elif order.status == "RESERVED":
                reserved_count += 1

            for item in order.items:
                qty = item.quantity
                unit_price = item.unit_price
                purchase_price = item.product.purchase_price if item.product else Decimal("0.00")

                total_items_sold += qty
                total_revenue += Decimal(qty) * unit_price
                total_cost += Decimal(qty) * purchase_price

        total_gross_profit = total_revenue - total_cost
        avg_margin = (
            (total_gross_profit / total_revenue * Decimal("100.00")).quantize(Decimal("0.01"))
            if total_revenue > Decimal("0.00")
            else Decimal("0.00")
        )

        relevant_orders_count = dispatched_count + (reserved_count if include_reserved else 0)
        avg_order_value = (
            (total_revenue / Decimal(relevant_orders_count)).quantize(Decimal("0.01"))
            if relevant_orders_count > 0
            else Decimal("0.00")
        )

        return FinancialSummary(
            period_label=self._get_period_label(year, month),
            year=year,
            month=month,
            total_dispatched_orders=dispatched_count,
            total_reserved_orders=reserved_count,
            total_items_sold=total_items_sold,
            total_revenue=total_revenue.quantize(Decimal("0.01")),
            total_cost=total_cost.quantize(Decimal("0.01")),
            total_gross_profit=total_gross_profit.quantize(Decimal("0.01")),
            average_margin_percentage=avg_margin,
            average_order_value=avg_order_value,
        )

    def get_monthly_category_turnover(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        include_reserved: bool = False,
    ) -> List[CategoryTurnoverItem]:
        """
        Vypočte měsíční obrat po kategoriích.
        Vzhledem k M:N vazbě může tatáž prodaná hračka spadat do více kategorií současně
        (např. Buková káča patří do 'Pro batolata' i 'Dárky do 500 Kč').
        """
        all_categories = self.db.query(Category).order_by(Category.name.asc()).all()
        orders = self._filter_orders_query(year, month, include_reserved).all()

        # Příprava akumulátorů pro každou kategorii
        cat_stats: Dict[UUID, dict] = {
            cat.id: {
                "category_id": cat.id,
                "category_name": cat.name,
                "items_sold_count": 0,
                "order_ids": set(),
                "total_revenue": Decimal("0.00"),
                "total_cost": Decimal("0.00"),
            }
            for cat in all_categories
        }

        # Agregace přes položky relevantních objednávek
        for order in orders:
            for item in order.items:
                product = item.product
                if not product:
                    continue

                qty = item.quantity
                revenue = Decimal(qty) * item.unit_price
                cost = Decimal(qty) * product.purchase_price

                # Přiřazení ke všem kategoriím produktu (M:N vazba)
                for cat in product.categories:
                    if cat.id in cat_stats:
                        cat_stats[cat.id]["items_sold_count"] += qty
                        cat_stats[cat.id]["order_ids"].add(order.id)
                        cat_stats[cat.id]["total_revenue"] += revenue
                        cat_stats[cat.id]["total_cost"] += cost

        # Celkový obrat kategorií pro výpočet procentuálního podílu
        sum_category_revenues = sum(
            stat["total_revenue"] for stat in cat_stats.values()
        )

        results: List[CategoryTurnoverItem] = []
        for cat_id, stat in cat_stats.items():
            revenue = stat["total_revenue"]
            cost = stat["total_cost"]
            profit = revenue - cost

            margin_pct = (
                (profit / revenue * Decimal("100.00")).quantize(Decimal("0.01"))
                if revenue > Decimal("0.00")
                else Decimal("0.00")
            )
            share_pct = (
                (revenue / sum_category_revenues * Decimal("100.00")).quantize(Decimal("0.01"))
                if sum_category_revenues > Decimal("0.00")
                else Decimal("0.00")
            )

            results.append(
                CategoryTurnoverItem(
                    category_id=cat_id,
                    category_name=stat["category_name"],
                    items_sold_count=stat["items_sold_count"],
                    orders_count=len(stat["order_ids"]),
                    total_revenue=revenue.quantize(Decimal("0.01")),
                    total_cost=cost.quantize(Decimal("0.01")),
                    gross_profit=profit.quantize(Decimal("0.01")),
                    margin_percentage=margin_pct,
                    revenue_share_percentage=share_pct,
                )
            )

        # Seřazení kategorií sestupně podle celkového obratu
        results.sort(key=lambda x: x.total_revenue, reverse=True)
        return results

    def get_top_selling_products(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        limit: int = 10,
        include_reserved: bool = False,
    ) -> List[TopSellingProductItem]:
        """Vrátí žebříček nejprodávanějších dřevěných hraček za vybrané období."""
        orders = self._filter_orders_query(year, month, include_reserved).all()

        prod_stats: Dict[UUID, dict] = {}
        for order in orders:
            for item in order.items:
                product = item.product
                if not product:
                    continue

                if product.id not in prod_stats:
                    prod_stats[product.id] = {
                        "product": product,
                        "units_sold": 0,
                        "total_revenue": Decimal("0.00"),
                        "total_cost": Decimal("0.00"),
                    }

                qty = item.quantity
                prod_stats[product.id]["units_sold"] += qty
                prod_stats[product.id]["total_revenue"] += Decimal(qty) * item.unit_price
                prod_stats[product.id]["total_cost"] += Decimal(qty) * product.purchase_price

        items: List[TopSellingProductItem] = []
        for p_id, stat in prod_stats.items():
            product = stat["product"]
            revenue = stat["total_revenue"]
            cost = stat["total_cost"]
            profit = revenue - cost
            margin_pct = (
                (profit / revenue * Decimal("100.00")).quantize(Decimal("0.01"))
                if revenue > Decimal("0.00")
                else Decimal("0.00")
            )

            cat_names = [c.name for c in product.categories]

            items.append(
                TopSellingProductItem(
                    product_id=p_id,
                    product_code=product.code,
                    product_name=product.name,
                    category_names=cat_names,
                    units_sold=stat["units_sold"],
                    total_revenue=revenue.quantize(Decimal("0.01")),
                    total_cost=cost.quantize(Decimal("0.01")),
                    gross_profit=profit.quantize(Decimal("0.01")),
                    margin_percentage=margin_pct,
                )
            )

        # Řazení: nejvíce prodaných kusů, poté tržby
        items.sort(key=lambda x: (x.units_sold, x.total_revenue), reverse=True)
        return items[:limit]

    def get_restock_recommendations(self) -> List[RestockRecommendationItem]:
        """
        Automatická analýza zásob a doporučení k doobjednání / plánování výroby (ADR 1).
        Vyhodnocuje centrální expediční sklad v Hradci Králové a sezónní garáž v Třebechovicích.
        """
        hk_warehouse = self.db.query(Warehouse).filter(Warehouse.code == "WH-HK").first()
        treb_warehouse = self.db.query(Warehouse).filter(Warehouse.code == "WH-TREB").first()

        hk_id = str(hk_warehouse.id) if hk_warehouse else ""
        treb_id = str(treb_warehouse.id) if treb_warehouse else ""

        products = self.db.query(Product).filter(Product.is_active == True).all()
        recommendations: List[RestockRecommendationItem] = []

        for prod in products:
            # Zjištění stavu v jednotlivých skladech
            hk_stock = next((s for s in prod.stocks if hk_warehouse and s.warehouse_id == hk_warehouse.id), None)
            treb_stock = next((s for s in prod.stocks if treb_warehouse and s.warehouse_id == treb_warehouse.id), None)

            hk_avail = hk_stock.available_quantity if hk_stock else 0
            treb_avail = treb_stock.available_quantity if treb_stock else 0
            total_avail = prod.total_available_quantity
            min_stock = prod.min_stock_level

            # Podmínka k dořešení: zásoba celkem pod minimem NEBO na centrále v HK pod minimem
            needs_attention = (total_avail < min_stock) or (hk_avail < min_stock)
            if not needs_attention:
                continue

            # Vyhodnocení vhodné akce podle ADR 1
            if hk_avail < min_stock and treb_avail > 0:
                # V HK chybí, ale v garáži je zásoba
                if total_avail >= min_stock:
                    # Celkově dostatek – čistý převoz ze sezónní garáže
                    rec_qty = min(treb_avail, (min_stock * 2) - hk_avail)
                    action_type = RestockActionType.TRANSFER_FROM_GARAGE
                    action_title = "Doporučen převoz z garáže Třebechovice"
                    action_desc = (
                        f"Na centrále v Hradci Králové zbývá pouze {hk_avail} ks (minimum: {min_stock} ks). "
                        f"V sezónní garáži v Třebechovicích je skladem {treb_avail} volných kusů. "
                        f"Doporučeno převézt {rec_qty} ks na centrálu (ADR 1)."
                    )
                    direct_url = (
                        f"/movements/new?movement_type=transfer&product_id={prod.id}"
                        f"&source_warehouse_id={treb_id}&destination_warehouse_id={hk_id}&quantity={rec_qty}"
                    )
                else:
                    # Chybí i celkově – částečný převoz a zbytek zadat do výroby
                    transfer_qty = treb_avail
                    produce_qty = max((min_stock * 2) - total_avail, 5)
                    action_type = RestockActionType.TRANSFER_AND_PRODUCE
                    action_title = "Kombinace: Převoz z garáže + zadání výroby"
                    action_desc = (
                        f"Převézt všech {transfer_qty} ks z garáže do HK a současně zadat výrobu "
                        f"dalších {produce_qty} ks v truhlářské dílně (celkem chybí do bezpečné zásoby)."
                    )
                    direct_url = (
                        f"/movements/new?movement_type=transfer&product_id={prod.id}"
                        f"&source_warehouse_id={treb_id}&destination_warehouse_id={hk_id}&quantity={transfer_qty}"
                    )
                    rec_qty = produce_qty
            else:
                # V garáži nic není nebo chybí celkově – zadat do truhlárny
                target_stock = max(min_stock * 2, 10)
                rec_qty = max(target_stock - total_avail, 5)
                action_type = RestockActionType.PRODUCE_IN_WORKSHOP
                action_title = "Zadat výrobu v truhlárně / Doobjednat"
                action_desc = (
                    f"Zásoby jsou pod minimem ({total_avail} ks z {min_stock} ks) a garáž je prázdná. "
                    f"Doporučeno zařadit do výrobního plánu truhlárny dávku {rec_qty} ks."
                )
                direct_url = (
                    f"/movements/new?movement_type=receipt&product_id={prod.id}"
                    f"&destination_warehouse_id={hk_id}&quantity={rec_qty}"
                )

            # Stanovení naléhavosti (Urgency)
            if total_avail <= 0 or hk_avail <= 0:
                urgency = RestockUrgency.CRITICAL
            elif total_avail < (min_stock // 2) or hk_avail < (min_stock // 2):
                urgency = RestockUrgency.HIGH
            else:
                urgency = RestockUrgency.MEDIUM

            recommendations.append(
                RestockRecommendationItem(
                    product_id=prod.id,
                    product_code=prod.code,
                    product_name=prod.name,
                    min_stock_level=min_stock,
                    total_physical=prod.total_physical_quantity,
                    total_reserved=prod.total_reserved_quantity,
                    total_available=total_avail,
                    hk_available=hk_avail,
                    treb_available=treb_avail,
                    recommended_quantity=rec_qty,
                    action_type=action_type,
                    action_title=action_title,
                    action_description=action_desc,
                    urgency=urgency,
                    direct_action_url=direct_url,
                )
            )

        # Řazení: CRITICAL první, HIGH druhé, MEDIUM třetí, poté podle deficitu
        urgency_order = {RestockUrgency.CRITICAL: 0, RestockUrgency.HIGH: 1, RestockUrgency.MEDIUM: 2}
        recommendations.sort(
            key=lambda r: (urgency_order[r.urgency], r.total_available - r.min_stock_level)
        )
        return recommendations

    def get_comprehensive_report(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        include_reserved: bool = False,
    ) -> ComprehensiveReportResponse:
        """Vytvoří kompletní manažerský přehled spojující souhrny, obraty, top produkty a restock."""
        summary = self.get_financial_summary(year, month, include_reserved)
        categories = self.get_monthly_category_turnover(year, month, include_reserved)
        top_products = self.get_top_selling_products(year, month, limit=10, include_reserved=include_reserved)
        restock = self.get_restock_recommendations()

        return ComprehensiveReportResponse(
            summary=summary,
            categories=categories,
            top_products=top_products,
            restock_recommendations=restock,
        )
