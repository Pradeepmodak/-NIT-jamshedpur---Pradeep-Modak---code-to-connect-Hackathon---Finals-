"""
Module A — Backtester.

Compares the dynamic (sentiment-tilted) index against equal-weight
over the replay window.  No look-ahead: weights decided with signals
up to day t-1 are applied to day t returns.

Outputs:
  data/output/backtest.json   — summary metrics
  data/output/equity.csv      — daily equity curves
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from engine.config import (
    BASE_WEIGHT,
    OUTPUT_DIR,
    REPLAY_END,
    REPLAY_START,
    SEED,
    TICKERS,
    TRANSACTION_COST_BPS,
)
from module_a.prices import fetch_prices, get_returns
from module_a.rebalancer import Rebalancer

logger = logging.getLogger(__name__)


def _compute_metrics(equity: pd.Series, name: str) -> Dict[str, Any]:
    """Compute return, volatility, Sharpe, max drawdown from an equity curve."""
    returns = equity.pct_change().dropna()
    total_return = float((equity.iloc[-1] / equity.iloc[0]) - 1)
    n_days = len(returns)
    ann_factor = 252

    vol_daily = float(returns.std())
    vol_annual = vol_daily * np.sqrt(ann_factor)

    mean_daily = float(returns.mean())
    sharpe = (mean_daily / vol_daily * np.sqrt(ann_factor)) if vol_daily > 0 else 0.0

    # Max drawdown
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    max_dd = float(drawdown.min())

    return {
        "name": name,
        "total_return_pct": round(total_return * 100, 4),
        "annualized_volatility_pct": round(vol_annual * 100, 4),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown_pct": round(max_dd * 100, 4),
        "trading_days": n_days,
    }


def run_backtest(
    signals: List[dict],
    tickers: List[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    rebalance_interval: int = 1,
    transaction_cost_bps: float = TRANSACTION_COST_BPS,
) -> Dict[str, Any]:
    """Run the full backtest.

    Parameters
    ----------
    signals : list[dict]
        Pre-computed signals (each with ticker, sentiment_score, impact_score,
        timestamp, text_snippet).
    tickers : list[str], optional
        Tickers to include (default: config.TICKERS).
    start, end : str, optional
        Date range (default: config.REPLAY_START/END).
    rebalance_interval : int
        Rebalance every N trading days.
    transaction_cost_bps : float
        Transaction cost in basis points per unit turnover.

    Returns
    -------
    dict with keys: dynamic_metrics, equalweight_metrics, avg_turnover,
    equity_path, backtest_path.
    """
    tickers = tickers or TICKERS
    start = start or REPLAY_START
    end = end or REPLAY_END

    # Fetch prices and compute returns
    prices = fetch_prices(tickers, start, end)
    returns = get_returns(prices)
    dates = returns.index

    if len(dates) == 0:
        logger.error("No trading days in [%s, %s]", start, end)
        return {"error": "No trading days found"}

    logger.info("Backtest: %d trading days, %d tickers", len(dates), len(tickers))

    # Group signals by date
    from datetime import datetime
    signal_by_date: Dict[str, List[dict]] = {}
    for sig in signals:
        ts = sig.get("timestamp", "")
        try:
            dt = pd.Timestamp(ts).normalize()
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            continue
        if date_str not in signal_by_date:
            signal_by_date[date_str] = []
        signal_by_date[date_str].append(sig)

    # Initialize rebalancer
    rebalancer = Rebalancer(tickers=tickers)

    # Equal-weight portfolio
    eq_weights = {t: 1.0 / len(tickers) for t in tickers}

    # Track equity curves
    dynamic_equity = [1.0]
    equalweight_equity = [1.0]
    turnovers: List[float] = []

    prev_dynamic_weights = {t: BASE_WEIGHT for t in tickers}

    for day_idx, date in enumerate(dates):
        date_str = date.strftime("%Y-%m-%d")
        day_returns = returns.loc[date]

        # ----- Equal-weight portfolio -----
        eq_ret = sum(eq_weights[t] * day_returns.get(t, 0.0) for t in tickers)
        equalweight_equity.append(equalweight_equity[-1] * (1 + eq_ret))

        # ----- Dynamic portfolio -----
        # No look-ahead: use YESTERDAY's weights for TODAY's returns
        dyn_ret = sum(prev_dynamic_weights[t] * day_returns.get(t, 0.0) for t in tickers)

        # Rebalance check (using signals from previous day)
        if day_idx > 0 and day_idx % rebalance_interval == 0:
            # Collect signals up to yesterday
            prev_date_str = dates[day_idx - 1].strftime("%Y-%m-%d")
            window_signals = signal_by_date.get(prev_date_str, [])
            if window_signals:
                new_weights = rebalancer.rebalance(prev_date_str, window_signals)

                # Compute turnover
                turnover = sum(abs(new_weights.get(t, 0) - prev_dynamic_weights.get(t, 0)) for t in tickers) / 2
                turnovers.append(turnover)

                # Apply transaction cost
                tc = turnover * (transaction_cost_bps / 10000.0)
                dyn_ret -= tc

                prev_dynamic_weights = new_weights

        dynamic_equity.append(dynamic_equity[-1] * (1 + dyn_ret))

    # Build equity DataFrames
    equity_dates = [dates[0] - pd.Timedelta(days=1)] + list(dates)
    equity_df = pd.DataFrame({
        "date": equity_dates,
        "dynamic": dynamic_equity,
        "equal_weight": equalweight_equity,
    })
    equity_df = equity_df.set_index("date")

    # Metrics
    dynamic_metrics = _compute_metrics(
        pd.Series(dynamic_equity, index=equity_dates), "Dynamic Sentiment Index"
    )
    ew_metrics = _compute_metrics(
        pd.Series(equalweight_equity, index=equity_dates), "Equal-Weight Index"
    )

    avg_turnover = float(np.mean(turnovers)) if turnovers else 0.0

    # Save results
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    equity_path = OUTPUT_DIR / "equity.csv"
    equity_df.to_csv(equity_path)
    logger.info("Saved equity curves to %s", equity_path)

    backtest_result = {
        "dynamic": dynamic_metrics,
        "equal_weight": ew_metrics,
        "avg_turnover_pct": round(avg_turnover * 100, 4),
        "total_rebalances": len(turnovers),
        "replay_start": start,
        "replay_end": end,
        "num_signals": len(signals),
    }

    backtest_path = OUTPUT_DIR / "backtest.json"
    with open(backtest_path, "w", encoding="utf-8") as f:
        json.dump(backtest_result, f, indent=2, default=str)
    logger.info("Saved backtest results to %s", backtest_path)

    # Save weight changes
    rebalancer.save_weight_changes()

    return {
        **backtest_result,
        "equity_path": str(equity_path),
        "backtest_path": str(backtest_path),
    }
