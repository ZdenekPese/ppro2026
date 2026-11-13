from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.domain.exceptions import AuthenticationError
from app.domain.models.auth import LoginRequest, UserResponse
from app.domain.services.auth_service import AuthService
from app.presentation.dependencies import get_current_user_optional

router = APIRouter(prefix="/auth", tags=["Autentizace"])


@router.post("/login", response_model=UserResponse)
def api_login(
    dto: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Přihlášení přes REST API s nastavením HttpOnly cookie relace."""
    auth_service = AuthService(db)
    try:
        user = auth_service.authenticate(dto.username, dto.password)
        raw_token = auth_service.create_session(user)
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=raw_token,
            httponly=True,
            samesite="lax",
            max_age=settings.SESSION_TTL_HOURS * 3600,
            path="/",
        )
        return user
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def api_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Odhlášení a zrušení aktuální relace."""
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    AuthService(db).logout(raw_token)
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def api_me(
    request: Request,
    db: Session = Depends(get_db),
):
    """Vrátí profil aktuálně přihlášeného uživatele a jeho roli."""
    user = get_current_user_optional(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Uživatel není přihlášen.",
        )
    return user
