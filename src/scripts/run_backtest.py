"""
Run the full backtest pipeline end-to-end:
  1. Ingest sample data
  2. Analyze through NLP pipeline
  3. Write signals to signals.jsonl
  4. Run backtest
  5. Print results

    python scripts/run_backtest.py
"""
from __future__ import annotations

import json
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.config import LOG_FORMAT, OUTPUT_DIR, SEED

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def main() -> None:
    import numpy as np
    np.random.seed(SEED)

    logger.info("=== SentinelRisk Full Pipeline ===")

    # 1. Ingest
    logger.info("--- Step 1: Ingestion ---")
    from engine.ingestion.newsapi_client import fetch_headlines
    from engine.ingestion.tweet_loader import load_tweets

    news = fetch_headlines()
    tweets = load_tweets()
    all_records = news + tweets
    all_records.sort(key=lambda r: r.timestamp)
    logger.info("Ingested %d records (%d news, %d tweets)", len(all_records), len(news), len(tweets))

    # 2. Analyze
    logger.info("--- Step 2: NLP Analysis ---")
    from engine.scoring.impact import analyze_batch, write_signals

    # Clear previous output
    signals_path = OUTPUT_DIR / "signals.jsonl"
    if signals_path.exists():
        signals_path.unlink()

    # Process in batches of 32 for memory efficiency
    all_signals = []
    batch_size = 32
    for i in range(0, len(all_records), batch_size):
        batch = all_records[i:i + batch_size]
        signals = analyze_batch(batch)
        all_signals.extend(signals)
        logger.info("  Processed batch %d/%d (%d signals)",
                     i // batch_size + 1,
                     (len(all_records) + batch_size - 1) // batch_size,
                     len(signals))

    # Write signals
    write_signals(all_signals, append=False)
    logger.info("Wrote %d signals to %s", len(all_signals), signals_path)

    # 3. Backtest
    logger.info("--- Step 3: Backtest ---")
    from module_a.backtest import run_backtest
    import dataclasses

    signal_dicts = [dataclasses.asdict(s) for s in all_signals]
    results = run_backtest(signal_dicts)

    # 4. Print results
    logger.info("--- Results ---")
    if "error" not in results:
        dyn = results["dynamic"]
        ew = results["equal_weight"]
        print("\n" + "=" * 60)
        print("  SentinelRisk Backtest Results")
        print("=" * 60)
        print(f"  Replay window: {results.get('replay_start')} -> {results.get('replay_end')}")
        print(f"  Signals processed: {results.get('num_signals')}")
        print(f"  Total rebalances: {results.get('total_rebalances')}")
        print()
        print(f"  {'Metric':<30} {'Dynamic':>12} {'Equal-Weight':>14}")
        print(f"  {'-'*30} {'-'*12} {'-'*14}")
        print(f"  {'Total Return (%)':<30} {dyn['total_return_pct']:>12.2f} {ew['total_return_pct']:>14.2f}")
        print(f"  {'Ann. Volatility (%)':<30} {dyn['annualized_volatility_pct']:>12.2f} {ew['annualized_volatility_pct']:>14.2f}")
        print(f"  {'Sharpe Ratio':<30} {dyn['sharpe_ratio']:>12.4f} {ew['sharpe_ratio']:>14.4f}")
        print(f"  {'Max Drawdown (%)':<30} {dyn['max_drawdown_pct']:>12.2f} {ew['max_drawdown_pct']:>14.2f}")
        print(f"  {'Avg Turnover (%)':<30} {results.get('avg_turnover_pct', 0):>12.2f}")
        print("=" * 60)
    else:
        print(f"Backtest error: {results['error']}")

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
