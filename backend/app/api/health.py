from fastapi import APIRouter, Depends
from sqlalchemy import select, func

from app.config import get_settings
from app.database import get_db
from app.models import News, Source
from app.schemas import HealthOut
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
settings = get_settings()


@router.get("/api/health", response_model=HealthOut)
async def health(db: AsyncSession = Depends(get_db)):
    sources_enabled = (await db.execute(
        select(func.count()).select_from(Source).where(Source.enabled == True)  # noqa: E712
    )).scalar() or 0
    news_total = (await db.execute(select(func.count()).select_from(News))).scalar() or 0
    news_featured = (await db.execute(
        select(func.count()).select_from(News).where(News.is_featured == True)  # noqa: E712
    )).scalar() or 0
    return HealthOut(
        status="ok",
        version=settings.app_version,
        db=True,
        redis=True,
        sources_enabled=sources_enabled,
        news_total=news_total,
        news_featured=news_featured,
    )
