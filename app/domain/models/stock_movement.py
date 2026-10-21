import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class StockMovementType(str, Enum):
    """Typ skladového pohybu."""
    RECEIPT = "receipt"                  # Příjem zboží do skladu (z výroby / od dodavatele)
    DISPATCH = "dispatch"                # Výdej zboží (expedice zákazníkovi)
    TRANSFER = "transfer"                # Vnitroskladový přesun (např. Třebechovice -> HK)
    INVENTORY_ADJUSTMENT = "inventory_adjustment"  # Inventurní dorovnání rozdílu (přebytek / manko)


class StockReceiptCreate(BaseModel):
    """Příjem zboží na sklad."""
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0, description="Počet přijímaných kusů (musí být kladný)")
    note: Optional[str] = Field(None, max_length=500, description="Poznámka / dodací list")
    reference_code: Optional[str] = Field(None, max_length=100, description="Číslo dokladu / dodacího listu")


class StockDispatchCreate(BaseModel):
    """Výdej zboží ze skladu."""
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0, description="Počet vydávaných kusů (musí být kladný)")
    note: Optional[str] = Field(None, max_length=500, description="Důvod výdeje")
    reference_code: Optional[str] = Field(None, max_length=100, description="Číslo objednávky")


class StockTransferCreate(BaseModel):
    """Vnitroskladový přesun mezi sklady (např. Garáž Třebechovice -> Hradec Králové)."""
    source_warehouse_id: uuid.UUID = Field(..., description="Zdrojový sklad (odkud)")
    destination_warehouse_id: uuid.UUID = Field(..., description="Cílový sklad (kam)")
    product_id: uuid.UUID
    quantity: int = Field(..., gt=0, description="Počet převážených kusů")
    note: Optional[str] = Field(None, max_length=500, description="Důvod přesunu / řidič")
    reference_code: Optional[str] = Field(None, max_length=100, description="Číslo převodky")


class InventoryAdjustmentCreate(BaseModel):
    """Inventurní vyrovnání skladu (vyřešení nesrovnalosti v garáži či HK)."""
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    actual_quantity: int = Field(..., ge=0, description="Skutečně nalezený fyzický stav kusů")
    note: str = Field(..., min_length=3, max_length=500, description="Povinné zdůvodnění rozdílu z inventury")


class StockMovementResponse(BaseModel):
    """Detail zaznamenaného skladového pohybu pro auditní stopu."""
    id: uuid.UUID
    product_id: uuid.UUID
    product_code: str
    product_name: str
    source_warehouse_id: Optional[uuid.UUID] = None
    source_warehouse_code: Optional[str] = None
    source_warehouse_name: Optional[str] = None
    destination_warehouse_id: Optional[uuid.UUID] = None
    destination_warehouse_code: Optional[str] = None
    destination_warehouse_name: Optional[str] = None
    movement_type: str
    quantity: int
    note: Optional[str] = None
    reference_code: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
