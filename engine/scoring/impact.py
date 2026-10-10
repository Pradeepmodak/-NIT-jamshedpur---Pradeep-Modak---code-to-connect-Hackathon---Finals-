from __future__ import annotations

import dataclasses
import json
import logging
from pathlib import Path
from typing import List, Tuple

from engine.config import (
    W_SENT, W_EVT, W_SEV, EVENT_WEIGHT, SEVERITY_KEYWORDS, OUTPUT_DIR, TICKERS, DEMO_MODE
)
from engine.ingestion.schema import SignalRecord, AnalyzedSignal
from engine.nlp.entity_extractor import extract_entities
from engine.nlp.sentiment import analyze_sentiment
from engine.nlp.event_classifier import classify_event

logger = logging.getLogger(__name__)

def compute_severity_score(text: str) -> float:
    """Count severity keyword matches, return score in [0, 1]."""
    text_lower = text.lower()
    count = sum(1 for kw in SEVERITY_KEYWORDS if kw.lower() in text_lower)
    return min(count / 5.0, 1.0)

def compute_impact(sentiment_score: float, event_type: str, text: str) -> tuple[int, str]:
    """Return (impact_score 1-10, explanation string)."""
    severity_score = compute_severity_score(text)
    event_w = EVENT_WEIGHT.get(event_type, 0.3)
    raw = 10 * (W_SENT * abs(sentiment_score) + W_EVT * event_w + W_SEV * severity_score)
    impact = max(1, min(10, round(raw)))
    
    text_lower = text.lower()
    found_sev = [kw for kw in SEVERITY_KEYWORDS if kw.lower() in text_lower]
    
    sentiment_dir = "positive" if sentiment_score > 0 else ("negative" if sentiment_score < 0 else "neutral")
    
    explanation = f"Sentiment is {sentiment_dir} (score: {sentiment_score:.2f}). "
    explanation += f"Event '{event_type}' weight: {event_w}. "
    if found_sev:
        explanation += f"Severity keywords found: {', '.join(found_sev[:3])}."
    else:
        explanation += "No severity keywords found."
        
    return int(impact), explanation

def analyze_record(record: SignalRecord) -> list[AnalyzedSignal]:
    """Full pipeline: entity extraction + sentiment + event + impact. Returns one AnalyzedSignal per matched ticker."""
    return analyze_batch([record])

def analyze_batch(records: list[SignalRecord]) -> list[AnalyzedSignal]:
    """Process a batch efficiently (batched sentiment)."""
    if not records:
        return []
    
    # 1. Extract entities for all records
    entities_list = [extract_entities(r.text) for r in records]
    
    # 2. Batch sentiment analysis
    texts = [r.text for r in records]
    sentiments = analyze_sentiment(texts)
    
    analyzed_signals = []
    
    # 3. Classify events individually and 4. Compute impact
    for i, record in enumerate(records):
        entities = entities_list[i]
        sentiment_score, sentiment_confidence = sentiments[i]
        
        event_label, event_confidence = classify_event(record.text)
        impact, explanation = compute_impact(sentiment_score, event_label, record.text)
        
        for entity_name, ticker in entities:
            # Filter by TICKERS config if it's set and not empty, otherwise allow all
            if ticker != "MARKET" and TICKERS and ticker not in TICKERS:
                continue
                
            signal = AnalyzedSignal(
                id=f"{record.id}_{ticker}",
                entity=entity_name,
                ticker=ticker,
                source=record.source,
                timestamp=record.timestamp,
                text_snippet=record.text[:200],
                sentiment_score=sentiment_score,
                sentiment_confidence=sentiment_confidence,
                event_type=event_label,
                event_confidence=event_confidence,
                impact_score=impact,
                explanation=explanation
            )
            analyzed_signals.append(signal)
            
    return analyzed_signals

def write_signals(signals: list[AnalyzedSignal], append: bool = True) -> Path:
    """Append signals to OUTPUT_DIR / 'signals.jsonl'. Return the path."""
    output_path = OUTPUT_DIR / "signals.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    mode = "a" if append else "w"
    with open(output_path, mode, encoding="utf-8") as f:
        for signal in signals:
            data = dataclasses.asdict(signal) if dataclasses.is_dataclass(signal) else signal.__dict__
            f.write(json.dumps(data) + "\n")
            
    return output_path
