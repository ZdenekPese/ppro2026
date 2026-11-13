from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.exceptions import (
    InsufficientStockError,
    InvalidOrderStatusError,
    OrderNotFoundError,
    ProductNotFoundError,
)
from app.domain.models.auth import UserRole
from app.domain.models.order import OrderCreate, OrderItemCreate
from app.domain.services.customer_service import CustomerService
from app.domain.services.order_service import OrderService
from app.domain.services.product_service import ProductService
from app.infrastructure.db.models import User
from app.infrastructure.repositories.category_repository import CategoryRepository
from app.presentation.dependencies import (
    ForbiddenWebException,
    require_customer_user,
    require_web_user,
)
from app.presentation.utils import parse_optional_uuid

router = APIRouter(tags=["Web Zákaznický portál"])

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def resolve_product_image(code: str, name: str = "") -> str:
    """Namapuje SKU kód nebo název hračky na ilustrační obrázek v /static/img/toys/."""
    upper_code = (code or "").upper()
    lower_name = (name or "").lower()

    exact_code_map = {
        "KAC-001": "spinning_top.svg",
        "KAC-002": "duck.svg",
        "AUT-003": "firetruck.svg",
        "HLV-001": "hedgehog_cage.svg",
        "HLV-002": "puzzle_tower.svg",
        "HLV-003": "puzzle_board.svg",
    }
    if upper_code in exact_code_map:
        return f"/static/img/toys/{exact_code_map[upper_code]}"

    prefix_map = {
        "VLK": "train.svg",
        "KON": "rocking_horse.svg",
        "KOS": "blocks.svg",
        "AUT": "car.svg",
        "DOM": "domino.svg",
        "PUZ": "puzzle_board.svg",
        "LET": "airplane.svg",
        "LOD": "sailboat.svg",
        "MECH": "woodpecker.svg",
        "HUD": "xylophone.svg",
        "LOU": "theater.svg",
    }
    prefix = upper_code.split("-")[0] if "-" in upper_code else upper_code
    if prefix in prefix_map:
        return f"/static/img/toys/{prefix_map[prefix]}"

    keyword_map = [
        (("vláč", "vlák", "lokomotiv"), "train.svg"),
        (("kačer", "kachn"), "duck.svg"),
        (("káč",), "spinning_top.svg"),
        (("koník", "kůň", "houpací"), "rocking_horse.svg"),
        (("kostk", "staveb"), "blocks.svg"),
        (("hasič",), "firetruck.svg"),
        (("aut", "náklaď", "voz"), "car.svg"),
        (("ježek", "klec"), "hedgehog_cage.svg"),
        (("věž", "krouž"), "puzzle_tower.svg"),
        (("domino",), "domino.svg"),
        (("puzzle", "tangram", "vklád"), "puzzle_board.svg"),
        (("letad", "dvouploš"), "airplane.svg"),
        (("loď", "plachetn"), "sailboat.svg"),
        (("datel", "slepič", "klap"), "woodpecker.svg"),
        (("xylofon", "rumba", "hudeb"), "xylophone.svg"),
        (("loutk", "divad"), "theater.svg"),
    ]
    for keywords, filename in keyword_map:
        if any(kw in lower_name for kw in keywords):
            return f"/static/img/toys/{filename}"

    return "/static/img/toys/default_toy.svg"


