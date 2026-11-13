import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    """Uživatelské role v systému Dřevěnka s.r.o. dle zadání."""
    MANAGER = "manager"      # Jednatel / Manažer (Petr Doležal) – plný přístup včetně ceníku a reportů
    WAREHOUSE = "warehouse"  # Skladník – příjem, výdej, převody, inventura, objednávky, zákazníci


class LoginRequest(BaseModel):
    """Přihlašovací požadavek."""
    username: str = Field(..., min_length=2, max_length=60)
    password: str = Field(..., min_length=1, max_length=255)


class UserCreate(BaseModel):
    """Schéma pro založení uživatelského účtu."""
    username: str = Field(..., min_length=2, max_length=60)
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=255)
    role: UserRole = UserRole.WAREHOUSE
    password: str = Field(..., min_length=6, max_length=255)


class UserResponse(BaseModel):
    """Veřejný profil přihlášeného uživatele (bez citlivých údajů)."""
    id: uuid.UUID
    username: str
    full_name: str
    email: str
    role: str
    role_label: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
