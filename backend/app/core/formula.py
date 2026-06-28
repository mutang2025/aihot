"""Scoring formula: 5 LLM dims * source weight * time decay * dedup penalty.

This is the core insight from Kazike's AIHOT: LLM is dumb for final scores
and dedup. Keep all the math in code so it's tweakable in seconds.
"""
from datetime import datetime, timezone
from math import exp
from typing import Optional

from app.core.tiers import Category, TIER_WEIGHT, FEATURED_THRESHOLD, Tier


# Per-dimension weights (must sum to 1.0). Tuned to favor importance+credibility.
DIM_WEIGHTS = {
    "importance": 0.30,
    "ai_relevance": 0.20,
    "novelty": 0.15,
    "actionability": 0.15,
    "credibility": 0.20,
}


def time_decay(published_at: Optional[datetime], now: Optional[datetime] = None) -> float:
    """Exponential decay: 1.0 within 24h, ~0.3 at 7d, ~0.05 at 30d."""
    if not published_at:
        return 0.5
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    hours = max(0.0, (now - published_at).total_seconds() / 3600.0)
    # half-life ~ 48h
    return float(exp(-hours / 48.0 / 1.0))  # 0.5 at 48h, ~0.06 at 14d


def dedup_penalty(duplicate_count: int) -> float:
    """Same event reported N times: first = 1.0, each additional * 0.7."""
    if duplicate_count <= 1:
        return 1.0
    return 0.7 ** (duplicate_count - 1)


def weighted_five_dim(scores: dict) -> float:
    """Combine 5 LLM scores (0-100) into one weighted 0-100 number."""
    if not scores:
        return 0.0
    total = 0.0
    weight_sum = 0.0
    for dim, w in DIM_WEIGHTS.items():
        v = scores.get(dim)
        if v is None:
            continue
        total += float(v) * w
        weight_sum += w
    if weight_sum == 0:
        return 0.0
    # Normalize if some dims were missing
    return total / weight_sum


def compute_final_score(
    five_dim: dict,
    tier: str,
    published_at: Optional[datetime],
    duplicate_count: int = 1,
    weight_override: Optional[float] = None,
) -> dict:
    """Compute final_score and return all intermediate values (for transparency)."""
    five_dim_weighted = weighted_five_dim(five_dim or {})
    src_w = (
        float(weight_override)
        if weight_override is not None
        else TIER_WEIGHT.get(Tier(tier) if tier in [t.value for t in Tier] else Tier.T2, 0.4)
    )
    td = time_decay(published_at)
    dp = dedup_penalty(duplicate_count)
    final = five_dim_weighted * src_w * td * dp
    return {
        "five_dim_weighted": round(five_dim_weighted, 2),
        "source_weight": round(src_w, 3),
        "time_decay": round(td, 3),
        "dedup_penalty": round(dp, 3),
        "final_score": round(final, 2),
    }


def is_featured(final_score: float, category: Optional[str]) -> bool:
    if not final_score or final_score <= 0:
        return False
    try:
        cat = Category(category) if category else Category.UNKNOWN
    except ValueError:
        cat = Category.UNKNOWN
    return final_score >= FEATURED_THRESHOLD[cat]
