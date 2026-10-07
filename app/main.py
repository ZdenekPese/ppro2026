from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.presentation.api.health_router import router as health_router

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


@app.get("/", response_class=HTMLResponse, tags=["Web"])
def home_page(request: Request):
    """Úvodní stránka skladového systému."""
    return templates.TemplateResponse(
        request=request,
        name="base.html",
        context={"title": "Sklad Dřevěnka s.r.o. - Úvod"},
    )

