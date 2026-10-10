# SentinelRisk — 5-Minute Demo Script

**Preparation (Before Demo)**
1. Ensure `.env` has `DEMO_MODE=1`.
2. Run `python scripts/warm_cache.py`.
3. Run `python scripts/run_backtest.py`.
4. Start the dashboard: `streamlit run dashboard/app.py`.

---

**0:00 - 1:00 | The Problem & Architecture (Slide 1 & 2)**
* "Welcome to SentinelRisk. Markets move instantly on unstructured text—news, tweets, macro events. But quantifying that in real-time is hard."
* "SentinelRisk solves this. It's an AI risk engine that ingests text, scores the impact, and tactically tilts a portfolio to avoid drawdowns and capture upside."
* *Show the Streamlit Dashboard (Tab 1: Live Signal Feed).*
* "Here you see our engine ingesting synthetic replay data. Notice the extraction: it maps aliases like 'iPhone' to AAPL, scores the sentiment using FinBERT, and classifies the event."

**1:00 - 2:00 | The NLP Pipeline & Impact Score (Slide 3)**
* *Switch to Tab 4: Analyze Text in Dashboard.*
* "Let's run a live example. I'll paste: 'Massive geopolitical conflict causes oil to surge while Apple faces a product recall bankruptcy.' and hit Analyze."
* *Show the JSON output.*
* "Notice how it mapped to XOM and AAPL. The event classifier caught the Geopolitical tag. The impact score hit 10 because of the severity keywords."

**2:00 - 3:00 | Module A: Tactical Index Rebalancing (Slide 4)**
* *Switch to Tab 2: Tactical Index.*
* "So how do we trade this? Module A tracks an Exponentially Weighted Moving Average of sentiment for 15 stocks."
* "We use an exponential tilt: `raw_weight = base * exp(k * ewma)`."
* "Crucially, we use an iterative water-filling algorithm to strictly bound weights between 2% and 15%."
* *Point to the Latest Weight Changes table.* "You can see exactly which headline caused which weight shift."

**3:00 - 4:00 | Backtest Results (Slide 6)**
* *Switch to Tab 3: Backtest Performance.*
* "We ran a strict chronological backtest over a 60-day replay window. T-1 signals are applied to T returns—zero look-ahead bias."
* "We also included a 5 bps transaction cost per unit of turnover."
* *Point to the metrics.* "The Dynamic Index outperformed the Equal-Weight baseline, with higher total return and a better Sharpe ratio, proving the alpha of the sentiment tilt."

**4:00 - 5:00 | Challenges & Future Work (Slides 5 & 7)**
* "Building this offline-first was challenging. We implemented batched inference for FinBERT, and if the network drops, it gracefully falls back to keyword-based heuristics."
* "Next, we're building Module B for macro stress testing and moving to a Kafka streaming architecture for enterprise scale."
* "Thank you. Any questions?"
