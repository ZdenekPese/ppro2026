from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.domain.exceptions import AuthenticationError, DuplicateUsernameError
from app.domain.models.auth import CustomerRegisterRequest, UserRole
from app.domain.services.auth_service import AuthService
from app.presentation.dependencies import get_current_user_optional, sanitize_next_url

router = APIRouter(tags=["Web Autentizace"])

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _login_context(
    *,
    next_url: str,
    username: str = "",
    error: Optional[str] = None,
    logged_out: bool = False,
) -> dict:
    show_demo = settings.APP_ENV == "development" or settings.DEBUG
    return {
        "next_url": next_url,
        "username": username,
        "error": error,
        "logged_out": logged_out,
        "show_demo": show_demo,
        "demo_manager_password": settings.DEMO_MANAGER_PASSWORD if show_demo else "",
        "demo_warehouse_password": settings.DEMO_WAREHOUSE_PASSWORD if show_demo else "",
        "demo_customer_password": settings.DEMO_CUSTOMER_PASSWORD if show_demo else "",
        "title": "Přihlášení do systému",
    }


def _set_session_cookie(response: RedirectResponse, raw_token: str) -> None:
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        samesite="lax",
        max_age=settings.SESSION_TTL_HOURS * 3600,
        path="/",
    )


def _default_home_for_user(role: str, safe_next: str) -> str:
    if role == UserRole.CUSTOMER.value and safe_next == "/":
        return "/shop"
    return safe_next


@router.get("/login", response_class=HTMLResponse)
def login_view(
    request: Request,
    next: Optional[str] = None,
    logged_out: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Zobrazení přihlašovací obrazovky."""
    safe_next = sanitize_next_url(next)
    current_user = get_current_user_optional(request, db)
    if current_user is not None:
        return RedirectResponse(
            url=_default_home_for_user(current_user.role, safe_next),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=_login_context(
            next_url=safe_next,
            logged_out=logged_out in ("1", "true"),
        ),
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Form("/"),
    db: Session = Depends(get_db),
):
    """Zpracování přihlášení a nastavení HttpOnly relační cookie."""
    safe_next = sanitize_next_url(next)
    auth_service = AuthService(db)
    try:
        user = auth_service.authenticate(username=username, password=password)
        raw_token = auth_service.create_session(user)

        target_url = _default_home_for_user(user.role, safe_next)
        response = RedirectResponse(url=target_url, status_code=status.HTTP_303_SEE_OTHER)
        _set_session_cookie(response, raw_token)
        return response
    except AuthenticationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context=_login_context(
                next_url=safe_next,
                username=username,
                error=str(exc),
            ),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


@router.post("/logout")
def logout_submit(
    request: Request,
    db: Session = Depends(get_db),
):
    """Odhlášení uživatele, zrušení relace v DB a smazání cookie."""
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    AuthService(db).logout(raw_token)

    response = RedirectResponse(url="/login?logged_out=1", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/register", response_class=HTMLResponse)
def register_view(
    request: Request,
    db: Session = Depends(get_db),
):
    """Zobrazení samoobslužné registrace nového zákazníka e-shopu."""
    current_user = get_current_user_optional(request, db)
    if current_user is not None:
        return RedirectResponse(
            url=_default_home_for_user(current_user.role, "/"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "form": {},
            "error": None,
            "title": "Registrace zákazníka — Dřevěnka s.r.o.",
        },
    )


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    username: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    """Zpracování registrace zákazníka: vytvoří Customer + User(customer) a rovnou přihlásí."""
    form_values = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "address": address,
    }

    if password != password_confirm:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "form": form_values,
                "error": "Zadaná hesla se neshodují. Zkontrolujte prosím obě pole hesla.",
                "title": "Registrace zákazníka — Chyba",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    auth_service = AuthService(db)
    try:
        dto = CustomerRegisterRequest(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address=address,
            password=password,
        )
        user = auth_service.register_customer_account(dto)
        raw_token = auth_service.create_session(user)

        response = RedirectResponse(url="/shop", status_code=status.HTTP_303_SEE_OTHER)
        _set_session_cookie(response, raw_token)
        return response
    except ValidationError as exc:
        err_msg = "Zkontrolujte prosím zadané údaje (jméno a přihlašovací jméno min. 2 znaky, heslo min. 6 znaků)."
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "form": form_values,
                "error": err_msg,
                "title": "Registrace zákazníka — Chyba",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except (DuplicateUsernameError, ValueError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={
                "form": form_values,
                "error": str(exc),
                "title": "Registrace zákazníka — Chyba",
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
