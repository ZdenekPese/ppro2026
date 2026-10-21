from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.exceptions import CategoryNotFoundError, DuplicateCategoryNameError
from app.domain.models.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.domain.services.category_service import CategoryService
from app.infrastructure.repositories.category_repository import CategoryRepository

router = APIRouter(prefix="/categories", tags=["Kategorie (Katalog)"])


def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    """Dependency injection pro CategoryService."""
    repo = CategoryRepository(db)
    return CategoryService(repo)


@router.get("", response_model=List[CategoryResponse])
def list_categories(
    search: Optional[str] = Query(None, description="Hledat podle názvu nebo popisu"),
    service: CategoryService = Depends(get_category_service),
):
    """Získání seznamu všech kategorií dřevěných hraček."""
    return service.list_categories(search=search)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: UUID,
    service: CategoryService = Depends(get_category_service),
):
    """Detail konkrétní kategorie."""
    try:
        return service.get_category_by_id(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    dto: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
):
    """Vytvoření nové kategorie dřevěných hraček."""
    try:
        return service.create_category(dto)
    except DuplicateCategoryNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    dto: CategoryUpdate,
    service: CategoryService = Depends(get_category_service),
):
    """Úprava existující kategorie."""
    try:
        return service.update_category(category_id, dto)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DuplicateCategoryNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    service: CategoryService = Depends(get_category_service),
):
    """Smazání kategorie."""
    try:
        service.delete_category(category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
