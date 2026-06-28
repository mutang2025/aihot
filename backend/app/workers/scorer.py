"""Batch Scoring: 5-dim LLM score + formula final score + featured flag.

Processes in batches via single LLM call per batch.
"""
import json
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.core.formula import compute_final_score, is_featured
from app.core.llm import get_llm
from app.database import db_session
from app.models import News, Source

BATCH_SIZE = 15

SCORE_SYSTEM = """You are an AI news analyst. Score news items on 5 dimensions (0-100 scale).

Return a strict JSON array. Each item must have:
- "id": the news id (integer)
- "importance": 0-100
- "ai_relevance": 0-100
- "novelty": 0-100
- "actionability": 0-100
- "credibility": 0-100
- "category": one of [model_release, product_release, industry, research, tips_opinions, unknown]

Rules:
- importance: How important is this news in the AI community?
- ai_relevance: How directly related to AI/ML?
- novelty: How new/unique is this information?
- actionability: Can developers/users act on this?
- credibility: Is the source reliable?
- category: Classify into one of the categories above"""

SCORE_USER_TEMPLATE = """Score the following news items. Return a JSON array of scored items.

{items}"""


async def score_batch(limit: int = 150) -> int:
    """Score AI-related news that lacks scores. Returns count processed."""
    async with db_session() as s:
        rows = (
            await s.execute(
                select(News, Source)
                .join(Source, News.source_id == Source.id)
                .where(News.is_ai_related == True)  # noqa: E712
                .where(News.five_dim_scores.is_(None))
                .order_by(News.fetched_at.desc())
                .limit(limit)
            )
        ).all()

    if not rows:
        logger.info("No un-scored AI news found")
        return 0

    total_processed = 0
    llm = get_llm()

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start:batch_start + BATCH_SIZE]
        items_text = "\n".join(
            f"- ID {n.id}: [{s.name} Tier-{s.tier}] {n.title} | {(n.summary or '')[:200]}"
            for n, s in batch
        )

        try:
            resp = await llm.chat(
                SCORE_SYSTEM,
                SCORE_USER_TEMPLATE.format(items=items_text),
                temperature=0.2,
                json_mode=True,
            )
            results = json.loads(resp)

            if isinstance(results, dict) and "importance" in results:
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
                        scores = {
                            "importance": float(item.get("importance", 0)),
                            "ai_relevance": float(item.get("ai_relevance", 0)),
                            "novelty": float(item.get("novelty", 0)),
                            "actionability": float(item.get("actionability", 0)),
                            "credibility": float(item.get("credibility", 0)),
                        }
                        category = item.get("category") or "unknown"
                        comp = compute_final_score(
                            scores, n.source.tier, n.published_at,
                            duplicate_count=1,
                            weight_override=n.source.weight_override,
                        )
                        n.five_dim_scores = scores
                        n.importance = scores["importance"]
                        n.novelty = scores["novelty"]
                        n.ai_relevance = scores["ai_relevance"]
                        n.actionability = scores["actionability"]
                        n.credibility = scores["credibility"]
                        n.source_weight = comp["source_weight"]
                        n.time_decay = comp["time_decay"]
                        n.dedup_penalty = comp["dedup_penalty"]
                        n.final_score = comp["final_score"]
                        n.category = category
                        n.is_featured = is_featured(comp["final_score"], category)
                        n.updated_at = datetime.now(timezone.utc)
                        s.add(n)
                        total_processed += 1
                await s.commit()

            logger.info(
                f"Score batch {batch_start // BATCH_SIZE + 1}: "
                f"{len(batch)} requested, {len(results)} scored"
            )

        except Exception as e:
            logger.warning(
                f"Score batch {batch_start // BATCH_SIZE + 1} failed: {e}"
            )

    return total_processed
