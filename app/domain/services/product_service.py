from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.domain.exceptions import (
    DuplicateProductCodeError,
    ProductNotFoundError,
    InvalidPriceError,
)
from app.domain.models.product import ProductCreate, ProductUpdate
from app.infrastructure.db.models import Product
from app.infrastructure.repositories.product_repository import ProductRepository


class ProductService:
    """Byznys služba pro správu dřevěných hraček a vynucování doménových pravidel."""

    def __init__(self, db: Session):
        self.repository = ProductRepository(db)

    def list_products(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Product]:
        """Získání seznamu produktů dle kritérií."""
        return self.repository.list_all(search=search, is_active=is_active)

    def get_product(self, product_id: UUID) -> Product:
        """Získání detailu produktu s ověřením existence."""
        product = self.repository.get_by_id(product_id)
        if not product:
            raise ProductNotFoundError(str(product_id))
        return product

    def create_product(self, dto: ProductCreate) -> Product:
        """Založení nového produktu s validací obchodních pravidel."""
        # 1. Kontrola unikátnosti kódu SKU
        existing = self.repository.get_by_code(dto.code)
        if existing:
            raise DuplicateProductCodeError(dto.code)

        # 2. Kontrola platnosti a limitů cen
        MAX_PRICE = Decimal("99999999.99")
        if dto.purchase_price < 0:
            raise InvalidPriceError("Nákupní cena nesmí být záporná.", field="purchase_price")
        if dto.purchase_price > MAX_PRICE:
            raise InvalidPriceError("Nákupní cena nesmí překročit 99 999 999,99 Kč.", field="purchase_price")
        if dto.selling_price < 0:
            raise InvalidPriceError("Prodejní cena nesmí být záporná.", field="selling_price")
        if dto.selling_price > MAX_PRICE:
            raise InvalidPriceError("Prodejní cena nesmí překročit 99 999 999,99 Kč.", field="selling_price")

        # 3. Vytvoření ORM entity
        product = Product(
            code=dto.code,
            name=dto.name,
            description=dto.description,
            purchase_price=dto.purchase_price,
            selling_price=dto.selling_price,
            min_stock_level=dto.min_stock_level,
            is_active=dto.is_active,
        )
        return self.repository.create(product)

    def update_product(self, product_id: UUID, dto: ProductUpdate) -> Product:
        """Aktualizace existujícího produktu."""
        product = self.get_product(product_id)

        # Validace cen, pokud se mění
        MAX_PRICE = Decimal("99999999.99")
        if dto.purchase_price is not None:
            if dto.purchase_price < 0:
                raise InvalidPriceError("Nákupní cena nesmí být záporná.", field="purchase_price")
            if dto.purchase_price > MAX_PRICE:
                raise InvalidPriceError("Nákupní cena nesmí překročit 99 999 999,99 Kč.", field="purchase_price")
        if dto.selling_price is not None:
            if dto.selling_price < 0:
                raise InvalidPriceError("Prodejní cena nesmí být záporná.", field="selling_price")
            if dto.selling_price > MAX_PRICE:
                raise InvalidPriceError("Prodejní cena nesmí překročit 99 999 999,99 Kč.", field="selling_price")

        if dto.name is not None:
            product.name = dto.name
        if dto.description is not None:
            product.description = dto.description
        if dto.purchase_price is not None:
            product.purchase_price = dto.purchase_price
        if dto.selling_price is not None:
            product.selling_price = dto.selling_price
        if dto.min_stock_level is not None:
            product.min_stock_level = dto.min_stock_level
        if dto.is_active is not None:
            product.is_active = dto.is_active

        return self.repository.update(product)

    def toggle_active(self, product_id: UUID) -> Product:
        """Přepnutí stavu aktivní/neaktivní (soft toggle)."""
        product = self.get_product(product_id)
        product.is_active = not product.is_active
        return self.repository.update(product)
