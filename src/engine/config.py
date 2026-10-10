"""
SentinelRisk — Central Configuration
All tunable constants, model names, ticker lists, alias dictionaries,
scoring weights, and path conventions live here.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Global seed for reproducibility
# ---------------------------------------------------------------------------
SEED: int = 42

# ---------------------------------------------------------------------------
# Paths (relative to project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
SAMPLES_DIR: Path = DATA_DIR / "samples"
CACHE_DIR: Path = DATA_DIR / "cache"
OUTPUT_DIR: Path = DATA_DIR / "output"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
SCREENSHOTS_DIR: Path = DOCS_DIR / "screenshots"

# Ensure output dir exists at import time
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Environment flags
# ---------------------------------------------------------------------------
DEMO_MODE: bool = os.getenv("DEMO_MODE", "0") == "1"
NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "")

# ---------------------------------------------------------------------------
# Tickers & alias dictionary
# ---------------------------------------------------------------------------
TICKERS: list[str] = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META",
    "NVDA", "JPM", "BAC", "XOM", "JNJ",
    "PG", "KO", "WMT", "DIS", "TSLA",
]

# Maps lowercase alias → ticker.  Includes company names, products, cashtags.
TICKER_ALIASES: dict[str, str] = {
    # AAPL
    "apple": "AAPL", "iphone": "AAPL", "ipad": "AAPL", "macbook": "AAPL",
    "aapl": "AAPL", "$aapl": "AAPL", "tim cook": "AAPL",
    # MSFT
    "microsoft": "MSFT", "azure": "MSFT", "windows": "MSFT", "msft": "MSFT",
    "$msft": "MSFT", "satya nadella": "MSFT", "xbox": "MSFT",
    # AMZN
    "amazon": "AMZN", "aws": "AMZN", "amzn": "AMZN", "$amzn": "AMZN",
    "jeff bezos": "AMZN", "andy jassy": "AMZN", "prime video": "AMZN",
    # GOOGL
    "google": "GOOGL", "alphabet": "GOOGL", "googl": "GOOGL", "$googl": "GOOGL",
    "youtube": "GOOGL", "sundar pichai": "GOOGL", "waymo": "GOOGL",
    "deepmind": "GOOGL", "gemini": "GOOGL",
    # META
    "meta": "META", "facebook": "META", "instagram": "META", "whatsapp": "META",
    "$meta": "META", "mark zuckerberg": "META", "zuckerberg": "META",
    "meta platforms": "META",
    # NVDA
    "nvidia": "NVDA", "nvda": "NVDA", "$nvda": "NVDA", "jensen huang": "NVDA",
    "geforce": "NVDA", "cuda": "NVDA",
    # JPM
    "jpmorgan": "JPM", "jp morgan": "JPM", "jpm": "JPM", "$jpm": "JPM",
    "jamie dimon": "JPM", "chase": "JPM", "j.p. morgan": "JPM",
    # BAC
    "bank of america": "BAC", "bofa": "BAC", "bac": "BAC", "$bac": "BAC",
    "merrill lynch": "BAC",
    # XOM
    "exxon": "XOM", "exxonmobil": "XOM", "exxon mobil": "XOM",
    "xom": "XOM", "$xom": "XOM",
    # JNJ
    "johnson & johnson": "JNJ", "johnson and johnson": "JNJ",
    "j&j": "JNJ", "jnj": "JNJ", "$jnj": "JNJ",
    # PG
    "procter & gamble": "PG", "procter and gamble": "PG", "p&g": "PG",
    "pg": "PG", "$pg": "PG",
    # KO
    "coca-cola": "KO", "coca cola": "KO", "coke": "KO",
    "ko": "KO", "$ko": "KO",
    # WMT
    "walmart": "WMT", "wal-mart": "WMT", "wmt": "WMT", "$wmt": "WMT",
    # DIS
    "disney": "DIS", "walt disney": "DIS", "dis": "DIS", "$dis": "DIS",
    "disney+": "DIS", "disney plus": "DIS",
    # TSLA
    "tesla": "TSLA", "tsla": "TSLA", "$tsla": "TSLA", "elon musk": "TSLA",
    "musk": "TSLA", "cybertruck": "TSLA",
}

# ---------------------------------------------------------------------------
# Scoring weights — Impact Score Formula
# impact = clip(round(10 * (W_SENT*|sentiment| + W_EVT*event_weight
#                           + W_SEV*severity_keyword_score)), 1, 10)
# ---------------------------------------------------------------------------
W_SENT: float = 0.40
W_EVT: float = 0.35
W_SEV: float = 0.25

EVENT_WEIGHT: dict[str, float] = {
    "Geopolitical":        0.90,
    "Credit Event":        0.85,
    "Macroeconomic":       0.80,
    "Merger/Acquisition":  0.70,
    "Product Launch":      0.50,
    "Other":               0.30,
}

# Keywords for rule-based event classification
EVENT_KEYWORDS: dict[str, list[str]] = {
    "Geopolitical": [
        "war", "sanctions", "tariff", "embargo", "geopolit", "military",
        "invasion", "treaty", "nato", "diplomatic", "conflict", "weapons",
        "nuclear", "troops", "border",
    ],
    "Macroeconomic": [
        "fed ", "federal reserve", "interest rate", "inflation", "gdp",
        "unemployment", "recession", "cpi", "monetary policy", "rate hike",
        "rate cut", "fiscal", "stimulus", "treasury", "yield curve",
        "central bank", "fomc",
    ],
    "Credit Event": [
        "default", "bankruptcy", "debt", "downgrade", "credit rating",
        "restructuring", "insolvency", "chapter 11", "liquidation",
        "credit crisis", "bond", "junk",
    ],
    "Merger/Acquisition": [
        "merger", "acquisition", "acquire", "takeover", "buyout", "ipo",
        "spinoff", "spin-off", "deal", "bid", "hostile", "joint venture",
    ],
    "Product Launch": [
        "launch", "unveil", "announce", "release", "introduce", "debut",
        "new product", "rollout", "upgrade", "next-gen", "innovation",
    ],
}
EVENT_RULE_CONFIDENCE_THRESHOLD: float = 0.60

# Severity keywords for impact scoring
SEVERITY_KEYWORDS: list[str] = [
    "crash", "surge", "plunge", "soar", "bankrupt", "bankruptcy", "crisis",
    "catastroph", "scandal", "fraud", "investigation", "sec ", "lawsuit",
    "recall", "record high", "record low", "all-time", "halt", "suspend",
    "layoff", "fire", "restructur", "warning", "downgrade", "upgrade",
    "beat", "miss", "disappoint", "exceed", "skyrocket", "tank", "tumble",
    "rally", "boom", "bust", "volatile", "spike", "collapse", "explode",
]

# ---------------------------------------------------------------------------
# NLP model names (Hugging Face)
# ---------------------------------------------------------------------------
FINBERT_MODEL: str = "ProsusAI/finbert"
ZEROSHOT_MODEL: str = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
SENTIMENT_BATCH_SIZE: int = 16

# ---------------------------------------------------------------------------
# Module A — Rebalancer
# ---------------------------------------------------------------------------
NUM_STOCKS: int = len(TICKERS)
BASE_WEIGHT: float = 1.0 / NUM_STOCKS

EWMA_HALFLIFE: int = 5                 # days; decay α = 1 - exp(-ln2/halflife)
REBALANCE_SENSITIVITY_K: float = 1.5   # exp(k * ewma) tilt
WEIGHT_LOWER_BOUND: float = 0.02       # 2 %
WEIGHT_UPPER_BOUND: float = 0.15       # 15 %
WEIGHT_SUM_TOLERANCE: float = 1e-9
REBALANCE_INTERVAL_DAYS: int = 1       # daily
TRANSACTION_COST_BPS: float = 5.0      # 5 basis points per unit turnover

# ---------------------------------------------------------------------------
# Replay / backtest window (fixed for determinism)
# ---------------------------------------------------------------------------
REPLAY_START: str = "2024-06-01"
REPLAY_END: str = "2024-08-30"         # ~60 trading days

# ---------------------------------------------------------------------------
# API / server
# ---------------------------------------------------------------------------
API_HOST: str = "0.0.0.0"
API_PORT: int = 8000
STREAMLIT_PORT: int = 8501

# ---------------------------------------------------------------------------
# Logging format
# ---------------------------------------------------------------------------
LOG_FORMAT: str = "%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
