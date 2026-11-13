from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.infrastructure.db.models import User, UserSession


class UserRepository:
    """Repozitář pro správu uživatelů a autentizačních relací."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        return self.db.scalar(stmt)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.db.scalar(stmt)

    def list_all(self) -> List[User]:
        stmt = select(User).order_by(User.full_name.asc())
        return list(self.db.scalars(stmt).all())

    def create(self, user: User) -> User:
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            raise

    def create_session(self, session_obj: UserSession) -> UserSession:
        try:
            self.db.add(session_obj)
            self.db.commit()
            self.db.refresh(session_obj)
            return session_obj
        except Exception:
            self.db.rollback()
            raise

    def get_active_session_by_token_hash(self, token_hash: str) -> Optional[UserSession]:
        now = datetime.now(timezone.utc)
        stmt = select(UserSession).where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > now,
        )
        return self.db.scalar(stmt)

    def delete_session_by_token_hash(self, token_hash: str) -> None:
        try:
            stmt = delete(UserSession).where(UserSession.token_hash == token_hash)
            self.db.execute(stmt)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def delete_expired_sessions(self) -> None:
        try:
            now = datetime.now(timezone.utc)
            stmt = delete(UserSession).where(UserSession.expires_at <= now)
            self.db.execute(stmt)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
