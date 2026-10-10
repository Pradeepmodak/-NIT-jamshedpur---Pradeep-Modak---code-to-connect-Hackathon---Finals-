"""
Sentiment Analysis — ProsusAI/finbert with keyword fallback.

score = P(positive) - P(negative)  ∈ [-1, 1]
confidence = max probability among the three classes
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import List, Optional, Tuple

from engine.config import (
    CACHE_DIR,
    DEMO_MODE,
    FINBERT_MODEL,
    SEED,
    SENTIMENT_BATCH_SIZE,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword fallback lists (financial domain)
# ---------------------------------------------------------------------------
_POS_WORDS = {
    "surge", "surges", "surging", "soar", "soars", "soaring", "rally",
    "rallies", "gain", "gains", "rise", "rises", "rising", "jump", "jumps",
    "record high", "beat", "beats", "exceed", "exceeds", "upgrade",
    "upgrades", "outperform", "bullish", "boom", "booming", "profit",
    "profitable", "growth", "strong", "positive", "optimis", "recover",
    "recovery", "innovation", "launch", "unveil", "expand", "expansion",
    "success", "breakthrough", "skyrocket",
}
_NEG_WORDS = {
    "crash", "crashes", "crashing", "plunge", "plunges", "plunging",
    "decline", "declines", "drop", "drops", "fall", "falls", "falling",
    "tumble", "tumbles", "loss", "losses", "miss", "misses", "disappoint",
    "disappoints", "downgrade", "downgrades", "underperform", "bearish",
    "bust", "bankrupt", "bankruptcy", "fraud", "scandal", "recall",
    "layoff", "layoffs", "fire", "warning", "crisis", "collapse",
    "tank", "tanks", "volatile", "negative", "pessimis", "weak",
    "lawsuit", "investigation", "halt", "suspend",
}


def _keyword_sentiment(text: str) -> Tuple[float, float]:
    """Simple keyword-based fallback: returns (score, confidence)."""
    lower = text.lower()
    pos = sum(1 for w in _POS_WORDS if w in lower)
    neg = sum(1 for w in _NEG_WORDS if w in lower)
    total = pos + neg
    if total == 0:
        return 0.0, 0.3  # neutral, low confidence
    score = (pos - neg) / total  # in [-1, 1]
    confidence = min(total / 5.0, 1.0)
    return round(score, 4), round(confidence, 4)


# ---------------------------------------------------------------------------
# Model loader (cached singleton)
# ---------------------------------------------------------------------------
_pipeline = None
_using_fallback = False


def _get_pipeline():
    """Lazily load the FinBERT pipeline. Returns None on failure."""
    global _pipeline, _using_fallback
    if _pipeline is not None or _using_fallback:
        return _pipeline
    try:
        from transformers import pipeline as hf_pipeline
        import torch

        kwargs = {
            "model": FINBERT_MODEL,
            "tokenizer": FINBERT_MODEL,
            "truncation": True,
            "max_length": 512,
        }
        if DEMO_MODE:
            kwargs["model_kwargs"] = {"local_files_only": True}
            kwargs["tokenizer"] = FINBERT_MODEL

        logger.info("Loading FinBERT model: %s (DEMO_MODE=%s)", FINBERT_MODEL, DEMO_MODE)
        _pipeline = hf_pipeline("text-classification", **kwargs, top_k=None)
        logger.info("FinBERT loaded successfully")
        return _pipeline
    except Exception as exc:
        logger.warning("FinBERT unavailable (%s), using keyword fallback", exc)
        _using_fallback = True
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_sentiment(texts: List[str]) -> List[Tuple[float, float]]:
    """Return ``[(score, confidence), ...]`` for each text.

    ``score = P(positive) - P(negative)`` in ``[-1, 1]``.
    ``confidence = max(P(pos), P(neg), P(neutral))``.
    """
    if not texts:
        return []

    pipe = _get_pipeline()
    if pipe is None:
        # Keyword fallback
        logger.debug("Using keyword fallback for %d texts", len(texts))
        return [_keyword_sentiment(t) for t in texts]

    results: List[Tuple[float, float]] = []
    # Process in batches
    for i in range(0, len(texts), SENTIMENT_BATCH_SIZE):
        batch = texts[i : i + SENTIMENT_BATCH_SIZE]
        # Sanitise: ensure non-empty strings
        batch = [t if t and t.strip() else "neutral" for t in batch]
        try:
            preds = pipe(batch)
            for pred in preds:
                prob = {item["label"].lower(): item["score"] for item in pred}
                p_pos = prob.get("positive", 0.0)
                p_neg = prob.get("negative", 0.0)
                p_neu = prob.get("neutral", 0.0)
                score = round(p_pos - p_neg, 4)
                confidence = round(max(p_pos, p_neg, p_neu), 4)
                results.append((score, confidence))
        except Exception as exc:
            logger.warning("FinBERT batch error: %s — falling back to keywords", exc)
            results.extend(_keyword_sentiment(t) for t in batch)

    return results
