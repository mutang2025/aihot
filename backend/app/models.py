"""ORM models: sources, news, scores, clusters, daily_digest, feedback, formula_config."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Source(Base):
    """An information source we monitor. tier T1/T1.5/T2 controls weight."""
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    url: Mapped[str] = mapped_column(String(1024))
    feed_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    tier: Mapped[str] = mapped_column(String(8), default="T2")  # T1, T1.5, T2
    category: Mapped[str] = mapped_column(String(64), default="industry")
    scraper_type: Mapped[str] = mapped_column(String(32), default="rss")  # rss/html/api/twitter
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    weight_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    news_items: Mapped[list["News"]] = relationship(back_populates="source")


class News(Base):
    """A single news item. One physical entry from a source. Clustering may group many of these."""
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(1024))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(8), default="en")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # AI processing results
    is_ai_related: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    translated_title: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)

    # Scoring: 5-dim from LLM, final_score from formula code
    five_dim_scores: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    importance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    novelty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_relevance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actionability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    credibility: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    time_decay: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dedup_penalty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Clustering
    cluster_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clusters.id"), nullable=True, index=True
    )
    is_cluster_main: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    source: Mapped["Source"] = relationship(back_populates="news_items", foreign_keys=[source_id])
    cluster: Mapped[Optional["Cluster"]] = relationship(
        back_populates="news_items",
        foreign_keys="[News.cluster_id]",
    )

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_source_external"),
        Index("ix_news_published_score", "published_at", "final_score"),
    )


class Cluster(Base):
    """An event cluster grouping multiple News items that report the same event."""
    __tablename__ = "clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    main_news_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("news.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(1024))
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, default=1)
    top_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    news_items: Mapped[list["News"]] = relationship(
        back_populates="cluster",
        foreign_keys="[News.cluster_id]",
    )


class DailyDigest(Base):
    """The AI daily digest snapshot for a specific date."""
    __tablename__ = "daily_digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    digest_date: Mapped[datetime] = mapped_column(DateTime, unique=True, index=True)
    sections: Mapped[dict] = mapped_column(JSONB)  # {"model_release": [...], ...}
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    sent_feishu: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_email: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Feedback(Base):
    """Human feedback on featured/recommended news. Used to retrain scoring."""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    news_id: Mapped[int] = mapped_column(ForeignKey("news.id"), index=True)
    rating: Mapped[str] = mapped_column(String(16))  # good/bad/skip
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FormulaConfig(Base):
    """Live-tunable scoring formula config. Edited via admin UI; no code redeploy needed."""
    __tablename__ = "formula_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True)
    value: Mapped[dict] = mapped_column(JSONB)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
