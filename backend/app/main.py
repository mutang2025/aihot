"""FastAPI app entry. Mounts all routers and a tiny scheduler for periodic workers."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import select

from app.api import feedback, health, news, sources
from app.config import get_settings
from app.database import Base, db_session, engine
from app.models import Source
from app.workers import clusterer, digester, prefilter, scorer
from app.workers.scraper import scrape_all_sources

settings = get_settings()
Path("/app/data/logs").mkdir(parents=True, exist_ok=True)
logger.add("/app/data/logs/aihot.log", rotation="10 MB", retention="30 days", level="INFO")

scheduler: Optional[AsyncIOScheduler] = None


async def _load_seed_sources():
    """On first start, populate sources table from sources.yaml if empty."""
    yaml_path = Path("/app/app/sources_data/sources.yaml")
    if not yaml_path.exists():
        yaml_path = Path(__file__).parent / "sources_data" / "sources.yaml"
    if not yaml_path.exists():
        logger.warning("sources.yaml not found, skipping seed")
        return
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    sources_list = data.get("sources", [])
    if not sources_list:
        return
    async with db_session() as s:
        existing = (await s.execute(select(Source))).scalars().all()
        existing_slugs = {x.slug for x in existing}
        added = 0
        for src in sources_list:
            if src["slug"] in existing_slugs:
                continue
            s.add(Source(**src))
            added += 1
        if added:
            logger.info(f"Seeded {added} new sources from sources.yaml")


async def _run_scrape_cycle():
    summary = await scrape_all_sources()
    logger.info(f"Scrape cycle: {summary}")
    pf = await prefilter.prefilter_batch(limit=100)
    sc = await scorer.score_batch(limit=50)
    cl = await clusterer.cluster_recent()
    logger.info(f"Pipeline: prefilter={pf} scored={sc} clusters={cl}")


async def _run_digest_cycle():
    picked = await digester.build_digest()
    sent = await digester.send_feishu_card(picked.get("digest_date")) if picked else False
    logger.info(f"Digest built and sent_feishu={sent}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    # Auto-create tables on first boot (dev convenience; use Alembic in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _load_seed_sources()
    scheduler = AsyncIOScheduler(timezone=settings.digest_timezone)
    scheduler.add_job(
        _run_scrape_cycle, "interval", minutes=settings.scraper_interval_minutes,
        id="scrape_cycle", next_run_time=None,
    )
    scheduler.add_job(
        _run_digest_cycle, "cron", hour=settings.digest_send_hour, minute=0,
        id="digest_cycle",
    )
    scheduler.start()
    # Run one scrape cycle immediately on boot
    asyncio.create_task(_run_scrape_cycle())
    logger.info("AIHOT started")
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(news.router)
app.include_router(sources.router)
app.include_router(feedback.router)


@app.post("/api/admin/run-scrape")
async def admin_run_scrape():
    """Manual trigger for one scrape cycle (for testing)."""
    asyncio.create_task(_run_scrape_cycle())
    return {"status": "started"}


@app.post("/api/admin/run-prefilter")
async def admin_run_prefilter(limit: int = 50):
    """Manual trigger for prefilter batch."""
    from app.workers.prefilter import prefilter_batch
    n = await prefilter_batch(limit=limit)
    return {"processed": n}


@app.post("/api/admin/run-scoring")
async def admin_run_scoring(limit: int = 20):
    """Manual trigger for scoring batch."""
    from app.workers.scorer import score_batch
    n = await score_batch(limit=limit)
    return {"scored": n}


@app.post("/api/admin/run-translate")
async def admin_run_translate(limit: int = 20):
    """Manual trigger for translate+summary batch."""
    from app.workers.translator import translate_batch
    n = await translate_batch(limit=limit)
    return {"translated": n}


@app.post("/api/admin/run-clustering")
async def admin_run_clustering():
    """Manual trigger for clustering cycle."""
    from app.workers.clusterer import cluster_recent
    n = await cluster_recent()
    return {"clusters": n}


@app.post("/api/admin/run-digest")
async def admin_run_digest():
    """Manual trigger for digest build+send."""
    asyncio.create_task(_run_digest_cycle())
    return {"status": "started"}
