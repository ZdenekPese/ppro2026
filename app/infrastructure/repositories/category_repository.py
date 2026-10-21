from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Category


class CategoryRepository:
    """Repozitář pro přístup ke kategoriím dřevěných hraček v databázi PostgreSQL."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self, search: Optional[str] = None) -> List[Category]:
        """Získání seznamu kategorií s volitelným vyhledáváním dle názvu a popisu."""
        stmt = select(Category)

        if search:
            search_term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Category.name.ilike(search_term),
                    Category.description.ilike(search_term),
                )
            )

        stmt = stmt.order_by(Category.name.asc())
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, category_id: UUID) -> Optional[Category]:
        """Vyhledání kategorie podle primárního klíče (UUID)."""
        return self.db.get(Category, category_id)

    def get_by_ids(self, category_ids: List[UUID]) -> List[Category]:
        """Vyhledání více kategorií podle seznamu UUID."""
        if not category_ids:
            return []
        stmt = select(Category).where(Category.id.in_(category_ids))
        return list(self.db.scalars(stmt).all())

    def get_by_name(self, name: str) -> Optional[Category]:
        """Vyhledání kategorie podle unikátního názvu."""
        stmt = select(Category).where(Category.name == name.strip())
        return self.db.scalars(stmt).first()

    def create(self, category: Category) -> Category:
        """Vložení nové kategorie do databáze."""
        try:
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)
            return category
        except Exception:
            self.db.rollback()
            raise

    def update(self, category: Category) -> Category:
        """Uložení změn existující kategorie."""
        try:
            self.db.commit()
            self.db.refresh(category)
            return category
        except Exception:
            self.db.rollback()
            raise

    def delete(self, category: Category) -> None:
        """Smazání kategorie."""
        try:
            self.db.delete(category)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
