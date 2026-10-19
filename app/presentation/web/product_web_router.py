from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.database import get_db
from app.domain.exceptions import DuplicateProductCodeError, ProductNotFoundError, InvalidPriceError
from app.domain.models.product import ProductCreate, ProductUpdate
from app.domain.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Web Produkty"])

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_service(db: Session = Depends(get_db)) -> ProductService:
    return ProductService(db)


@router.get("", response_class=HTMLResponse)
def product_list_view(
    request: Request,
    search: Optional[str] = None,
    service: ProductService = Depends(get_service),
):
    """Zobrazení katalogu dřevěných hraček v přehledné tabulce."""
    products = service.list_products(search=search)
    total_products = len(products)
    active_products = sum(1 for p in products if p.is_active)
    avg_price = (sum(p.selling_price for p in products) / total_products) if total_products > 0 else Decimal("0.00")
    avg_margin = (sum(p.selling_price - p.purchase_price for p in products) / total_products) if total_products > 0 else Decimal("0.00")

    return templates.TemplateResponse(
        request=request,
        name="product_list.html",
        context={
            "products": products,
            "search": search or "",
            "title": "Katalog hraček - Dřevěnka s.r.o.",
            "total_products": total_products,
            "active_products": active_products,
            "avg_price": avg_price,
            "avg_margin": avg_margin,
        },
    )



@router.get("/new", response_class=HTMLResponse)
def product_create_view(request: Request):
    """Zobrazení formuláře pro přidání nové dřevěné hračky."""
    return templates.TemplateResponse(
        request=request,
        name="product_form.html",
        context={
            "product": None,
            "title": "Přidat novou hračku - Dřevěnka s.r.o.",
            "error": None,
        },
    )


@router.post("/new", response_class=HTMLResponse)
def product_create_submit(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    purchase_price: Decimal = Form(...),
    selling_price: Decimal = Form(...),
    min_stock_level: int = Form(5),
    service: ProductService = Depends(get_service),
):
    """Zpracování formuláře pro přidání hračky."""
    try:
        dto = ProductCreate(
            code=code,
            name=name,
            description=description,
            purchase_price=purchase_price,
            selling_price=selling_price,
            min_stock_level=min_stock_level,
        )
        service.create_product(dto)
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)
    except (DuplicateProductCodeError, InvalidPriceError, ValueError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="product_form.html",
            context={
                "product": {
                    "code": code,
                    "name": name,
                    "description": description,
                    "purchase_price": purchase_price,
                    "selling_price": selling_price,
                    "min_stock_level": min_stock_level,
                },
                "title": "Přidat novou hračku - Chyba",
                "error": str(exc),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


@router.get("/{product_id}/edit", response_class=HTMLResponse)
def product_edit_view(
    request: Request,
    product_id: UUID,
    service: ProductService = Depends(get_service),
):
    """Zobrazení formuláře pro editaci hračky."""
    try:
        product = service.get_product(product_id)
        return templates.TemplateResponse(
            request=request,
            name="product_form.html",
            context={
                "product": product,
                "title": f"Upravit: {product.name}",
                "error": None,
            },
        )
    except ProductNotFoundError:
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{product_id}/edit", response_class=HTMLResponse)
def product_edit_submit(
    request: Request,
    product_id: UUID,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    purchase_price: Decimal = Form(...),
    selling_price: Decimal = Form(...),
    min_stock_level: int = Form(5),
    is_active: bool = Form(False),
    service: ProductService = Depends(get_service),
):
    """Uložení upraveného produktu."""
    try:
        dto = ProductUpdate(
            name=name,
            description=description,
            purchase_price=purchase_price,
            selling_price=selling_price,
            min_stock_level=min_stock_level,
            is_active=is_active,
        )
        service.update_product(product_id, dto)
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)
    except (InvalidPriceError, ValueError) as exc:
        product = service.get_product(product_id)
        return templates.TemplateResponse(
            request=request,
            name="product_form.html",
            context={
                "product": product,
                "title": f"Upravit: {name} - Chyba",
                "error": str(exc),
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
