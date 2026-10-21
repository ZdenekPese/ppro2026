import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryBase(BaseModel):
    """Základní atributy kategorie dřevěných hraček."""
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Název kategorie (např. Pro batolata, Dárky do 500 Kč)",
    )
    description: Optional[str] = Field(
        None,
        description="Detailnější popis zaměření kategorie",
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Název kategorie nesmí být prázdný.")
        return clean


class CategoryCreate(CategoryBase):
    """Schéma pro vytvoření nové kategorie."""
    pass


class CategoryUpdate(BaseModel):
    """Schéma pro úpravu existující kategorie."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            raise ValueError("Název kategorie nesmí být prázdný.")
        return clean


class CategoryResponse(CategoryBase):
    """Schéma pro vrácení detailu kategorie."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
