import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class WarehouseBase(BaseModel):
    """Základní atributy skladu."""
    code: str = Field(
        ...,
        min_length=2,
        max_length=20,
        description="Unikátní kód skladu (např. WH-HK, WH-TREB)",
    )
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Název skladu",
    )
    location: Optional[str] = Field(
        None,
        max_length=255,
        description="Adresa / upřesnění lokace skladu",
    )
    is_primary: bool = Field(
        default=False,
        description="Zda jde o primární sklad pro běžnou expedici",
    )

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean:
            raise ValueError("Kód skladu nesmí být prázdný.")
        return clean

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Název skladu nesmí být prázdný.")
        return clean


class WarehouseCreate(WarehouseBase):
    """Schéma pro vytvoření nového skladu."""
    pass


class WarehouseUpdate(BaseModel):
    """Schéma pro úpravu skladu."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    is_primary: Optional[bool] = None


class WarehouseResponse(WarehouseBase):
    """Schéma detailu skladu."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseStockBase(BaseModel):
    """Základní atributy skladové zásoby."""
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    physical_quantity: int = Field(default=0, ge=0, description="Fyzický počet kusů na polici")
    reserved_quantity: int = Field(default=0, ge=0, description="Počet kusů blokovaných v objednávkách")


class WarehouseStockUpdate(BaseModel):
    """Úprava skladové zásoby."""
    physical_quantity: Optional[int] = Field(None, ge=0)
    reserved_quantity: Optional[int] = Field(None, ge=0)


class WarehouseStockResponse(WarehouseStockBase):
    """Detail skladové zásoby položky na konkrétním skladě."""
    id: uuid.UUID
    available_quantity: int = Field(description="Disponibilní zásoba (fyzická - rezervovaná)")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductStockDetail(BaseModel):
    """Skladová data jednoho produktu rozpadlá po skladech."""
    product_id: uuid.UUID
    product_code: str
    product_name: str
    min_stock_level: int
    selling_price: Decimal
    purchase_price: Decimal
    is_active: bool
    stocks: Dict[str, WarehouseStockResponse] = Field(
        default_factory=dict,
        description="Zásoby indexované kódem skladu (např. 'WH-HK', 'WH-TREB')",
    )
    total_physical: int = 0
    total_reserved: int = 0
    total_available: int = 0
    status: str = "ok"  # 'danger' (pod minimem), 'warning' (blízko minima), 'ok' (dostatek)
    is_below_min: bool = False


class WarehouseInventorySummary(BaseModel):
    """Souhrn za jeden sklad."""
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    is_primary: bool
    total_items_count: int
    total_value: Decimal


class DashboardSummary(BaseModel):
    """Kompletní přehled dashboardu pro majitele e-shopu Petra Doležala."""
    total_products_count: int
    total_physical_count: int
    total_reserved_count: int
    total_available_count: int
    total_stock_value: Decimal
    critical_items_count: int
    warehouses: List[WarehouseInventorySummary]
    critical_items: List[ProductStockDetail]
