from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.infrastructure.db.health import check_database_connection

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", status_code=status.HTTP_200_OK)
def check_health(db: Session = Depends(get_db)):
    """Healthcheck endpoint ověřující stav aplikace a spojení s PostgreSQL."""
    try:
        check_database_connection(db)
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {str(exc)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "service": "drevenka-warehouse-api",
        "version": "1.0.0",
    }
