from __future__ import annotations

import csv
import hashlib
import logging
import time
import random
from pathlib import Path
from typing import Generator
from datetime import datetime, timezone

from engine.config import RAW_DIR, SAMPLES_DIR, SEED
from engine.ingestion.schema import SignalRecord

logger = logging.getLogger(__name__)

random.seed(SEED)

def load_tweets(csv_path: Path | None = None) -> list[SignalRecord]:
    """Load all tweets sorted by timestamp."""
    if csv_path is None:
        csv_path = RAW_DIR / 'stock_tweets.csv'

    if not csv_path.exists():
        fallback_path = SAMPLES_DIR / 'tweets.csv'
        if fallback_path.exists():
            logger.info(f"CSV {csv_path} missing, falling back to {fallback_path}")
            csv_path = fallback_path
        else:
            logger.warning(f"Both {csv_path} and {fallback_path} are missing.")
            return []

    records = []
    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get('Date', '')
                tweet_text = row.get('Tweet', '')
                if not date_str or not tweet_text:
                    continue
                
                record_id = hashlib.md5(f"{date_str}{tweet_text}".encode('utf-8')).hexdigest()
                
                records.append(SignalRecord(
                    id=record_id,
                    source='tweet',
                    text=tweet_text.strip(),
                    timestamp=date_str.strip()
                ))
    except Exception as e:
        logger.error(f"Error reading tweets: {e}")
        
    records.sort(key=lambda r: r.timestamp)
    return records

def stream_tweets(speed_multiplier: float = 1.0, csv_path: Path | None = None) -> Generator[SignalRecord, None, None]:
    """Yield tweets in timestamp order with real-time delays scaled by speed_multiplier."""
    records = load_tweets(csv_path)
    if not records:
        return
        
    def parse_dt(ts_str: str) -> datetime:
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)

    last_time = None
    for record in records:
        current_time = parse_dt(record.timestamp)
        if last_time is not None:
            delay = (current_time - last_time).total_seconds()
            if delay > 0:
                time.sleep(delay / speed_multiplier)
        
        last_time = current_time
        yield record
