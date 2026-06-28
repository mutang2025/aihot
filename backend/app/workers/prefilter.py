"""Batch Pre-filter: cheap LLM check whether news is AI-related.

Processes in batches via single LLM call per batch.
"""
import json
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.core.llm import get_llm
from app.database import db_session
from app.models import News

BATCH_SIZE = 20

PREFILTER_SYSTEM = """You are an AI news classifier. Determine if a news item is about AI/ML/LLMs.

Return a strict JSON object:
{"is_ai_related": true/false}

Rules:
- true if the news is about AI, ML, LLMs, generative AI, neural networks, or major tech companies' AI products
- false if it's about general technology, non-AI software, or unrelated topics"""

PREFILTER_USER_TEMPLATE = """Classify the following news items. Return a JSON array of {{id, is_ai_related}}.

{items}"""


async def prefilter_batch(limit: int = 200) -> int:
    """Process unfiltered news in batches. Returns count processed."""
    async with db_session() as s:
        rows = (
            await s.execute(
                select(News)
                .where(News.is_ai_related.is_(None))
                .order_by(News.fetched_at.desc())
                .limit(limit)
            )
        ).scalars().all()

    if not rows:
        logger.info("No unfiltered news found")
        return 0

    total_processed = 0
    llm = get_llm()

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start:batch_start + BATCH_SIZE]
        items_text = "\n".join(
            f"- ID {n.id}: {n.title} | {(n.summary or '')[:150]}"
            for n in batch
        )

        try:
            resp = await llm.chat(
                PREFILTER_SYSTEM,
                PREFILTER_USER_TEMPLATE.format(items=items_text),
                temperature=0.0,
                json_mode=True,
            )
            results = json.loads(resp)

            if isinstance(results, dict) and "is_ai_related" in results:
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
                        n.is_ai_related = bool(item.get("is_ai_related"))
                        n.updated_at = datetime.now(timezone.utc)
                        s.add(n)
                        total_processed += 1
                await s.commit()

            logger.info(
                f"Prefilter batch {batch_start // BATCH_SIZE + 1}: "
                f"{len(batch)} requested, {len(results)} classified, "
                f"{sum(1 for r in results if r.get('is_ai_related'))} AI-related"
            )

        except Exception as e:
            logger.warning(
                f"Prefilter batch {batch_start // BATCH_SIZE + 1} failed: {e}"
            )

    return total_processed
