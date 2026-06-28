"""Daily digest: pick top items per category, generate Chinese headlines, send Feishu."""
import json
from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger
from sqlalchemy import select

from app.config import get_settings
from app.core.llm import get_llm
from app.core.prompts import DIGEST_SYSTEM, DIGEST_USER
from app.database import db_session
from app.models import DailyDigest, News

settings = get_settings()


async def build_digest(target_date: datetime = None) -> dict:
    """Build digest for target_date (defaults to yesterday in digest timezone)."""
    import zoneinfo
    tz = zoneinfo.ZoneInfo(settings.digest_timezone)
    if target_date is None:
        target_date = (datetime.now(tz) - timedelta(days=1)).date()
    else:
        target_date = target_date.date() if isinstance(target_date, datetime) else target_date

    start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=tz)
    end = start + timedelta(days=1)

    async with db_session() as s:
        rows = (
            await s.execute(
                select(News)
                .where(News.is_featured == True)  # noqa: E712
                .where(News.published_at >= start.astimezone(timezone.utc))
                .where(News.published_at < end.astimezone(timezone.utc))
                .order_by(News.final_score.desc().nullslast())
                .limit(100)
            )
        ).scalars().all()

    sections = {
        "model_release": [],
        "product_release": [],
        "industry": [],
        "research": [],
        "tips_opinions": [],
    }
    for n in rows:
        cat = n.category or "industry"
        if cat not in sections:
            cat = "industry"
        sections[cat].append(
            {
                "news_id": n.id,
                "title": n.title,
                "translated_title": n.translated_title,
                "url": n.url,
                "score": n.final_score,
            }
        )

    # LLM picks top items per section and writes Chinese headlines
    try:
        llm = get_llm()
        resp = await llm.chat(
            DIGEST_SYSTEM,
            DIGEST_USER.format(sections_json=json.dumps(sections, ensure_ascii=False, indent=2)),
            temperature=0.3,
            json_mode=True,
        )
        picked = json.loads(resp).get("sections", sections)
    except Exception as e:
        logger.warning(f"Digest LLM failed, using raw sections: {e}")
        picked = sections

    async with db_session() as s:
        existing = (
            await s.execute(select(DailyDigest).where(DailyDigest.digest_date == start))
        ).scalar_one_or_none()
        if existing:
            existing.sections = picked
            existing.total_items = sum(len(v) for v in picked.values() if isinstance(v, list))
        else:
            d = DailyDigest(
                digest_date=start,
                sections=picked,
                total_items=sum(len(v) for v in picked.values() if isinstance(v, list)),
            )
            s.add(d)
    return picked


async def send_feishu_card(digest_date: datetime) -> bool:
    """Send digest as a Feishu card. Returns True on success."""
    if not settings.feishu_webhook_url:
        logger.info("No Feishu webhook configured; skipping.")
        return False
    import zoneinfo
    tz = zoneinfo.ZoneInfo(settings.digest_timezone)
    start = datetime.combine(
        digest_date.date() if isinstance(digest_date, datetime) else digest_date,
        datetime.min.time(),
    ).replace(tzinfo=tz)
    async with db_session() as s:
        d = (await s.execute(select(DailyDigest).where(DailyDigest.digest_date == start))).scalar_one_or_none()
    if not d:
        return False

    # Build Feishu card
    elements = []
    for sec, items in d.sections.items():
        if not items:
            continue
        elements.append({"tag": "hr"})
        elements.append(
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**{_section_zh(sec)}**"},
            }
        )
        for it in items[:5]:
            title = it.get("headline_zh") or it.get("translated_title") or it.get("title", "")
            url = it.get("url", "")
            line = f"- [{title}]({url})" if url else f"- {title}"
            elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})

    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"AIHOT 每日 AI 热点 - {start.strftime('%Y-%m-%d')}"},
            },
            "elements": elements or [{"tag": "div", "text": {"tag": "plain_text", "content": "今日无精选"}}],
        },
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(settings.feishu_webhook_url, json=card)
    ok = r.status_code == 200
    if ok:
        async with db_session() as s:
            d2 = (await s.execute(select(DailyDigest).where(DailyDigest.digest_date == start))).scalar_one()
            d2.sent_feishu = True
            s.add(d2)
    return ok


def _section_zh(s: str) -> str:
    return {
        "model_release": "模型发布/更新",
        "product_release": "产品发布/更新",
        "industry": "行业动态",
        "research": "论文研究",
        "tips_opinions": "技巧与观点",
    }.get(s, s)
