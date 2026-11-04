from decimal import Decimal
from pathlib import Path
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.exceptions import (
    CustomerNotFoundError,
    InsufficientStockError,
    InvalidOrderStatusError,
    OrderNotFoundError,
    ProductNotFoundError,
)
from app.domain.models.customer import CustomerCreate
from app.domain.models.order import OrderCreate, OrderItemCreate
from app.domain.services.customer_service import CustomerService
from app.domain.services.order_service import OrderService
from app.infrastructure.repositories.customer_repository import CustomerRepository
from app.infrastructure.repositories.product_repository import ProductRepository
from app.infrastructure.repositories.warehouse_repository import WarehouseRepository

router = APIRouter(tags=["Web Objednávky a Zákazníci"])

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    return OrderService(db)


def get_customer_service(db: Session = Depends(get_db)) -> CustomerService:
    return CustomerService(db)


@router.get("/orders", response_class=HTMLResponse)
def orders_list_view(
    request: Request,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    service: OrderService = Depends(get_order_service),
):
    """Webový přehled všech objednávek."""
    clean_status = status_filter.strip() if status_filter and status_filter.strip() else None
    orders = service.list_orders(status=clean_status, search=search)
    all_orders = service.list_orders()

    count_all = len(all_orders)
    count_reserved = sum(1 for o in all_orders if o.status == "RESERVED")
    count_dispatched = sum(1 for o in all_orders if o.status == "DISPATCHED")
    count_cancelled = sum(1 for o in all_orders if o.status == "CANCELLED")

    return templates.TemplateResponse(
        request=request,
        name="orders.html",
        context={
            "orders": orders,
            "status_filter": status_filter,
            "search": search or "",
            "count_all": count_all,
            "count_reserved": count_reserved,
            "count_dispatched": count_dispatched,
            "count_cancelled": count_cancelled,
            "title": "Správa objednávek e-shopu - Dřevěnka s.r.o.",
        },
    )


@router.get("/orders/new", response_class=HTMLResponse)
def order_new_view(
    request: Request,
    db: Session = Depends(get_db),
):
    """Formulář pro vytvoření nové e-shopové objednávky."""
    customers = CustomerRepository(db).list_all(only_active=True)
    products = ProductRepository(db).list_all(is_active=True)
    warehouses = WarehouseRepository(db).list_all()

    return templates.TemplateResponse(
        request=request,
        name="order_form.html",
        context={
            "customers": customers,
            "products": products,
            "warehouses": warehouses,
            "error": None,
            "title": "Nová objednávka - Dřevěnka s.r.o.",
        },
    )


@router.post("/orders/new", response_class=HTMLResponse)
def order_new_submit(
    request: Request,
    customer_mode: str = Form(...),  # 'existing' nebo 'new'
    existing_customer_id: Optional[UUID] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    warehouse_id: Optional[UUID] = Form(None),
    note: Optional[str] = Form(None),
    product_id_1: UUID = Form(...),
    quantity_1: int = Form(...),
    product_id_2: Optional[UUID] = Form(None),
    quantity_2: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    order_service: OrderService = Depends(get_order_service),
    customer_service: CustomerService = Depends(get_customer_service),
):
    """Zpracování založení objednávky s automatickou rezervací."""
    try:
        # Získání nebo vytvoření zákazníka
        if customer_mode == "existing" and existing_customer_id:
            cust_id = existing_customer_id
        else:
            if not first_name or not last_name or not email or not address:
                raise ValueError("Vyplňte prosím všechny povinné údaje zákazníka (jméno, příjmení, e-mail a adresu).")
            new_cust = customer_service.create_customer(
                CustomerCreate(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    address=address,
                )
            )
            cust_id = new_cust.id

        # Sestavení položek objednávky
        items = [OrderItemCreate(product_id=product_id_1, quantity=quantity_1)]
        if product_id_2 and quantity_2 and quantity_2 > 0:
            items.append(OrderItemCreate(product_id=product_id_2, quantity=quantity_2))

        dto = OrderCreate(
            customer_id=cust_id,
            warehouse_id=warehouse_id,
            note=note,
            items=items,
        )
        saved = order_service.create_order(dto)
        return RedirectResponse(url=f"/orders/{saved.id}", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as exc:
        customers = CustomerRepository(db).list_all(only_active=True)
        products = ProductRepository(db).list_all(is_active=True)
        warehouses = WarehouseRepository(db).list_all()
        return templates.TemplateResponse(
            request=request,
            name="order_form.html",
            context={
                "customers": customers,
                "products": products,
                "warehouses": warehouses,
                "error": str(exc),
                "title": "Chyba při vytváření objednávky",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


@router.get("/orders/{order_id}", response_class=HTMLResponse)
def order_detail_view(
    request: Request,
    order_id: UUID,
    success: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    service: OrderService = Depends(get_order_service),
):
    """Detail konkrétní objednávky s možností expedice a storna."""
    try:
        order = service.get_order_response(order_id)
        return templates.TemplateResponse(
            request=request,
            name="order_detail.html",
            context={
                "order": order,
                "success": success,
                "error": error,
                "title": f"Objednávka {order.order_number} - Dřevěnka s.r.o.",
            },
        )
    except OrderNotFoundError:
        return RedirectResponse(url="/orders", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/orders/{order_id}/dispatch", response_class=HTMLResponse)
def order_dispatch_submit(
    request: Request,
    order_id: UUID,
    service: OrderService = Depends(get_order_service),
):
    """Zpracování expedice objednávky skladníkem."""
    try:
        service.dispatch_order(order_id)
        return RedirectResponse(
            url=f"/orders/{order_id}?success=Objednávka+byla+úspěšně+expedována+a+položky+byly+odepsány+ze+skladu.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"/orders/{order_id}?error={str(exc)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.post("/orders/{order_id}/cancel", response_class=HTMLResponse)
def order_cancel_submit(
    request: Request,
    order_id: UUID,
    service: OrderService = Depends(get_order_service),
):
    """Zpracování storna objednávky."""
    try:
        service.cancel_order(order_id)
        return RedirectResponse(
            url=f"/orders/{order_id}?success=Objednávka+byla+stornována+a+rezervované+kusy+byly+uvolněny+zpět+do+prodeje.",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:
        return RedirectResponse(
            url=f"/orders/{order_id}?error={str(exc)}",
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.get("/customers", response_class=HTMLResponse)
def customers_list_view(
    request: Request,
    search: Optional[str] = None,
    service: CustomerService = Depends(get_customer_service),
):
    """Zobrazení adresáře zákazníků."""
    customers = service.list_customers(search=search)
    return templates.TemplateResponse(
        request=request,
        name="customers.html",
        context={
            "customers": customers,
            "search": search or "",
            "title": "Adresář zákazníků - Dřevěnka s.r.o.",
        },
    )