def _render_shop(
    request: Request,
    db: Session,
    current_user: User,
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    only_in_stock: bool = False,
    order_error: Optional[str] = None,
    submitted_quantities: Optional[Dict[str, int]] = None,
    note_value: str = "",
    status_code: int = status.HTTP_200_OK,
):
    clean_category_id = parse_optional_uuid(category_id)
    product_service = ProductService(db)
    products = product_service.list_products(
        search=search,
        is_active=True,
        category_id=clean_category_id,
    )
    categories = CategoryRepository(db).list_all()

    shop_items = []
    for prod in products:
        avail = max(0, prod.total_available_quantity)
        if only_in_stock and avail <= 0:
            continue

        if avail <= 0:
            avail_state = "out"
            avail_label = "Dočasně vyprodáno"
        elif avail <= prod.min_stock_level:
            avail_state = "low"
            avail_label = f"Poslední kusy ({avail} ks)"
        else:
            avail_state = "ok"
            avail_label = f"Skladem ({avail} ks)"

        prefill_qty = 0
        if submitted_quantities and str(prod.id) in submitted_quantities:
            prefill_qty = submitted_quantities[str(prod.id)]

        shop_items.append(
            {
                "id": prod.id,
                "code": prod.code,
                "name": prod.name,
                "description": prod.description,
                "selling_price": prod.selling_price,
                "categories": prod.categories,
                "available_quantity": avail,
                "avail_state": avail_state,
                "avail_label": avail_label,
                "prefill_qty": prefill_qty,
                "image_url": resolve_product_image(prod.code, prod.name),
            }
        )

    customer_profile = None
    if current_user.customer_id:
        try:
            customer_profile = CustomerService(db).get_customer_response(current_user.customer_id)
        except Exception:
            customer_profile = None

    return templates.TemplateResponse(
        request=request,
        name="shop.html",
        context={
            "items": shop_items,
            "categories": categories,
            "selected_category_id": clean_category_id,
            "search": search or "",
            "only_in_stock": only_in_stock,
            "customer_profile": customer_profile,
            "is_customer_role": current_user.role == UserRole.CUSTOMER.value,
            "order_error": order_error,
            "note_value": note_value,
            "title": "E-shop dřevěných hraček - Dřevěnka s.r.o.",
        },
        status_code=status_code,
    )


@router.get("/shop", response_class=HTMLResponse)
def shop_catalog_view(
    request: Request,
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    only_in_stock: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_web_user),
):
    """Veřejný katalog pro přihlášené zákazníky (pouze prodejní ceny a dostupnost bez nákupních marží)."""
    return _render_shop(
        request=request,
        db=db,
        current_user=current_user,
        search=search,
        category_id=category_id,
        only_in_stock=only_in_stock,
    )


