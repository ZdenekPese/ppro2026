from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.exceptions import AuthenticationError, DuplicateUsernameError
from app.domain.models.auth import UserCreate
from app.infrastructure.db.models import User, UserSession
from app.infrastructure.repositories.user_repository import UserRepository


def hash_password(password: str) -> str:
    """Zahashuje heslo pomocí nativního scrypt s náhodnou solí."""
    salt = secrets.token_hex(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )
    return f"scrypt${salt}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Bezpečné ověření hesla proti uloženému scrypt hashi v konstantním čase."""
    try:
        algorithm, salt, expected_hex = stored_hash.split("$", 2)
    except ValueError:
        return False

    if algorithm != "scrypt":
        return False

    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )
    return hmac.compare_digest(derived.hex(), expected_hex)


def hash_session_token(raw_token: str) -> str:
    """SHA-256 otisk relačního tokenu ukládaný do databáze."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class AuthService:
    """Aplikační služba pro autentizaci pracovníků a správu relací."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def authenticate(self, username: str, password: str) -> User:
        """Ověří přihlašovací údaje uživatele a vrátí entitu User."""
        clean_username = username.strip().lower()
        user = self.user_repo.get_by_username(clean_username)
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Neplatné uživatelské jméno nebo heslo.")

        if not user.is_active:
            raise AuthenticationError("Tento uživatelský účet byl deaktivován.")

        return user

    def create_session(self, user: User, ttl_hours: Optional[int] = None) -> str:
        """Vytvoří novou databázovou relaci a vrátí surový token pro HttpOnly cookie."""
        hours = ttl_hours if ttl_hours is not None else settings.SESSION_TTL_HOURS
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_session_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

        session_obj = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.user_repo.create_session(session_obj)
        return raw_token

    def get_user_by_session_token(self, raw_token: Optional[str]) -> Optional[User]:
        """Načte aktivního uživatele podle tokenu z cookie."""
        if not raw_token:
            return None
        token_hash = hash_session_token(raw_token)
        session_obj = self.user_repo.get_active_session_by_token_hash(token_hash)
        if not session_obj or not session_obj.user or not session_obj.user.is_active:
            return None
        return session_obj.user

    def logout(self, raw_token: Optional[str]) -> None:
        """Zruší existující relaci uživatele v databázi."""
        if not raw_token:
            return
        token_hash = hash_session_token(raw_token)
        self.user_repo.delete_session_by_token_hash(token_hash)

    def create_user(self, dto: UserCreate) -> User:
        """Založí nového pracovníka systému se zahashovaným heslem."""
        clean_username = dto.username.strip().lower()
        if self.user_repo.get_by_username(clean_username):
            raise DuplicateUsernameError(clean_username)

        user = User(
            username=clean_username,
            full_name=dto.full_name.strip(),
            email=dto.email.strip().lower(),
            role=dto.role.value,
            password_hash=hash_password(dto.password),
            is_active=True,
        )
        return self.user_repo.create(user)
