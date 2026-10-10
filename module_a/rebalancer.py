"""
Module A — Tactical Index Rebalancer.

Uses exponentially-weighted moving average (EWMA) of sentiment
(weighted by impact) to tilt portfolio weights away from equal-weight.

Weight formula:
    raw_weight = base_weight * exp(k * ewma_sentiment)
    → iterative water-filling: clamp violators, redistribute, repeat
    → final weights sum to 1, each in [WEIGHT_LOWER_BOUND, WEIGHT_UPPER_BOUND]
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from engine.config import (
    BASE_WEIGHT,
    EWMA_HALFLIFE,
    NUM_STOCKS,
    OUTPUT_DIR,
    REBALANCE_SENSITIVITY_K,
    SEED,
    TICKERS,
    WEIGHT_LOWER_BOUND,
    WEIGHT_SUM_TOLERANCE,
    WEIGHT_UPPER_BOUND,
)

logger = logging.getLogger(__name__)

# Decay factor from half-life: α = 1 - exp(-ln2 / halflife)
EWMA_ALPHA: float = 1.0 - math.exp(-math.log(2) / EWMA_HALFLIFE)


@dataclass
class WeightChange:
    """Record of a single weight change for a ticker."""
    date: str
    ticker: str
    old_weight: float
    new_weight: float
    reason_headline: str
    reason_impact: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def water_fill_normalise(
    raw_weights: Dict[str, float],
    lower: float = WEIGHT_LOWER_BOUND,
    upper: float = WEIGHT_UPPER_BOUND,
    tol: float = WEIGHT_SUM_TOLERANCE,
) -> Dict[str, float]:
    tickers = list(raw_weights.keys())
    n = len(tickers)
    if n == 0:
        return {}

    total = sum(raw_weights.values())
    if total <= 0:
        return {t: 1.0 / n for t in tickers}

    weights = {t: raw_weights[t] / total for t in tickers}
    clamped_set = set()
    
    max_iterations = 100
    for _ in range(max_iterations):
        changed = False
        
        # Identify violators not already clamped
        for t in tickers:
            if t not in clamped_set:
                if weights[t] > upper:
                    weights[t] = upper
                    clamped_set.add(t)
                    changed = True
                elif weights[t] < lower:
                    weights[t] = lower
                    clamped_set.add(t)
                    changed = True
                    
        if not changed:
            break
            
        unclamped = [t for t in tickers if t not in clamped_set]
        if not unclamped:
            break
            
        clamped_sum = sum(weights[t] for t in clamped_set)
        remaining = 1.0 - clamped_sum
        
        if remaining <= 0:
            # Overconstrained: distribute equally or just let it be
            per_unclamped = 0.0
        else:
            raw_unclamped_sum = sum(raw_weights[t] for t in unclamped)
            if raw_unclamped_sum <= 0:
                per_unclamped = remaining / len(unclamped)
                for t in unclamped:
                    weights[t] = per_unclamped
                continue
            else:
                for t in unclamped:
                    weights[t] = (raw_weights[t] / raw_unclamped_sum) * remaining
                    
    # Final safety normalize to exactly 1.0
    total_w = sum(weights.values())
    if abs(total_w - 1.0) > tol and total_w > 0:
        weights = {t: w / total_w for t, w in weights.items()}
        
    return weights


class Rebalancer:
    """Tactical index rebalancer using EWMA sentiment + impact tilting."""

    def __init__(
        self,
        tickers: List[str] | None = None,
        k: float = REBALANCE_SENSITIVITY_K,
        alpha: float = EWMA_ALPHA,
    ):
        self.tickers = tickers or TICKERS
        self.k = k
        self.alpha = alpha
        self.n = len(self.tickers)

        # State
        self.ewma: Dict[str, float] = {t: 0.0 for t in self.tickers}
        self.current_weights: Dict[str, float] = {
            t: BASE_WEIGHT for t in self.tickers
        }
        self.weight_history: List[Dict[str, float]] = []  # [{date: ..., AAPL: ..., ...}]
        self.weight_changes: List[WeightChange] = []
        self._date_index: List[str] = []

    def update_ewma(
        self,
        signals: List[dict],
    ) -> None:
        """Update EWMA sentiment for each ticker from a batch of signals.

        Each signal dict must have: ticker, sentiment_score, impact_score.
        The EWMA update is:
            ewma[t] = α * (sentiment * impact/10) + (1-α) * ewma[t]
        """
        # Aggregate signals per ticker (weighted by impact)
        ticker_updates: Dict[str, List[Tuple[float, float]]] = {
            t: [] for t in self.tickers
        }
        for sig in signals:
            ticker = sig.get("ticker", "")
            if ticker in ticker_updates:
                sent = float(sig.get("sentiment_score", 0.0))
                impact = float(sig.get("impact_score", 1))
                ticker_updates[ticker].append((sent, impact))

        for t in self.tickers:
            updates = ticker_updates[t]
            if updates:
                # Weighted average of sentiment * (impact/10) for this ticker
                weighted_sum = sum(s * (imp / 10.0) for s, imp in updates)
                count = len(updates)
                observation = weighted_sum / count
                self.ewma[t] = self.alpha * observation + (1 - self.alpha) * self.ewma[t]

    def compute_weights(self) -> Dict[str, float]:
        """Compute new weights from current EWMA state.

        raw_weight ∝ base_weight * exp(k * ewma)
        Then apply iterative water-filling normalisation.
        """
        raw = {}
        for t in self.tickers:
            raw[t] = BASE_WEIGHT * math.exp(self.k * self.ewma[t])
        return water_fill_normalise(raw)

    def rebalance(
        self,
        date: str,
        signals: List[dict],
    ) -> Dict[str, float]:
        """Run one rebalance cycle: update EWMA, compute weights, log changes.

        Parameters
        ----------
        date : str
            Date string for this rebalance (ISO format).
        signals : list[dict]
            Signals from the current window (each has ticker, sentiment_score,
            impact_score, text_snippet).

        Returns
        -------
        dict[str, float]
            New weights after rebalancing.
        """
        old_weights = dict(self.current_weights)
        self.update_ewma(signals)
        new_weights = self.compute_weights()

        # Find highest-impact signal per ticker for explanations
        ticker_top_signal: Dict[str, dict] = {}
        for sig in signals:
            t = sig.get("ticker", "")
            imp = sig.get("impact_score", 0)
            if t in new_weights:
                if t not in ticker_top_signal or imp > ticker_top_signal[t].get("impact_score", 0):
                    ticker_top_signal[t] = sig

        # Log changes
        for t in self.tickers:
            old_w = old_weights.get(t, BASE_WEIGHT)
            new_w = new_weights.get(t, BASE_WEIGHT)
            if abs(old_w - new_w) > 0.001:  # threshold for logging
                top_sig = ticker_top_signal.get(t, {})
                change = WeightChange(
                    date=date,
                    ticker=t,
                    old_weight=round(old_w, 6),
                    new_weight=round(new_w, 6),
                    reason_headline=top_sig.get("text_snippet", "No signal")[:150],
                    reason_impact=top_sig.get("impact_score", 0),
                )
                self.weight_changes.append(change)

        self.current_weights = new_weights
        weight_record = {"date": date, **{t: round(new_weights[t], 6) for t in self.tickers}}
        self.weight_history.append(weight_record)
        self._date_index.append(date)

        return new_weights

    def get_weight_history_df(self) -> pd.DataFrame:
        """Return weight history as a DataFrame."""
        if not self.weight_history:
            return pd.DataFrame()
        df = pd.DataFrame(self.weight_history)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df

    def save_weight_changes(self, path: Path | None = None) -> Path:
        """Save weight changes to JSONL."""
        path = path or OUTPUT_DIR / "weight_changes.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for change in self.weight_changes:
                f.write(json.dumps(change.to_dict()) + "\n")
        logger.info("Saved %d weight changes to %s", len(self.weight_changes), path)
        return path
