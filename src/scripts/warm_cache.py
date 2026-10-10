"""
Warm cache: pre-download models and price data for offline use.

Run this ONCE with internet, then DEMO_MODE=1 works fully offline.

    python scripts/warm_cache.py
"""
from __future__ import annotations

import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.config import (
    CACHE_DIR,
    FINBERT_MODEL,
    LOG_FORMAT,
    REPLAY_END,
    REPLAY_START,
    TICKERS,
    ZEROSHOT_MODEL,
)

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def warm_models() -> None:
    """Download HuggingFace models to local cache."""
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        logger.info("Downloading FinBERT: %s", FINBERT_MODEL)
        AutoTokenizer.from_pretrained(FINBERT_MODEL)
        AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL)
        logger.info("FinBERT cached successfully")

        logger.info("Downloading zero-shot model: %s", ZEROSHOT_MODEL)
        AutoTokenizer.from_pretrained(ZEROSHOT_MODEL)
        AutoModelForSequenceClassification.from_pretrained(ZEROSHOT_MODEL)
        logger.info("Zero-shot model cached successfully")

    except Exception as exc:
        logger.warning("Model download failed: %s", exc)
        logger.info("The engine will use keyword-based fallbacks.")


def warm_prices() -> None:
    """Download price data to local cache."""
    try:
        from module_a.prices import fetch_prices

        logger.info("Downloading prices for %d tickers: %s–%s",
                     len(TICKERS), REPLAY_START, REPLAY_END)
        df = fetch_prices(TICKERS, REPLAY_START, REPLAY_END, force_refresh=True)
        logger.info("Cached %d days of prices to %s", len(df), CACHE_DIR)
    except Exception as exc:
        logger.warning("Price download failed: %s — synthetic will be used", exc)


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("=== SentinelRisk Cache Warmer ===")
    warm_prices()
    warm_models()
    logger.info("=== Cache warming complete ===")


if __name__ == "__main__":
    main()
