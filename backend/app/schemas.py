"""Pydantic schemas for API request/response."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    url: str
    feed_url: Optional[str] = None
    tier: str
    category: str
    scraper_type: str
    enabled: bool
    last_fetched_at: Optional[datetime] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None


class SourceIn(BaseModel):
    slug: str
    name: str
    url: str
    feed_url: Optional[str] = None
    tier: str = "T2"
    category: str = "industry"
    scraper_type: str = "rss"
    enabled: bool = True
    weight_override: Optional[float] = None
    config: dict = {}


class NewsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_id: int
    source_name: Optional[str] = None
    source_tier: Optional[str] = None
    url: str
    title: str
    summary: Optional[str] = None
    translated_title: Optional[str] = None
    ai_summary: Optional[str] = None
    category: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime
    final_score: Optional[float] = None
    is_featured: bool
    cluster_id: Optional[int] = None
    is_cluster_main: bool
    cluster_member_count: Optional[int] = None


class ClusterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    category: Optional[str] = None
    member_count: int
    top_score: Optional[float] = None
    is_featured: bool
    first_seen_at: datetime
    last_updated_at: datetime
    main_news: Optional[NewsOut] = None
    members: list[NewsOut] = []


class DigestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    digest_date: datetime
    sections: dict
    total_items: int
    sent_feishu: bool
    sent_email: bool


class FeedbackIn(BaseModel):
    news_id: int
    rating: str  # good/bad/skip
    note: Optional[str] = None


class FormulaConfigIn(BaseModel):
    key: str
    value: dict
    description: Optional[str] = None


class HealthOut(BaseModel):
    status: str
    version: str
    db: bool
    redis: bool
    sources_enabled: int
    news_total: int
    news_featured: int
