from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def get_health(db: SessionDep):
    db.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "ok"}
