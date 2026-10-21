from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.presentation.api.health_router import router as health_router
from app.presentation.api.product_router import router as product_router
from app.presentation.api.category_router import router as category_router
from app.presentation.api.warehouse_router import router as warehouse_router
from app.presentation.api.stock_movement_router import router as stock_movement_router
from app.presentation.web.product_web_router import router as product_web_router
from app.presentation.web.dashboard_web_router import router as dashboard_web_router
from app.presentation.web.stock_movement_web_router import router as stock_movement_web_router

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

# Registrace API routerů
app.include_router(health_router, prefix="/api")
app.include_router(product_router, prefix="/api")
app.include_router(category_router, prefix="/api")
app.include_router(warehouse_router, prefix="/api")
app.include_router(stock_movement_router, prefix="/api")

# Registrace webových routerů
app.include_router(dashboard_web_router)
app.include_router(product_web_router)
app.include_router(stock_movement_web_router)


