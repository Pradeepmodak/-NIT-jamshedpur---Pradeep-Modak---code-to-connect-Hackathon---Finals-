"""
Entity Extractor — maps free text to S&P 100 tickers using an alias
dictionary with word-boundary regex matching.

A single text can map to multiple tickers.  If no alias matches the text
is tagged as "MARKET".
"""
from __future__ import annotations

import logging
import re
from typing import List, Tuple

from engine.config import TICKER_ALIASES, TICKERS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-compile patterns once at module load
# ---------------------------------------------------------------------------
# $CASHTAG pattern — e.g. $AAPL, $MSFT
_CASHTAG_RE = re.compile(
    r"\$(" + "|".join(re.escape(t) for t in TICKERS) + r")\b",
    re.IGNORECASE,
)

# Alias patterns sorted longest-first so "bank of america" matches before "bank"
_SORTED_ALIASES: list[tuple[str, str, re.Pattern[str]]] = []
for _alias, _ticker in sorted(TICKER_ALIASES.items(), key=lambda x: -len(x[0])):
    _SORTED_ALIASES.append((
        _alias,
        _ticker,
        re.compile(r"\b" + re.escape(_alias) + r"\b", re.IGNORECASE),
    ))


def extract_entities(text: str) -> List[Tuple[str, str]]:
    """Return ``[(entity_name, ticker), ...]`` found in *text*.

    * Matches are deduplicated by ticker (first occurrence kept).
    * Results are sorted by position of first occurrence.
    * If nothing matches, returns ``[("MARKET", "MARKET")]``.
    """
    if not text or not text.strip():
        return [("MARKET", "MARKET")]

    hits: dict[str, tuple[str, int]] = {}  # ticker -> (entity_name, position)

    # 1. $CASHTAG matches
    for m in _CASHTAG_RE.finditer(text):
        ticker = m.group(1).upper()
        if ticker not in hits:
            hits[ticker] = (f"${ticker}", m.start())

    # 2. Alias matches
    for alias, ticker, pattern in _SORTED_ALIASES:
        if ticker in hits:
            continue  # already found via a different alias
        m = pattern.search(text)
        if m:
            hits[ticker] = (alias, m.start())

    if not hits:
        return [("MARKET", "MARKET")]

    # Sort by position in text
    results = sorted(hits.items(), key=lambda x: x[1][1])
    return [(entity_name, ticker) for ticker, (entity_name, _pos) in results]