@router.post("/shop/order", response_class=HTMLResponse)
async def shop_order_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer_user),
):
    """Založení zákaznické objednávky s okamžitou rezervací zásob a fixací prodejních cen."""
    form_data = await request.form()
    note_raw = str(form_data.get("note") or "").strip()

    order_items: List[OrderItemCreate] = []
    submitted_quantities: Dict[str, int] = {}

    try:
        for key, raw_val in form_data.items():
            if not key.startswith("qty_"):
                continue
            pid_str = key[4:]
            val_str = str(raw_val or "").strip()
            if not val_str:
                continue
            qty = int(val_str)
            if qty < 0:
                raise ValueError("Množství v košíku nesmí být záporné.")
            if qty > 0:
                pid = UUID(pid_str)
                submitted_quantities[str(pid)] = qty
                order_items.append(OrderItemCreate(product_id=pid, quantity=qty))
    except ValueError as exc:
        return _render_shop(
            request=request,
            db=db,
            current_user=current_user,
            order_error=f"Neplatně zadané množství položek: {exc}",
            submitted_quantities=submitted_quantities,
            note_value=note_raw,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if not order_items:
        return _render_shop(
            request=request,
            db=db,
            current_user=current_user,
            order_error="Vyberte prosím alespoň jednu hračku s množstvím větším než 0 ks.",
            submitted_quantities=submitted_quantities,
            note_value=note_raw,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Předběžná kontrola celkové dostupnosti pro všechny položky najednou (atomické odmítnutí bez dílčí rezervace)
    product_service = ProductService(db)
    try:
        for item in order_items:
            product = product_service.get_product(item.product_id)
            if not product.is_active:
                raise ValueError(f"Hračka '{product.name}' momentálně není v nabídce e-shopu.")
            total_avail = product.total_available_quantity
            if total_avail < item.quantity:
                raise InsufficientStockError(available=total_avail, requested=item.quantity)

        dto = OrderCreate(
            customer_id=current_user.customer_id,
            warehouse_id=None,
            note=note_raw or None,
            items=order_items,
        )
        created_order = OrderService(db).create_order(dto)
        return RedirectResponse(
            url=f"/my-orders/{created_order.id}?created=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except (InsufficientStockError, ProductNotFoundError, ValueError) as exc:
        return _render_shop(
            request=request,
            db=db,
            current_user=current_user,
            order_error=str(exc),
            submitted_quantities=submitted_quantities,
            note_value=note_raw,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


@router.get("/my-orders", response_class=HTMLResponse)
def my_orders_list_view(
    request: Request,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer_user),
):
    """Seznam objednávek přihlášeného zákazníka (vlastní historie a stav expedice)."""
    clean_status = status_filter.strip() if status_filter and status_filter.strip() else None
    orders = OrderService(db).list_orders(
        status=clean_status,
        customer_id=current_user.customer_id,
    )

    reserved_count = sum(1 for o in orders if o.status in ("RESERVED", "NEW"))
    dispatched_count = sum(1 for o in orders if o.status == "DISPATCHED")
    total_spent = sum((o.total_price for o in orders if o.status != "CANCELLED"), Decimal("0.00"))

    return templates.TemplateResponse(
        request=request,
        name="my_orders.html",
        context={
            "orders": orders,
            "selected_status": clean_status or "",
            "reserved_count": reserved_count,
            "dispatched_count": dispatched_count,
            "total_spent": total_spent,
            "title": "Moje objednávky - Dřevěnka s.r.o.",
        },
    )


@router.get("/my-orders/{order_id}", response_class=HTMLResponse)
def my_order_detail_view(
    request: Request,
    order_id: UUID,
    created: Optional[str] = None,
    cancelled: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer_user),
):
    """Detail vlastní zákaznické objednávky s fixovanou cenou a možností storna před expedicí."""
    try:
        order = OrderService(db).get_order_response(order_id)
    except OrderNotFoundError:
        return RedirectResponse(url="/my-orders", status_code=status.HTTP_303_SEE_OTHER)

    if order.customer_id != current_user.customer_id:
        raise ForbiddenWebException(
            required_role="Vlastník objednávky",
            message="Nemáte oprávnění prohlížet objednávky jiných zákazníků.",
        )

    customer = CustomerService(db).get_customer_response(current_user.customer_id)
    item_images = {
        str(it.product_id): resolve_product_image(it.product_code, it.product_name)
        for it in order.items
    }

    return templates.TemplateResponse(
        request=request,
        name="my_order_detail.html",
        context={
            "order": order,
            "customer": customer,
            "item_images": item_images,
            "created": created,
            "cancelled": cancelled,
            "error": error,
            "title": f"Moje objednávka {order.order_number} - Dřevěnka s.r.o.",
        },
    )


@router.post("/my-orders/{order_id}/cancel")
def my_order_cancel_submit(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer_user),
):
    """Storno vlastní neexpedované objednávky zákazníkem (uvolní rezervaci ve skladu)."""
    order_service = OrderService(db)
    try:
        order = order_service.get_order_response(order_id)
    except OrderNotFoundError:
        return RedirectResponse(url="/my-orders", status_code=status.HTTP_303_SEE_OTHER)

    if order.customer_id != current_user.customer_id:
        raise ForbiddenWebException(
            required_role="Vlastník objednávky",
            message="Nemáte oprávnění stornovat objednávku jiného zákazníka.",
        )

    try:
        order_service.cancel_order(order_id)
        return RedirectResponse(
            url=f"/my-orders/{order_id}?cancelled=1",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except InvalidOrderStatusError as exc:
        from urllib.parse import quote
        return RedirectResponse(
            url=f"/my-orders/{order_id}?error={quote(str(exc), safe='')}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
