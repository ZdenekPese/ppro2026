import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OrderStatus(str, Enum):
    """Stavy životního cyklu objednávky."""
    NEW = "NEW"                    # Nově přijatá objednávka
    RESERVED = "RESERVED"          # Zboží úspěšně zarezervováno v centrálním skladu (ochrana před přeprodejem)
    DISPATCHED = "DISPATCHED"      # Objednávka fyzicky expedována, uvolněna rezervace, fyzický odpis
    CANCELLED = "CANCELLED"        # Stornováno, uvolněna rezervace


class OrderItemCreate(BaseModel):
    """Položka objednávky při jejím vytváření."""
    product_id: uuid.UUID = Field(..., description="ID objednávaného produktu")
    quantity: int = Field(..., gt=0, description="Objednaný počet kusů (kladné celé číslo)")
    unit_price: Optional[Decimal] = Field(
        None,
        ge=Decimal(0),
        description="Fixovaná prodejní cena (pokud není zadána, převezme se aktuální cena produktu z katalogu)",
    )


class OrderCreate(BaseModel):
    """Schéma pro vytvoření nové objednávky z e-shopu."""
    customer_id: uuid.UUID = Field(..., description="ID zákazníka")
    warehouse_id: Optional[uuid.UUID] = Field(
        None,
        description="Expediční sklad (pokud není zadán, použije se centrální sklad Hradec Králové)",
    )
    order_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Volitelné vlastní číslo objednávky (pokud chybí, vygeneruje se automaticky)",
    )
    note: Optional[str] = Field(None, max_length=500, description="Poznámka k objednávce")
    items: List[OrderItemCreate] = Field(..., min_length=1, description="Seznam položek v objednávce")


class OrderItemResponse(BaseModel):
    """Detail položky objednávky v odpovědi API."""
    id: uuid.UUID
    product_id: uuid.UUID
    product_code: str
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    """Kompletní detail objednávky."""
    id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID
    customer_name: str
    customer_email: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    status: str
    total_price: Decimal
    note: Optional[str] = None
    created_at: datetime
    dispatched_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []
    can_dispatch: bool = False
    can_cancel: bool = False
    requires_transfer_from_garage: bool = False

    model_config = ConfigDict(from_attributes=True)
