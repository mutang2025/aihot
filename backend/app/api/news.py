"""News & clusters & digest API."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Cluster, News, Source, DailyDigest
from app.schemas import NewsOut, ClusterOut, DigestOut

router = APIRouter()


@router.get("/api/news", response_model=list[NewsOut])
async def list_news(
    category: Optional[str] = None,
    source_id: Optional[int] = None,
    q: Optional[str] = None,
    featured_only: bool = False,
    cluster_main_only: bool = True,
    since_hours: int = 168,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List news with filters. Default: cluster main items only, last 7 days."""
    stmt = (
        select(News, Source)
        .join(Source, News.source_id == Source.id)
        .where(News.fetched_at > datetime.now(timezone.utc) - timedelta(hours=since_hours))
    )
    if category:
        stmt = stmt.where(News.category == category)
    if source_id:
        stmt = stmt.where(News.source_id == source_id)
    if featured_only:
        stmt = stmt.where(News.is_featured == True)  # noqa: E712
    if cluster_main_only:
        stmt = stmt.where(or_(News.cluster_id.is_(None), News.is_cluster_main == True))  # noqa: E712
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(News.title.ilike(like), News.translated_title.ilike(like), News.ai_summary.ilike(like)))
    stmt = stmt.order_by(News.final_score.desc().nullslast(), News.published_at.desc().nullslast())
    stmt = stmt.limit(min(limit, 200)).offset(offset)
    rows = (await db.execute(stmt)).all()
    out = []
    for n, s in rows:
        item = NewsOut.model_validate(n)
        item.source_name = s.name
        item.source_tier = s.tier
        out.append(item)
    return out


@router.get("/api/news/{news_id}", response_model=NewsOut)
async def get_news(news_id: int, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(
        select(News, Source).join(Source).where(News.id == news_id)
    )).first()
    if not row:
        raise HTTPException(404, "News not found")
    n, s = row
    item = NewsOut.model_validate(n)
    item.source_name = s.name
    item.source_tier = s.tier
    return item


@router.get("/api/clusters/{cluster_id}", response_model=ClusterOut)
async def get_cluster(cluster_id: int, db: AsyncSession = Depends(get_db)):
    c = (await db.execute(
        select(Cluster).where(Cluster.id == cluster_id).options(selectinload(Cluster.news_items).selectinload(News.source))
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Cluster not found")
    out = ClusterOut.model_validate(c)
    if c.news_items:
        main = next((n for n in c.news_items if n.is_cluster_main), c.news_items[0])
        out.main_news = NewsOut.model_validate(main)
        out.main_news.source_name = main.source.name
        out.main_news.source_tier = main.source.tier
        out.members = []
        for n in c.news_items:
            if n.id == main.id:
                continue
            m = NewsOut.model_validate(n)
            m.source_name = n.source.name
            m.source_tier = n.source.tier
            out.members.append(m)
    return out


@router.get("/api/digest/latest", response_model=DigestOut)
async def get_latest_digest(db: AsyncSession = Depends(get_db)):
    d = (await db.execute(select(DailyDigest).order_by(DailyDigest.digest_date.desc()).limit(1))).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "No digest yet")
    return d
