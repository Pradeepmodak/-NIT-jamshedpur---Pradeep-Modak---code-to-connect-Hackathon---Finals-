from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
import uuid
from pathlib import Path

from engine.config import DEMO_MODE, NEWSAPI_KEY, SAMPLES_DIR, CACHE_DIR
from engine.ingestion.schema import SignalRecord

logger = logging.getLogger(__name__)

def _parse_articles(data) -> list[SignalRecord]:
    articles = data.get("articles", []) if isinstance(data, dict) else data
    if not isinstance(articles, list):
        return []
        
    records = []
    for art in articles:
        if not isinstance(art, dict):
            continue
        title = art.get("title") or ""
        desc = art.get("description") or ""
        text = f"{title} {desc}".strip()
        ts = art.get("publishedAt", datetime.now(timezone.utc).isoformat())
        record_id = str(uuid.uuid4())
        records.append(SignalRecord(id=record_id, source="newsapi", text=text, timestamp=ts))
    return records

def _load_from_file(filepath: Path) -> list[SignalRecord]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Try to handle serialized SignalRecords or NewsAPI format
            if isinstance(data, list) and len(data) > 0 and "source" in data[0] and "text" in data[0]:
                return [SignalRecord.from_dict(item) for item in data]
            return _parse_articles(data)
    except Exception as e:
        logger.error(f"Failed to load from {filepath}: {e}")
        return []

def fetch_headlines(query: str = 'stock market finance', page_size: int = 50) -> list[SignalRecord]:
    """Fetch headlines from NewsAPI with fallbacks."""
    sample_file = SAMPLES_DIR / 'news.json'
    cache_file = CACHE_DIR / 'newsapi_cache.json'

    if DEMO_MODE:
        logger.info(f"DEMO_MODE is True, loading from samples {sample_file}")
        return _load_from_file(sample_file)

    url = f"https://newsapi.org/v2/everything?q={urllib.parse.quote(query)}&pageSize={page_size}"
    req = urllib.request.Request(url)
    if NEWSAPI_KEY:
        req.add_header("X-Api-Key", NEWSAPI_KEY)

    try:
        if not NEWSAPI_KEY:
            raise ValueError("NEWSAPI_KEY is not set")
            
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
            
        logger.info("Successfully fetched from NewsAPI and cached response")
        return _parse_articles(data)
            
    except Exception as e:
        logger.warning(f"Failed to fetch from NewsAPI: {e}. Trying cache...")
        if cache_file.exists():
            logger.info(f"Loading from cache {cache_file}")
            return _load_from_file(cache_file)
        else:
            logger.warning(f"Cache missing. Falling back to {sample_file}")
            return _load_from_file(sample_file)
