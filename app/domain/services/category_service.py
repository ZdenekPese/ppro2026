from typing import List, Optional
from uuid import UUID

from app.domain.exceptions import CategoryNotFoundError, DuplicateCategoryNameError
from app.domain.models.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.infrastructure.db.models import Category
from app.infrastructure.repositories.category_repository import CategoryRepository


class CategoryService:
    """Aplikační služba pro správu kategorií dřevěných hraček."""

    def __init__(self, category_repo: CategoryRepository):
        self.category_repo = category_repo

    def list_categories(self, search: Optional[str] = None) -> List[CategoryResponse]:
        """Vrátí seznam všech kategorií splňujících vyhledávací kritérium."""
        categories = self.category_repo.list_all(search=search)
        return [CategoryResponse.model_validate(cat) for cat in categories]

    def get_category_by_id(self, category_id: UUID) -> CategoryResponse:
        """Vrátí detail konkrétní kategorie nebo vyvolá CategoryNotFoundError."""
        category = self.category_repo.get_by_id(category_id)
        if not category:
            raise CategoryNotFoundError(str(category_id))
        return CategoryResponse.model_validate(category)

    def create_category(self, data: CategoryCreate) -> CategoryResponse:
        """Vytvoří novou kategorii po ověření unikátnosti názvu."""
        existing = self.category_repo.get_by_name(data.name)
        if existing:
            raise DuplicateCategoryNameError(data.name)

        new_category = Category(
            name=data.name,
            description=data.description,
        )
        saved = self.category_repo.create(new_category)
        return CategoryResponse.model_validate(saved)

    def update_category(self, category_id: UUID, data: CategoryUpdate) -> CategoryResponse:
        """Upraví existující kategorii po ověření existence a unikátnosti názvu."""
        category = self.category_repo.get_by_id(category_id)
        if not category:
            raise CategoryNotFoundError(str(category_id))

        if data.name is not None and data.name != category.name:
            existing = self.category_repo.get_by_name(data.name)
            if existing and existing.id != category_id:
                raise DuplicateCategoryNameError(data.name)
            category.name = data.name

        if data.description is not None:
            category.description = data.description

        saved = self.category_repo.update(category)
        return CategoryResponse.model_validate(saved)

    def delete_category(self, category_id: UUID) -> None:
        """Smaže kategorii (vazby v asociační tabulce se odstraní kaskádově)."""
        category = self.category_repo.get_by_id(category_id)
        if not category:
            raise CategoryNotFoundError(str(category_id))
        self.category_repo.delete(category)
