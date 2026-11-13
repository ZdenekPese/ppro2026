from pathlib import Path
from urllib.parse import quote
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.core.config import settings
from app.presentation.dependencies import ForbiddenWebException, NotAuthenticatedWebException
from app.presentation.api.auth_router import router as auth_router
from app.presentation.api.health_router import router as health_router
from app.presentation.api.product_router import router as product_router
from app.presentation.api.category_router import router as category_router
from app.presentation.api.warehouse_router import router as warehouse_router
from app.presentation.api.stock_movement_router import router as stock_movement_router
from app.presentation.api.customer_router import router as customer_router
from app.presentation.api.order_router import router as order_router
from app.presentation.api.report_router import router as report_router
from app.presentation.web.auth_web_router import router as auth_web_router
from app.presentation.web.customer_portal_web_router import router as customer_portal_web_router
from app.presentation.web.product_web_router import router as product_web_router
from app.presentation.web.dashboard_web_router import router as dashboard_web_router
from app.presentation.web.stock_movement_web_router import router as stock_movement_web_router
from app.presentation.web.order_web_router import router as order_web_router
from app.presentation.web.report_web_router import router as report_web_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Informační systém skladu pro e-shop Dřevěnka s.r.o. (Semestrální projekt PPRO 2026/2027)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Cesty pro statické soubory a šablony
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "presentation" / "static"
TEMPLATES_DIR = BASE_DIR / "presentation" / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Vrací výchozí favicon ikonu webu pro prohlížeče."""
    return FileResponse(STATIC_DIR / "favicon.ico", media_type="image/x-icon")


@app.exception_handler(NotAuthenticatedWebException)
def not_authenticated_web_handler(request: Request, exc: NotAuthenticatedWebException):
    """Přesměruje nepřihlášeného uživatele na přihlašovací obrazovku."""
    next_param = quote(exc.next_url, safe="/?=&")
    target = f"/login?next={next_param}" if exc.next_url and exc.next_url != "/" else "/login"
    return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)


@app.exception_handler(ForbiddenWebException)
def forbidden_web_handler(request: Request, exc: ForbiddenWebException):
    """Zobrazí přehlednou stránku 403 při nedostatečné uživatelské roli."""
    return templates.TemplateResponse(
        request=request,
        name="403.html",
        context={
            "required_role": exc.required_role,
            "message": exc.message,
            "title": "Přístup omezen",
        },
        status_code=status.HTTP_403_FORBIDDEN,
    )


# Registrace API routerů
app.include_router(auth_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(product_router, prefix="/api")
app.include_router(category_router, prefix="/api")
app.include_router(warehouse_router, prefix="/api")
app.include_router(stock_movement_router, prefix="/api")
app.include_router(customer_router, prefix="/api")
app.include_router(order_router, prefix="/api")
app.include_router(report_router, prefix="/api")

# Registrace webových routerů
app.include_router(auth_web_router)
app.include_router(customer_portal_web_router)
app.include_router(dashboard_web_router)
app.include_router(product_web_router)
app.include_router(stock_movement_web_router)
app.include_router(order_web_router)
app.include_router(report_web_router)


