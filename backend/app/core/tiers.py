"""Source tier weights and category metadata.

T1  - official first-party blogs/research (highest weight)
T1.5 - official social accounts (more noise, lower weight)
T2  - KOLs, media, aggregators (lowest weight)
"""
from enum import Enum


class Tier(str, Enum):
    T1 = "T1"
    T1_5 = "T1.5"
    T2 = "T2"


# Default weight per tier. Can be overridden per-source via sources.weight_override.
TIER_WEIGHT = {
    Tier.T1: 1.0,
    Tier.T1_5: 0.7,
    Tier.T2: 0.4,
}


class Category(str, Enum):
    MODEL_RELEASE = "model_release"
    PRODUCT_RELEASE = "product_release"
    INDUSTRY = "industry"
    RESEARCH = "research"
    TIPS_OPINIONS = "tips_opinions"
    UNKNOWN = "unknown"


# Per-category minimum featured-score threshold.
FEATURED_THRESHOLD = {
    Category.MODEL_RELEASE: 70,
    Category.PRODUCT_RELEASE: 65,
    Category.INDUSTRY: 60,
    Category.RESEARCH: 55,
    Category.TIPS_OPINIONS: 50,
    Category.UNKNOWN: 60,
}
