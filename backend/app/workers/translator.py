"""Batch Translator: LLM-powered translation + Chinese summary.

Processes news in batches via a single LLM call per batch.
"""
import json
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.core.llm import get_llm
from app.database import db_session
from app.models import News


BATCH_SIZE = 10

TRANSLATE_SYSTEM = """You are a professional translator. Translate titles and summaries to Simplified Chinese. Preserve technical terms in English when appropriate. Be concise.

Return a strict JSON array. Each item must have:
- "id": the news id (integer)
- "translated_title": Chinese translated title (string)
- "ai_summary": 2-3 sentence Chinese summary (string)

Rules:
- Only include items you successfully translated
- If translation fails for an item, omit it from the array
- Keep ai_summary to 2-3 sentences, factual and concise"""

TRANSLATE_USER_TEMPLATE = """Translate the following news titles and summaries to Simplified Chinese.

{items}"""


async def translate_batch(limit: int = 100) -> int:
    """Translate news in batches. Returns count processed."""
    async with db_session() as s:
        rows = (
            await s.execute(
                select(News)
                .where(News.is_ai_related == True)  # noqa: E712
                .where(News.translated_title.is_(None))
                .order_by(News.fetched_at.desc())
                .limit(limit)
            )
        ).scalars().all()

    if not rows:
        logger.info("No untranslatable news found")
        return 0

    total_processed = 0
    llm = get_llm()

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start:batch_start + BATCH_SIZE]
        items_text = "\n".join(
            f"- ID {n.id}: {n.title} | Summary: {(n.summary or '')[:200]}"
            for n in batch
        )

        try:
            resp = await llm.chat(
                TRANSLATE_SYSTEM,
                TRANSLATE_USER_TEMPLATE.format(items=items_text),
                temperature=0.2,
                json_mode=True,
            )
            results = json.loads(resp)

            if isinstance(results, dict):
                results = [results]

            async with db_session() as s:
                for item in results:
                    nid = item.get("id")
                    if nid is None:
                        continue
                    n = (await s.execute(
                        select(News).where(News.id == nid)
                    )).scalar_one_or_none()
                    if n:
                        n.translated_title = item.get("translated_title", n.title)
                        n.ai_summary = item.get("ai_summary", "")
                        n.updated_at = datetime.now(timezone.utc)
                        s.add(n)
                        total_processed += 1
                await s.commit()

            logger.info(
                f"Translated batch {batch_start // BATCH_SIZE + 1}: "
                f"{len(batch)} requested, {len(results)} translated"
            )

        except Exception as e:
            logger.warning(
                f"Translate batch {batch_start // BATCH_SIZE + 1} failed: {e}"
            )

    return total_processed
