import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    """Základní schéma pro zákazníka e-shopu Dřevěnka s.r.o."""
    first_name: str = Field(..., min_length=1, max_length=100, description="Křestní jméno zákazníka")
    last_name: str = Field(..., min_length=1, max_length=100, description="Příjmení zákazníka")
    email: str = Field(..., min_length=3, max_length=255, description="E-mailový kontakt")
    phone: Optional[str] = Field(None, max_length=50, description="Telefonní kontakt")
    address: str = Field(..., min_length=3, max_length=500, description="Doručovací adresa zákazníka")


class CustomerCreate(CustomerBase):
    """Schéma pro založení nového zákazníka."""
    pass


class CustomerUpdate(BaseModel):
    """Schéma pro úpravu údajů existujícího zákazníka."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, min_length=3, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, min_length=3, max_length=500)
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    """Detail zákazníka v odpovědi API."""
    id: uuid.UUID
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    orders_count: int = 0

    model_config = ConfigDict(from_attributes=True)
