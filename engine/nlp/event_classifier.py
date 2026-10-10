"""
Event Classifier — hybrid rule-based + zero-shot fallback.

1. Count keyword hits per event category → confidence = min(hits/3, 1.0).
2. If best rule confidence < threshold, try zero-shot NLI model.
3. If zero-shot fails (offline), return the best rule result anyway.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from engine.config import (
    CACHE_DIR,
    DEMO_MODE,
    EVENT_KEYWORDS,
    EVENT_RULE_CONFIDENCE_THRESHOLD,
    EVENT_WEIGHT,
    ZEROSHOT_MODEL,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Zero-shot model (lazy singleton)
# ---------------------------------------------------------------------------
_zs_pipeline = None
_zs_unavailable = False
_CANDIDATE_LABELS: List[str] = list(EVENT_WEIGHT.keys())


def _get_zs_pipeline():
    """Lazily load the zero-shot classifier. Returns None on failure."""
    global _zs_pipeline, _zs_unavailable
    if _zs_pipeline is not None or _zs_unavailable:
        return _zs_pipeline
    try:
        from transformers import pipeline as hf_pipeline

        kwargs = {"model": ZEROSHOT_MODEL}
        if DEMO_MODE:
            kwargs["model_kwargs"] = {"local_files_only": True}
        logger.info("Loading zero-shot model: %s (DEMO_MODE=%s)", ZEROSHOT_MODEL, DEMO_MODE)
        _zs_pipeline = hf_pipeline("zero-shot-classification", **kwargs)
        logger.info("Zero-shot model loaded successfully")
        return _zs_pipeline
    except Exception as exc:
        logger.warning("Zero-shot model unavailable (%s), using rules only", exc)
        _zs_unavailable = True
        return None


# ---------------------------------------------------------------------------
# Rule-based classifier
# ---------------------------------------------------------------------------

def _rule_classify(text: str) -> Tuple[str, float]:
    """Return (best_label, confidence) from keyword counting."""
    lower = text.lower()
    scores: Dict[str, int] = {}
    for label, keywords in EVENT_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in lower)
        if count > 0:
            scores[label] = count

    if not scores:
        return ("Other", 0.20)

    best_label = max(scores, key=scores.get)  # type: ignore[arg-type]
    confidence = min(scores[best_label] / 3.0, 1.0)
    return (best_label, round(confidence, 4))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_event(text: str) -> Tuple[str, float]:
    """Return ``(event_type, confidence)`` for the given text.

    Uses a fast rule-based layer first.  If the best rule confidence
    is below ``EVENT_RULE_CONFIDENCE_THRESHOLD``, falls back to
    the zero-shot NLI model.  If the model is unavailable the rule
    result is returned regardless of confidence.
    """
    if not text or not text.strip():
        return ("Other", 0.0)

    rule_label, rule_conf = _rule_classify(text)

    if rule_conf >= EVENT_RULE_CONFIDENCE_THRESHOLD:
        logger.debug("Rule classification: %s (%.2f)", rule_label, rule_conf)
        return (rule_label, rule_conf)

    # Try zero-shot fallback
    pipe = _get_zs_pipeline()
    if pipe is None:
        logger.debug("Zero-shot unavailable, returning rule result: %s (%.2f)", rule_label, rule_conf)
        return (rule_label, max(rule_conf, 0.20))

    try:
        result = pipe(text, candidate_labels=_CANDIDATE_LABELS, multi_label=False)
        zs_label = result["labels"][0]
        zs_conf = round(float(result["scores"][0]), 4)
        logger.debug("Zero-shot classification: %s (%.2f)", zs_label, zs_conf)
        return (zs_label, zs_conf)
    except Exception as exc:
        logger.warning("Zero-shot inference failed (%s), using rule result", exc)
        return (rule_label, max(rule_conf, 0.20))
