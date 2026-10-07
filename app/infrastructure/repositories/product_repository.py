from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Product


class ProductRepository:
    """Repozitář pro přístup k produktovým datům v databázi PostgreSQL."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Product]:
        """Získání seznamu produktů s volitelným fulltextovým vyhledáváním a filtrem aktivity."""
        stmt = select(Product)

        if is_active is not None:
            stmt = stmt.where(Product.is_active == is_active)

        if search:
            search_term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Product.name.ilike(search_term),
                    Product.code.ilike(search_term),
                    Product.description.ilike(search_term),
                )
            )

        stmt = stmt.order_by(Product.name.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, product_id: UUID) -> Optional[Product]:
        """Vyhledání produktu podle primárního klíče (UUID)."""
        return self.db.get(Product, product_id)

    def get_by_code(self, code: str) -> Optional[Product]:
        """Vyhledání produktu podle unikátního skladového kódu (SKU)."""
        stmt = select(Product).where(Product.code == code.strip().upper())
        return self.db.scalars(stmt).first()

    def create(self, product: Product) -> Product:
        """Vložení nového produktu do databáze."""
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update(self, product: Product) -> Product:
        """Uložení změn existujícího produktu."""
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, product: Product) -> None:
        """Fyzické smazání produktu (pokud na něj nejsou vázány zásoby)."""
        self.db.delete(product)
        self.db.commit()
