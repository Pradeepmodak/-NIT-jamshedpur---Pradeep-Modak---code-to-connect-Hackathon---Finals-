"""
Common schema for all ingested records.
Every data source normalises into SignalRecord before entering the NLP pipeline.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


@dataclass
class SignalRecord:
    """Raw ingested record — source-agnostic."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: str = ""          # "newsapi" | "tweet" | "manual"
    text: str = ""
    timestamp: str = ""       # ISO-8601 string

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SignalRecord":
        return cls(
            id=d.get("id", uuid.uuid4().hex[:12]),
            source=d.get("source", ""),
            text=d.get("text", ""),
            timestamp=d.get("timestamp", datetime.utcnow().isoformat()),
        )


@dataclass
class AnalyzedSignal:
    """Fully scored output record written to signals.jsonl."""
    id: str = ""
    entity: str = ""          # human-readable entity name
    ticker: str = ""          # mapped ticker or "MARKET"
    source: str = ""
    timestamp: str = ""
    text_snippet: str = ""
    sentiment_score: float = 0.0
    sentiment_confidence: float = 0.0
    event_type: str = "Other"
    event_confidence: float = 0.0
    impact_score: int = 1
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "AnalyzedSignal":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
