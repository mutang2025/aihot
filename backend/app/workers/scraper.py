"""Generic scraper: RSS, HTML, JSON API. Per-source config in sources.yaml.

Strategy: each Source row in DB has scraper_type. We dispatch to the right
fetcher. New sources are added via admin UI -> config persisted to DB.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx
from bs4 import BeautifulSoup
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import get_settings
from app.database import db_session
from app.models import News, Source

settings = get_settings()


async def fetch_url(url: str, headers: Optional[dict] = None) -> str:
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "AIHOT/0.1 (+https://github.com/local/aihot)",
            **(headers or {}),
        },
    ) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


def _make_external_id(source: dict, raw: dict) -> str:
    """Stable ID for a news entry. Prefer guid/id/url; fall back to hash of title+url."""
    slug = source.get("slug", "")
    for k in ("id", "guid", "link"):
        if raw.get(k):
            return f"{slug}:{raw[k]}"
    h = hashlib.sha1(f"{raw.get('title','')}|{raw.get('link','')}".encode("utf-8")).hexdigest()[:16]
    return f"{slug}:h:{h}"


async def _scrape_rss(source: dict) -> list[dict]:
    feed_url = source.get("feed_url") or source["url"]
    fallback_url = source["url"]
    xml = await fetch_url(feed_url)
    feed = feedparser.parse(xml)
    out = []
    for entry in feed.entries[:50]:
        out.append(
            {
                "external_id": _make_external_id(source, entry),
                "url": entry.get("link", fallback_url),
                "title": entry.get("title", "").strip(),
                "summary": (entry.get("summary") or entry.get("description") or "").strip()[:2000],
                "author": entry.get("author"),
                "published_at": _parse_dt(entry.get("published") or entry.get("updated")),
            }
        )
    return out


async def _scrape_html(source: dict) -> list[dict]:
    """Default HTML scraper: uses CSS selectors from source.config."""
    cfg = source.get("config") or {}
    sel = cfg.get("selectors", {})
    item_sel = sel.get("item", "article")
    title_sel = sel.get("title", "h2 a, h1 a, .title a")
    link_sel = sel.get("link", "a")
    summary_sel = sel.get("summary", "p")
    base_url = source["url"]

    html = await fetch_url(base_url)
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(item_sel)[:50]
    out = []
    for item in items:
        title_el = item.select_one(title_sel)
        link_el = item.select_one(link_sel) or title_el
        title = (title_el.get_text(strip=True) if title_el else "").strip()
        link = (link_el.get("href") if link_el and link_el.has_attr("href") else base_url)
        if link.startswith("/"):
            from urllib.parse import urljoin
            link = urljoin(base_url, link)
        summary_el = item.select_one(summary_sel)
        summary = (summary_el.get_text(strip=True) if summary_el else "")[:2000]
        if not title or not link:
            continue
        out.append(
            {
                "external_id": _make_external_id(source, {"title": title, "link": link}),
                "url": link,
                "title": title,
                "summary": summary,
                "published_at": None,
            }
        )
    return out


async def _scrape_api(source: dict) -> list[dict]:
    """Generic JSON API. source.config should have 'path' to the items array
    and field mappings: title_field, url_field, summary_field, date_field."""
    cfg = source.get("config") or {}
    headers = cfg.get("headers", {})
    url = cfg.get("endpoint") or source["url"]
    items_path = cfg.get("items_path", "")
    title_f = cfg.get("title_field", "title")
    url_f = cfg.get("url_field", "url")
    summary_f = cfg.get("summary_field", "summary")
    date_f = cfg.get("date_field", "published_at")

    raw = await fetch_url(url, headers=headers)
    data = json.loads(raw)
    if items_path:
        for key in items_path.split("."):
            data = data.get(key, []) if isinstance(data, dict) else []
    if not isinstance(data, list):
        return []

    out = []
    for it in data[:50]:
        title = (it.get(title_f) or "").strip()
        link = (it.get(url_f) or "").strip()
        if not title or not link:
            continue
        out.append(
            {
                "external_id": _make_external_id(source, {"title": title, "link": link}),
                "url": link,
                "title": title,
                "summary": (it.get(summary_f) or "")[:2000],
                "published_at": _parse_dt(it.get(date_f)),
            }
        )
    return out


def _parse_dt(s) -> Optional[datetime]:
    if not s:
        return None
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    try:
        # feedparser gives time structs
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


SCRAPERS = {
    "rss": _scrape_rss,
    "html": _scrape_html,
    "api": _scrape_api,
}


async def scrape_source(source: dict) -> int:
    """Scrape one source. Returns number of new items inserted.

    Accepts a plain dict (built in scrape_all_sources while still in session)
    so we don't touch detached ORM attributes after the session closes.
    """
    scraper_type = source["scraper_type"]
    slug = source["slug"]
    source_id = source["id"]
    scraper = SCRAPERS.get(scraper_type)
    if not scraper:
        logger.warning(f"No scraper for type={scraper_type} (source={slug})")
        return 0
    try:
        items = await scraper(source)
    except Exception as e:
        logger.error(f"Scrape failed for {slug}: {e}")
        async with db_session() as s:
            stmt = (
                update(Source)
                .where(Source.id == source_id)
                .values(last_status="error", last_error=str(e)[:500])
            )
            await s.execute(stmt)
        return 0

    if not items:
        async with db_session() as s:
            stmt = (
                update(Source)
                .where(Source.id == source_id)
                .values(last_status="ok_empty", last_error=None)
            )
            await s.execute(stmt)
        return 0

    new_count = 0
    async with db_session() as s:
        for it in items:
            stmt = (
                pg_insert(News)
                .values(
                    source_id=source_id,
                    external_id=it["external_id"],
                    url=it["url"],
                    title=it["title"],
                    summary=it.get("summary"),
                    author=it.get("author"),
                    published_at=it.get("published_at"),
                    language="en",
                )
                .on_conflict_do_nothing(index_elements=["source_id", "external_id"])
            )
            res = await s.execute(stmt)
            if res.rowcount > 0:
                new_count += 1
        upd = (
            update(Source)
            .where(Source.id == source_id)
            .values(
                last_status="ok",
                last_error=None,
                last_fetched_at=datetime.now(timezone.utc),
            )
        )
        await s.execute(upd)
    return new_count


async def scrape_all_sources() -> dict:
    """Iterate enabled sources, scrape each, return summary."""
    summary = {"scraped": 0, "new_items": 0, "errors": 0}
    async with db_session() as s:
        sources = (await s.execute(select(Source).where(Source.enabled == True))).scalars().all()  # noqa: E712
        # Build a list of plain dicts in-session so we don't touch detached attrs later
        sources_payload = [
            {
                "id": src.id,
                "slug": src.slug,
                "name": src.name,
                "url": src.url,
                "feed_url": src.feed_url,
                "tier": src.tier,
                "category": src.category,
                "scraper_type": src.scraper_type,
                "config": src.config or {},
                "weight_override": src.weight_override,
            }
            for src in sources
        ]
    for src in sources_payload:
        try:
            new = await scrape_source(src)
            summary["scraped"] += 1
            summary["new_items"] += new
        except Exception as e:
            logger.error(f"Top-level error for {src['slug']}: {e}")
            summary["errors"] += 1
    return summary
