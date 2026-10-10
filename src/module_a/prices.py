"""
Module A — Price data fetcher with disk caching.

Uses yfinance for historical daily closes.  Falls back to cached CSVs
or synthetic data when offline / DEMO_MODE.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from engine.config import (
    CACHE_DIR,
    DEMO_MODE,
    REPLAY_END,
    REPLAY_START,
    SEED,
    TICKERS,
)

logger = logging.getLogger(__name__)

_PRICE_CACHE_FILE = CACHE_DIR / "prices.csv"


def _generate_synthetic_prices(
    tickers: list[str],
    start: str,
    end: str,
) -> pd.DataFrame:
    """Generate synthetic daily prices for demo/offline use.

    Uses geometric Brownian motion seeded with SEED for determinism.
    """
    rng = np.random.RandomState(SEED)
    dates = pd.bdate_range(start=start, end=end)
    n_days = len(dates)

    data: dict[str, list[float]] = {}
    # Base prices that look plausible
    base_prices = {
        "AAPL": 190.0, "MSFT": 420.0, "AMZN": 180.0, "GOOGL": 175.0,
        "META": 480.0, "NVDA": 120.0, "JPM": 195.0, "BAC": 38.0,
        "XOM": 110.0, "JNJ": 155.0, "PG": 165.0, "KO": 62.0,
        "WMT": 67.0, "DIS": 102.0, "TSLA": 180.0,
    }
    for ticker in tickers:
        price = base_prices.get(ticker, 100.0)
        prices = [price]
        for _ in range(n_days - 1):
            ret = rng.normal(0.0003, 0.018)  # ~7% annual return, ~28% vol
            price = price * (1 + ret)
            prices.append(round(price, 2))
        data[ticker] = prices

    df = pd.DataFrame(data, index=dates)
    df.index.name = "Date"
    return df


def fetch_prices(
    tickers: list[str] | None = None,
    start: str | None = None,
    end: str | None = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Fetch daily closing prices for *tickers* over [start, end].

    Priority:
      1. Disk cache (if exists and not force_refresh)
      2. yfinance download (if not DEMO_MODE)
      3. Synthetic prices (deterministic, SEED=42)
    """
    tickers = tickers or TICKERS
    start = start or REPLAY_START
    end = end or REPLAY_END

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Try disk cache
    if _PRICE_CACHE_FILE.exists() and not force_refresh:
        try:
            df = pd.read_csv(_PRICE_CACHE_FILE, index_col="Date", parse_dates=True)
            # Check if we have all requested tickers
            missing = [t for t in tickers if t not in df.columns]
            if not missing:
                mask = (df.index >= start) & (df.index <= end)
                result = df.loc[mask, tickers]
                if len(result) > 0:
                    logger.info(
                        "Loaded prices from cache: %d days, %d tickers",
                        len(result), len(tickers),
                    )
                    return result
            else:
                logger.info("Cache missing tickers %s, will re-fetch", missing)
        except Exception as exc:
            logger.warning("Cache read failed: %s", exc)

    # 2. Try yfinance (skip in DEMO_MODE)
    if not DEMO_MODE:
        try:
            import yfinance as yf

            logger.info("Downloading prices from yfinance: %s", tickers)
            df = yf.download(
                tickers,
                start=start,
                end=end,
                auto_adjust=True,
                progress=False,
            )
            # yfinance returns MultiIndex columns for multiple tickers
            if isinstance(df.columns, pd.MultiIndex):
                df = df["Close"]
            elif len(tickers) == 1:
                df = df[["Close"]].rename(columns={"Close": tickers[0]})

            df = df.dropna(how="all")
            if len(df) > 0:
                df.index.name = "Date"
                # Save to cache
                df.to_csv(_PRICE_CACHE_FILE)
                logger.info(
                    "Downloaded and cached %d days of prices", len(df)
                )
                return df[tickers]
        except Exception as exc:
            logger.warning("yfinance download failed: %s", exc)

    # 3. Synthetic fallback
    logger.info("Using synthetic prices (SEED=%d)", SEED)
    df = _generate_synthetic_prices(tickers, start, end)
    # Cache the synthetic data too
    df.to_csv(_PRICE_CACHE_FILE)
    return df


def get_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute simple daily returns from price DataFrame."""
    return prices.pct_change().dropna()
