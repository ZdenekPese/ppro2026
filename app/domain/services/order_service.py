from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.domain.exceptions import (
    CustomerNotFoundError,
    InsufficientStockError,
    InvalidOrderStatusError,
    OrderNotFoundError,
    ProductNotFoundError,
    WarehouseNotFoundError,
)
from app.domain.models.order import (
    OrderCreate,
    OrderItemResponse,
    OrderResponse,
    OrderStatus,
)
from app.domain.models.stock_movement import StockMovementType
from app.infrastructure.db.models import Order, OrderItem, StockMovement
from app.infrastructure.repositories.customer_repository import CustomerRepository
from app.infrastructure.repositories.order_repository import OrderRepository
from app.infrastructure.repositories.product_repository import ProductRepository
from app.infrastructure.repositories.stock_movement_repository import StockMovementRepository
from app.infrastructure.repositories.warehouse_repository import WarehouseRepository
from app.infrastructure.repositories.warehouse_stock_repository import WarehouseStockRepository


class OrderService:
    """Aplikační služba pro správu objednávek a nákupního procesu (Fáze 6)."""

    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.warehouse_repo = WarehouseRepository(db)
        self.product_repo = ProductRepository(db)
        self.stock_repo = WarehouseStockRepository(db)
        self.movement_repo = StockMovementRepository(db)

    def _format_order(self, order: Order) -> OrderResponse:
        """Převedení ORM entity Order na kompletní DTO odpověď."""
        items_dto: List[OrderItemResponse] = []
        requires_transfer = False

        # Zjištění, zda v expedičním skladě něco nechybí pro expedici
        for it in order.items:
            prod = it.product
            code = prod.code if prod else "N/A"
            name = prod.name if prod else "Neznámý produkt"
            
            items_dto.append(
                OrderItemResponse(
                    id=it.id,
                    product_id=it.product_id,
                    product_code=code,
                    product_name=name,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    total_price=it.total_price,
                )
            )

            # Kontrola fyzické dostupnosti na expedičním skladě
            if order.status == OrderStatus.RESERVED.value:
                stock = self.stock_repo.get_by_warehouse_and_product(order.warehouse_id, it.product_id)
                if not stock or stock.physical_quantity < it.quantity:
                    requires_transfer = True

        can_dispatch = order.status in (OrderStatus.RESERVED.value, OrderStatus.NEW.value)
        can_cancel = order.status in (OrderStatus.RESERVED.value, OrderStatus.NEW.value)

        return OrderResponse(
            id=order.id,
            order_number=order.order_number,
            customer_id=order.customer_id,
            customer_name=order.customer.full_name if order.customer else "Neznámý zákazník",
            customer_email=order.customer.email if order.customer else "",
            warehouse_id=order.warehouse_id,
            warehouse_code=order.warehouse.code if order.warehouse else "",
            warehouse_name=order.warehouse.name if order.warehouse else "",
            status=order.status,
            total_price=order.total_price,
            note=order.note,
            created_at=order.created_at,
            dispatched_at=order.dispatched_at,
            items=items_dto,
            can_dispatch=can_dispatch,
            can_cancel=can_cancel,
            requires_transfer_from_garage=requires_transfer,
        )

    def list_orders(
        self,
        status: Optional[str] = None,
        customer_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[OrderResponse]:
        """Získání seznamu objednávek s filtry."""
        orders = self.order_repo.list_all(
            status=status,
            customer_id=customer_id,
            warehouse_id=warehouse_id,
            search=search,
            limit=limit,
        )
        return [self._format_order(o) for o in orders]

    def get_order(self, order_id: UUID) -> Order:
        """Získání ORM entity objednávky s kontrolou existence."""
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFoundError(str(order_id))
        return order

    def get_order_response(self, order_id: UUID) -> OrderResponse:
        """Získání DTO detailu objednávky."""
        order = self.get_order(order_id)
        return self._format_order(order)

    def create_order(self, dto: OrderCreate) -> OrderResponse:
        """
        Vytvoření nové objednávky z e-shopu s okamžitou rezervací kusů.
        Splňuje pravidla:
        1. Neměnnost ceny: cena se fixuje v položkách v čase nákupu.
        2. Okamžitá rezervace: zabrání přeprodeji zboží.
        3. Řešení Garáže Třebechovice (ADR 1): pokud je celkový stav napříč sklady dostatečný.
        """
        customer = self.customer_repo.get_by_id(dto.customer_id)
        if not customer:
            raise CustomerNotFoundError(str(dto.customer_id))

        # Expediční sklad: buď zadaný, nebo výchozí primární (Centrální sklad HK)
        if dto.warehouse_id:
            warehouse = self.warehouse_repo.get_by_id(dto.warehouse_id)
            if not warehouse:
                raise WarehouseNotFoundError(str(dto.warehouse_id))
        else:
            warehouse = self.warehouse_repo.get_primary()
            if not warehouse:
                warehouses = self.warehouse_repo.list_all()
                if not warehouses:
                    raise WarehouseNotFoundError("V systému není evidován žádný sklad.")
                warehouse = warehouses[0]

        # Validace a příprava položek
        order_number = dto.order_number or self.order_repo.generate_next_order_number()
        total_price = Decimal("0.00")
        order_items: List[OrderItem] = []

        # Kontrola a rezervace zásob
        for item_dto in dto.items:
            product = self.product_repo.get_by_id(item_dto.product_id)
            if not product:
                raise ProductNotFoundError(str(item_dto.product_id))

            # Fixace prodejní ceny v čase nákupu (neměnnost ceny)
            price = item_dto.unit_price if item_dto.unit_price is not None else product.selling_price
            order_items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=item_dto.quantity,
                    unit_price=price,
                )
            )
            total_price += Decimal(item_dto.quantity) * price

            # Kontrola disponibilní zásoby v expedičním skladu
            stock = self.stock_repo.get_or_create(warehouse.id, product.id)
            avail_in_wh = stock.available_quantity

            if avail_in_wh < item_dto.quantity:
                # Zjištění celkové disponibilní zásoby napříč všemi sklady (ADR 1)
                total_avail = product.total_available_quantity
                if total_avail < item_dto.quantity:
                    raise InsufficientStockError(available=total_avail, requested=item_dto.quantity)

                # Celkově zboží máme, ale část je v sezónní garáži -> zarezervujeme dostupné v HK, zbytek v garáži
                qty_to_reserve = item_dto.quantity
                reserve_in_wh = min(avail_in_wh, qty_to_reserve)
                if reserve_in_wh > 0:
                    stock.reserved_quantity += reserve_in_wh
                    self.stock_repo.update(stock)
                    qty_to_reserve -= reserve_in_wh

                # Zbývající část rezervujeme v ostatních skladech (např. v garáži)
                if qty_to_reserve > 0:
                    for other_wh in self.warehouse_repo.list_all():
                        if other_wh.id == warehouse.id:
                            continue
                        other_stock = self.stock_repo.get_or_create(other_wh.id, product.id)
                        other_avail = other_stock.available_quantity
                        if other_avail > 0:
                            take = min(other_avail, qty_to_reserve)
                            other_stock.reserved_quantity += take
                            self.stock_repo.update(other_stock)
                            qty_to_reserve -= take
                            if qty_to_reserve == 0:
                                break
            else:
                # Plná rezervace v expedičním skladu
                stock.reserved_quantity += item_dto.quantity
                self.stock_repo.update(stock)

        # Založení objednávky ve stavu RESERVED
        order = Order(
            order_number=order_number,
            customer_id=customer.id,
            warehouse_id=warehouse.id,
            status=OrderStatus.RESERVED.value,
            total_price=total_price,
            note=dto.note,
            items=order_items,
        )
        saved = self.order_repo.create(order)
        return self._format_order(saved)

    def dispatch_order(self, order_id: UUID, performed_by: Optional[str] = None) -> OrderResponse:
        """
        Fyzická expedice objednávky:
        1. Ověření stavu (lze expedovat pouze rezervovanou/novou).
        2. Fyzický odpis z regálu a uvolnění rezervace.
        3. Vytvoření auditního záznamu StockMovement (typ dispatch) pro každou položku.
        4. Přepnutí objednávky do stavu DISPATCHED.
        """
        order = self.get_order(order_id)
        if order.status not in (OrderStatus.RESERVED.value, OrderStatus.NEW.value):
            raise InvalidOrderStatusError(
                order.status,
                OrderStatus.DISPATCHED.value,
                reason="Lze expedovat pouze otevřenou či rezervovanou objednávku.",
            )

        # Provedení fyzického odpisu a vytvoření pohybů
        for item in order.items:
            stock = self.stock_repo.get_or_create(order.warehouse_id, item.product_id)
            if stock.physical_quantity < item.quantity:
                raise InsufficientStockError(
                    available=stock.physical_quantity,
                    requested=item.quantity,
                )

            # Odpis z regálu a uvolnění rezervace
            stock.physical_quantity -= item.quantity
            stock.reserved_quantity = max(0, stock.reserved_quantity - item.quantity)
            self.stock_repo.update(stock)

            # Auditní záznam pohybu (Zadání B: 100% dohledatelnost)
            movement = StockMovement(
                product_id=item.product_id,
                source_warehouse_id=order.warehouse_id,
                destination_warehouse_id=None,
                movement_type=StockMovementType.DISPATCH.value,
                quantity=item.quantity,
                reference_code=order.order_number,
                note=f"Expedice e-shop objednávky č. {order.order_number} zákazníkovi {order.customer.full_name}",
                performed_by=performed_by,
            )
            self.movement_repo.create(movement)

        order.status = OrderStatus.DISPATCHED.value
        order.dispatched_at = datetime.now()
        saved = self.order_repo.update(order)
        return self._format_order(saved)

    def cancel_order(self, order_id: UUID) -> OrderResponse:
        """
        Storno objednávky:
        Uvolnění zablokovaných rezervací v regálech zpět do volného prodeje.
        """
        order = self.get_order(order_id)
        if order.status == OrderStatus.DISPATCHED.value:
            raise InvalidOrderStatusError(
                order.status,
                OrderStatus.CANCELLED.value,
                reason="Již fyzicky expedovanou a odeslanou objednávku nelze stornovat.",
            )

        if order.status != OrderStatus.CANCELLED.value:
            # Uvolnění rezervací
            for item in order.items:
                stock = self.stock_repo.get_or_create(order.warehouse_id, item.product_id)
                stock.reserved_quantity = max(0, stock.reserved_quantity - item.quantity)
                self.stock_repo.update(stock)

            order.status = OrderStatus.CANCELLED.value
            saved = self.order_repo.update(order)
            return self._format_order(saved)

        return self._format_order(order)
