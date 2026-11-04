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
from app.infrastructure.repositories.category_repository import CategoryRepository
from app.presentation.utils import parse_optional_uuid

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
    category_id: Optional[str] = None,
    db: Session = Depends(get_db),
    service: ProductService = Depends(get_service),
):
    """Zobrazení katalogu dřevěných hraček v přehledné tabulce s filtrem kategorií."""
    clean_category_id = parse_optional_uuid(category_id)
    products = service.list_products(search=search, category_id=clean_category_id)
    cat_repo = CategoryRepository(db)
    categories = cat_repo.list_all()

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
            "categories": categories,
            "selected_category_id": clean_category_id,
            "title": "Katalog hraček - Dřevěnka s.r.o.",
            "total_products": total_products,
            "active_products": active_products,
            "avg_price": avg_price,
            "avg_margin": avg_margin,
            "total_categories": len(categories),
        },
    )


@router.get("/new", response_class=HTMLResponse)
def product_create_view(
    request: Request,
    db: Session = Depends(get_db),
):
    """Zobrazení formuláře pro přidání nové dřevěné hračky včetně výběru kategorií."""
    cat_repo = CategoryRepository(db)
    categories = cat_repo.list_all()
    return templates.TemplateResponse(
        request=request,
        name="product_form.html",
        context={
            "product": None,
            "categories": categories,
            "selected_category_ids": [],
            "title": "Přidat novou hračku - Dřevěnka s.r.o.",
            "error": None,
            "errors": {},
        },
    )



from sqlalchemy.exc import SQLAlchemyError, DataError


def extract_field_errors(exc: Exception) -> dict[str, str]:
    """Mapování výjimek na konkrétní pole formuláře."""
    errors = {}
    if isinstance(exc, InvalidPriceError):
        if exc.field:
            errors[exc.field] = str(exc)
        else:
            errors["selling_price"] = str(exc)
    elif isinstance(exc, DuplicateProductCodeError):
        errors["code"] = str(exc)
    elif isinstance(exc, DataError) or "numeric" in str(exc).lower() or "out of range" in str(exc).lower():
        errors["selling_price"] = "Zadaná částka je příliš vysoká (max. 99 999 999,99 Kč)."
        errors["purchase_price"] = "Zadaná částka je příliš vysoká (max. 99 999 999,99 Kč)."
    else:
        msg = str(exc)
        if "purchase_price" in msg:
            errors["purchase_price"] = "Nákupní cena musí být v rozmezí 0 až 99 999 999,99 Kč."
        if "selling_price" in msg:
            errors["selling_price"] = "Prodejní cena musí být v rozmezí 0 až 99 999 999,99 Kč."
        if "min_stock_level" in msg:
            errors["min_stock_level"] = "Minimální zásoba musí být v rozmezí 0 až 1 000 000 ks."
        if "code" in msg:
            errors["code"] = "Kód SKU musí mít 2 až 50 znaků."
        if "name" in msg:
            errors["name"] = "Název hračky musí mít 2 až 255 znaků."
    return errors


@router.post("/new", response_class=HTMLResponse)
def product_create_submit(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    purchase_price: Decimal = Form(...),
    selling_price: Decimal = Form(...),
    min_stock_level: int = Form(5),
    category_ids: list[UUID] = Form(default=[]),
    db: Session = Depends(get_db),
    service: ProductService = Depends(get_service),
):
    """Zpracování formuláře pro přidání hračky včetně kategorií."""
    cat_repo = CategoryRepository(db)
    all_categories = cat_repo.list_all()
    try:
        dto = ProductCreate(
            code=code,
            name=name,
            description=description,
            purchase_price=purchase_price,
            selling_price=selling_price,
            min_stock_level=min_stock_level,
            category_ids=category_ids,
        )
        service.create_product(dto)
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)
    except (DuplicateProductCodeError, InvalidPriceError, ValueError, SQLAlchemyError) as exc:
        field_errors = extract_field_errors(exc)
        main_error = "Opravte prosím označené chyby u formulářových polí." if field_errors else str(exc)
        if isinstance(exc, (DataError, SQLAlchemyError)) and not isinstance(exc, (DuplicateProductCodeError, InvalidPriceError)):
            main_error = "Zadaná částka je mimo povolený rozsah databáze (max. 99 999 999,99 Kč)."

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
                "categories": all_categories,
                "selected_category_ids": category_ids,
                "title": "Přidat novou hračku - Chyba",
                "error": main_error,
                "errors": field_errors,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


@router.get("/{product_id}/edit", response_class=HTMLResponse)
def product_edit_view(
    request: Request,
    product_id: UUID,
    db: Session = Depends(get_db),
    service: ProductService = Depends(get_service),
):
    """Zobrazení formuláře pro editaci hračky."""
    try:
        product = service.get_product(product_id)
        cat_repo = CategoryRepository(db)
        all_categories = cat_repo.list_all()
        selected_category_ids = [c.id for c in product.categories]
        return templates.TemplateResponse(
            request=request,
            name="product_form.html",
            context={
                "product": product,
                "categories": all_categories,
                "selected_category_ids": selected_category_ids,
                "title": f"Upravit: {product.name}",
                "error": None,
                "errors": {},
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
    category_ids: list[UUID] = Form(default=[]),
    db: Session = Depends(get_db),
    service: ProductService = Depends(get_service),
):
    """Uložení upraveného produktu včetně přiřazených kategorií."""
    cat_repo = CategoryRepository(db)
    all_categories = cat_repo.list_all()
    try:
        dto = ProductUpdate(
            name=name,
            description=description,
            purchase_price=purchase_price,
            selling_price=selling_price,
            min_stock_level=min_stock_level,
            is_active=is_active,
            category_ids=category_ids,
        )
        service.update_product(product_id, dto)
        return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)
    except (InvalidPriceError, ValueError, SQLAlchemyError) as exc:
        field_errors = extract_field_errors(exc)
        main_error = "Opravte prosím označené chyby u cenových polí." if field_errors else str(exc)
        if isinstance(exc, (DataError, SQLAlchemyError)) and not isinstance(exc, InvalidPriceError):
            main_error = "Zadaná částka je mimo povolený rozsah databáze (max. 99 999 999,99 Kč)."

        # Zachováme uživatelem zadané hodnoty ve formuláři
        product_data = {
            "id": product_id,
            "name": name,
            "description": description,
            "purchase_price": purchase_price,
            "selling_price": selling_price,
            "min_stock_level": min_stock_level,
            "is_active": is_active,
        }
        try:
            existing = service.get_product(product_id)
            product_data["code"] = existing.code
        except Exception:
            product_data["code"] = ""

        return templates.TemplateResponse(
            request=request,
            name="product_form.html",
            context={
                "product": product_data,
                "categories": all_categories,
                "selected_category_ids": category_ids,
                "title": f"Upravit: {name} - Chyba",
                "error": main_error,
                "errors": field_errors,
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

