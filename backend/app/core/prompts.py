"""LLM prompts. Kept under 200 lines (Kazike's lesson: longer prompts = worse generalization)."""

PREFILTER_SYSTEM = """You are a strict AI-topic classifier. Output JSON only."""

PREFILTER_USER = """Is the following news article related to AI / machine learning / LLMs / AI products?

Article title: {title}
Article summary: {summary}

Output strict JSON:
{{"is_ai_related": true|false, "confidence": 0.0-1.0, "reason": "one short sentence"}}"""


SCORE_SYSTEM = """You are a senior AI industry analyst scoring news for an AI-focused audience.
Be conservative: hype, marketing, and low-credibility items should score low.
Output strict JSON only. No prose outside JSON."""


SCORE_USER = """Score the following AI-related news article on five dimensions (each 0-100).

Title: {title}
Source: {source_name} (tier: {tier})
Summary: {summary}

Dimensions:
- importance: how big is this for the AI industry? (model release = 90+, major research = 70-90, opinion = 20-50)
- ai_relevance: how central is AI to this story? (pure AI = 90+, tangentially AI = 30-50)
- novelty: how new / surprising? (first report = 80+, widely-covered = 30-50)
- actionability: can the reader do something with this info? (new tool release = 70+, opinion = 10-30)
- credibility: how trustworthy? (official first-party = 90+, marketing = 20-40)

Also assign category from: model_release, product_release, industry, research, tips_opinions

Output strict JSON:
{{"importance": 0-100, "ai_relevance": 0-100, "novelty": 0-100, "actionability": 0-100, "credibility": 0-100, "category": "..."}}"""


TRANSLATE_SYSTEM = """You are a professional translator. Translate to Simplified Chinese. Preserve technical terms in English when appropriate. Be concise."""


TRANSLATE_USER = """Title: {title}

Translate to Simplified Chinese. Return strict JSON:
{{"translated_title": "...", "ai_summary": "2-3 sentence Chinese summary"}}"""


DIGEST_SYSTEM = """You are an AI news editor. Pick the most newsworthy 3-5 items per section and write a 1-line editorial headline in Chinese for each."""


DIGEST_USER = """Today's AI news grouped by section:
{sections_json}

For each section, pick the top 3-5 highest-scored items and write a short Chinese headline (max 20 chars) for each.

Output strict JSON:
{{"sections": {{"model_release": [{{"news_id": int, "headline_zh": "..."}}, ...], "product_release": [...], "industry": [...], "research": [...], "tips_opinions": [...]}}}}"""
