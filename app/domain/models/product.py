from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductBase(BaseModel):
    """Základní atributy dřevěné hračky."""
    code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Unikátní skladový SKU kód hračky (např. KAC-001)",
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Název hračky",
    )
    description: Optional[str] = Field(
        None,
        description="Detailní popis hračky",
    )
    purchase_price: Decimal = Field(
        ...,
        ge=0,
        description="Nákupní / výrobní cena bez DPH v Kč (nesmí být záporná)",
    )
    selling_price: Decimal = Field(
        ...,
        ge=0,
        description="Výchozí prodejní cena v Kč (nesmí být záporná)",
    )
    min_stock_level: int = Field(
        default=5,
        ge=0,
        description="Minimální doporučená skladová zásoba",
    )
    is_active: bool = Field(
        default=True,
        description="Zda je produkt aktivní v nabídce",
    )

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        clean_code = v.strip().upper()
        if not clean_code:
            raise ValueError("Kód produktu nesmí být prázdný.")
        return clean_code

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        clean_name = v.strip()
        if not clean_name:
            raise ValueError("Název produktu nesmí být prázdný.")
        return clean_name


class ProductCreate(ProductBase):
    """Schéma pro vytvoření nového produktu."""
    pass


class ProductUpdate(BaseModel):
    """Schéma pro úpravu existujícího produktu."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    purchase_price: Optional[Decimal] = Field(None, ge=0)
    selling_price: Optional[Decimal] = Field(None, ge=0)
    min_stock_level: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Schéma pro vrácení detailu produktu."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
