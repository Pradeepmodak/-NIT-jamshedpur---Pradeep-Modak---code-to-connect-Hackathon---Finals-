"""
FastAPI application — SentinelRisk REST API.

Endpoints
---------
GET  /health             → system health check
GET  /signals             → filtered signal list
GET  /signals/{ticker}    → signals for a specific ticker
POST /analyze             → analyze raw text and return signals
"""
from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from engine.config import OUTPUT_DIR, DEMO_MODE
from engine.ingestion.schema import SignalRecord, AnalyzedSignal
from engine.scoring.impact import analyze_record, write_signals

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SentinelRisk API",
    description="AI/NLP Financial Risk Signal Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory signal store (loaded from disk on startup)
_signals: List[dict] = []


def _load_signals_from_disk() -> None:
    """Load existing signals.jsonl into memory."""
    global _signals
    signals_file = OUTPUT_DIR / "signals.jsonl"
    if not signals_file.exists():
        return
    loaded = 0
    with open(signals_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    _signals.append(json.loads(line))
                    loaded += 1
                except json.JSONDecodeError as exc:
                    logger.warning("Skipping malformed signal line: %s", exc)
    logger.info("Loaded %d signals from %s", loaded, signals_file)


@app.on_event("startup")
async def _startup() -> None:
    _load_signals_from_disk()


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to analyze")


class HealthResponse(BaseModel):
    status: str
    demo_mode: bool
    timestamp: str
    signal_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health_check() -> dict:
    return {
        "status": "ok",
        "demo_mode": DEMO_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signal_count": len(_signals),
    }


@app.get("/signals")
def get_signals(
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    min_impact: Optional[int] = Query(None, ge=1, le=10, description="Minimum impact score"),
) -> List[dict]:
    """Return signals, optionally filtered by ticker and/or minimum impact."""
    results = _signals
    if ticker:
        t_upper = ticker.upper()
        results = [s for s in results if s.get("ticker", "").upper() == t_upper]
    if min_impact is not None:
        results = [s for s in results if s.get("impact_score", 0) >= min_impact]
    return results


@app.get("/signals/{ticker}")
def get_signals_by_ticker(ticker: str) -> List[dict]:
    """Return all signals for a specific ticker."""
    t_upper = ticker.upper()
    return [s for s in _signals if s.get("ticker", "").upper() == t_upper]


@app.post("/analyze")
def analyze_text(request: AnalyzeRequest) -> List[dict]:
    """Analyze raw text through the full NLP pipeline."""
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Text cannot be empty.")

    record = SignalRecord(
        id=uuid4().hex[:12],
        source="api",
        text=text,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    try:
        signals = analyze_record(record)
    except Exception as exc:
        logger.error("Analysis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal analysis error.")

    # Persist
    if signals:
        write_signals(signals, append=True)
        for sig in signals:
            d = dataclasses.asdict(sig)
            _signals.append(d)

    return [dataclasses.asdict(s) for s in signals]
