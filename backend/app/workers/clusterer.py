"""Event clustering using embedding cosine similarity.

v1.0: use scikit-learn TF-IDF + cosine (no external embedding service).
A real bge-m3 / OpenAI embedding can be plugged in later via the same interface.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from loguru import logger
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select, func

from app.config import get_settings
from app.database import db_session
from app.models import Cluster, News

settings = get_settings()
EMBED_CACHE = Path("/app/data/embeddings/tfidf.npz")


async def cluster_recent(limit: int = 200, threshold: float = None) -> int:
    """Cluster unclustered news from the last 72h. Returns number of clusters touched."""
    threshold = threshold or settings.similarity_threshold
    async with db_session() as s:
        rows = (
            await s.execute(
                select(News)
                .where(News.cluster_id.is_(None))
                .where(News.fetched_at > func.now() - func.make_interval(0, 0, 0, 3, 0, 0, 0))
                .order_by(News.final_score.desc().nullslast())
                .limit(limit)
            )
        ).scalars().all()

    if not rows:
        return 0

    texts = [(r.title or "") + " " + (r.summary or "")[:500] for r in rows]
    vec = TfidfVectorizer(max_features=5000, stop_words="english", ngram_range=(1, 2))
    try:
        X = vec.fit_transform(texts)
    except ValueError:
        return 0
    sim = cosine_similarity(X)

    # Union-find for transitive clustering
    parent = list(range(len(rows)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if sim[i, j] >= threshold:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(len(rows)):
        groups.setdefault(find(i), []).append(i)

    cluster_count = 0
    async with db_session() as s:
        for indices in groups.values():
            if len(indices) < 2:
                # Single item - no cluster needed
                n = rows[indices[0]]
                continue
            # Pick main = highest tier, then highest final_score
            def sort_key(i):
                n = rows[i]
                tier_rank = {"T1": 3, "T1.5": 2, "T2": 1}.get(n.source.tier, 0) if n.source else 0
                return (tier_rank, n.final_score or 0)
            main_i = max(indices, key=sort_key)
            main = rows[main_i]
            members = [rows[i] for i in indices]
            c = Cluster(
                main_news_id=main.id,
                title=main.title,
                category=main.category,
                member_count=len(members),
                top_score=max((m.final_score or 0) for m in members),
                is_featured=any(m.is_featured for m in members),
            )
            s.add(c)
            await s.flush()
            for i in indices:
                rows[i].cluster_id = c.id
                rows[i].is_cluster_main = (i == main_i)
                s.add(rows[i])
            cluster_count += 1
    return cluster_count
