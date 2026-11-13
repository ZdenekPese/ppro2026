from typing import Optional
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.domain.models.auth import UserRole
from app.domain.services.auth_service import AuthService
from app.infrastructure.db.models import User


class NotAuthenticatedWebException(Exception):
    """Vyvoláno při přístupu nepřihlášeného uživatele na chráněnou webovou stránku."""

    def __init__(self, next_url: str = "/"):
        self.next_url = next_url


class ForbiddenWebException(Exception):
    """Vyvoláno při přístupu uživatele s nedostatečnou rolí."""

    def __init__(self, required_role: str, message: str):
        self.required_role = required_role
        self.message = message


def sanitize_next_url(next_url: Optional[str]) -> str:
    """Povolí pouze interní relativní cesty začínající '/' (ochrana před open-redirect)."""
    if not next_url:
        return "/"
    candidate = next_url.strip()
    if (
        not candidate.startswith("/")
        or candidate.startswith("//")
        or "\\" in candidate
        or candidate.startswith("/login")
        or candidate.startswith("/logout")
    ):
        return "/"
    return candidate


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Načte přihlášeného uživatele z cookie relace, nebo vrátí None."""
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    user = AuthService(db).get_user_by_session_token(raw_token)
    request.state.user = user
    return user


def require_web_user(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Vyžaduje platné přihlášení uživatele; jinak přesměruje na přihlašovací obrazovku."""
    if current_user is None:
        target = request.url.path
        if request.url.query:
            target = f"{target}?{request.url.query}"
        raise NotAuthenticatedWebException(next_url=sanitize_next_url(target))
    return current_user


def require_staff_user(
    current_user: User = Depends(require_web_user),
) -> User:
    """Vyžaduje interní roli zaměstnance (Jednatel / Manažer nebo Skladník)."""
    if current_user.role not in (UserRole.MANAGER.value, UserRole.WAREHOUSE.value):
        raise ForbiddenWebException(
            required_role="Zaměstnanec skladu (Jednatel nebo Skladník)",
            message="Tato interní skladová sekce je dostupná pouze zaměstnancům firmy Dřevěnka s.r.o. Zákazníci mají k dispozici e-shop a přehled vlastních objednávek.",
        )
    return current_user


def require_customer_user(
    current_user: User = Depends(require_web_user),
) -> User:
    """Vyžaduje zákaznický účet navázaný na evidovaného zákazníka."""
    if current_user.role != UserRole.CUSTOMER.value or not current_user.customer_id:
        raise ForbiddenWebException(
            required_role="Zákazník",
            message="Tato sekce je určena pouze pro přihlášené zákazníky e-shopu Dřevěnka s.r.o.",
        )
    return current_user


def require_manager_user(
    current_user: User = Depends(require_web_user),
) -> User:
    """Vyžaduje roli Jednatel / Manažer (např. pro finanční reporty a ceník produktů)."""
    if current_user.role != UserRole.MANAGER.value:
        raise ForbiddenWebException(
            required_role="Jednatel / Manažer",
            message="Tato sekce je vyhrazena pro vedení firmy (Jednatel / Manažer). Role Skladník má přístup ke skladové operativě, pohybům a expedici objednávek.",
        )
    return current_user
