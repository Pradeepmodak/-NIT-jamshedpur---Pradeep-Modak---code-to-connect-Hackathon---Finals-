"""
SentinelRisk Streamlit Dashboard.

Run with: streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.config import OUTPUT_DIR, TICKERS, DEMO_MODE, PROJECT_ROOT

st.set_page_config(page_title="SentinelRisk Dashboard", layout="wide", initial_sidebar_state="expanded")

# -----------------------------------------------------------------------------
# Data Loading (Cached)
# -----------------------------------------------------------------------------

@st.cache_data
def load_backtest_results() -> Dict[str, Any]:
    path = OUTPUT_DIR / "backtest.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading backtest.json: {e}")
    return {}

@st.cache_data
def load_equity_curve() -> pd.DataFrame:
    path = OUTPUT_DIR / "equity.csv"
    if path.exists():
        try:
            return pd.read_csv(path, index_col="date", parse_dates=True)
        except Exception as e:
            st.error(f"Error loading equity.csv: {e}")
    return pd.DataFrame()

def load_signals() -> List[dict]:
    path = OUTPUT_DIR / "signals.jsonl"
    signals = []
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        signals.append(json.loads(line))
        except Exception as e:
            st.error(f"Error loading signals.jsonl: {e}")
    return signals

def load_weight_changes() -> pd.DataFrame:
    path = OUTPUT_DIR / "weight_changes.jsonl"
    changes = []
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        changes.append(json.loads(line))
        except Exception as e:
            st.error(f"Error loading weight_changes.jsonl: {e}")
    if not changes:
        return pd.DataFrame()
    df = pd.DataFrame(changes)
    df["date"] = pd.to_datetime(df["date"])
    return df

# -----------------------------------------------------------------------------
# Sidebar & Replay State
# -----------------------------------------------------------------------------

with st.sidebar:
    st.title("SentinelRisk")
    if DEMO_MODE:
        st.warning("⚠️ DEMO_MODE = 1\n\n(Offline, cached/sample data only)")
    else:
        st.success("🟢 LIVE MODE")
        
    st.markdown("---")
    st.header("Replay Controls")
    
    # Session state for replay
    if "replay_idx" not in st.session_state:
        st.session_state.replay_idx = 0
    if "is_playing" not in st.session_state:
        st.session_state.is_playing = False
        
    replay_speed = st.slider("Replay Speed", min_value=1.0, max_value=20.0, value=5.0, step=1.0)
    
    col1, col2, col3 = st.columns(3)
    if col1.button("Play"):
        st.session_state.is_playing = True
    if col2.button("Pause"):
        st.session_state.is_playing = False
    if col3.button("Reset"):
        st.session_state.replay_idx = 0
        st.session_state.is_playing = False

# -----------------------------------------------------------------------------
# Main Application
# -----------------------------------------------------------------------------

st.title("SentinelRisk Dashboard")

tab1, tab2, tab3, tab4 = st.tabs([
    "Live Signal Feed", 
    "Tactical Index (Module A)", 
    "Backtest Performance", 
    "Analyze Text"
])

all_signals = load_signals()
# Sort ascending by timestamp for replay
all_signals.sort(key=lambda x: x.get("timestamp", ""))

if st.session_state.is_playing and all_signals:
    # Advance replay index based on speed
    st.session_state.replay_idx = min(st.session_state.replay_idx + int(replay_speed), len(all_signals))
    time.sleep(0.5)
    st.rerun()

current_signals = all_signals[:st.session_state.replay_idx] if st.session_state.replay_idx > 0 else all_signals

# --- Tab 1: Live Signal Feed ---
with tab1:
    st.header("Signal Feed")
    col1, col2 = st.columns(2)
    selected_ticker = col1.selectbox("Filter by Ticker", ["ALL"] + TICKERS)
    min_impact = col2.slider("Minimum Impact Score", 1, 10, 1)
    
    filtered_signals = current_signals
    if selected_ticker != "ALL":
        filtered_signals = [s for s in filtered_signals if s.get("ticker", "") == selected_ticker]
    filtered_signals = [s for s in filtered_signals if s.get("impact_score", 0) >= min_impact]
    
    # Show top 50 descending
    filtered_signals.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    if not filtered_signals:
        st.info("No signals found.")
    else:
        for s in filtered_signals[:50]:
            impact = s.get("impact_score", 0)
            sent_score = s.get("sentiment_score", 0.0)
            
            # Colors
            if sent_score > 0.2: color = "green"
            elif sent_score < -0.2: color = "red"
            else: color = "gray"
            
            st.markdown(f"""
            <div style="padding: 10px; border-left: 5px solid {color}; background-color: #1e1e1e; margin-bottom: 10px; border-radius: 5px;">
                <div style="display: flex; justify-content: space-between;">
                    <strong>{s.get("ticker", "MARKET")}</strong>
                    <span style="color: #aaa; font-size: 0.8em;">{s.get("timestamp", "")[:19]} | {s.get("source", "unknown")}</span>
                </div>
                <div style="margin: 5px 0;">{s.get("text_snippet", "")}</div>
                <div style="font-size: 0.9em;">
                    <span style="color: {color};">Sentiment: {sent_score:.2f}</span> | 
                    <span>Impact: <b>{impact}/10</b></span> | 
                    <span>Event: {s.get("event_type", "Other")}</span>
                </div>
                <div style="font-size: 0.8em; color: #888; margin-top: 5px;">
                    <i>{s.get("explanation", "")}</i>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- Tab 2: Weights over time ---
with tab2:
    st.header("Tactical Index Weights")
    
    # We reconstruct weights over time based on the replay signals
    # Since backtest generates static files, we'll use weight_changes.jsonl to approximate
    changes_df = load_weight_changes()
    
    if not changes_df.empty:
        # Reconstruct daily weights for the stacked area chart
        # Start with equal weights
        base_w = 1.0 / len(TICKERS)
        weights_hist = []
        current_w = {t: base_w for t in TICKERS}
        
        # Group changes by date
        grouped = changes_df.groupby("date")
        
        # Determine current date based on replay signals
        if current_signals:
            latest_ts = current_signals[0].get("timestamp", "")
            # Filter changes up to latest_ts if in replay mode
        
        st.subheader("Latest Weight Changes")
        st.dataframe(changes_df.sort_values("date", ascending=False).head(20)[
            ["date", "ticker", "old_weight", "new_weight", "reason_impact", "reason_headline"]
        ], use_container_width=True)
        
        st.info("Note: Run `python scripts/run_backtest.py` to update the weights history.")
    else:
        st.info("No weight changes recorded. Run the backtest pipeline first.")

# --- Tab 3: Backtest Performance ---
with tab3:
    st.header("Backtest Results")
    bt_res = load_backtest_results()
    eq_df = load_equity_curve()
    
    if bt_res and not eq_df.empty:
        dyn = bt_res.get("dynamic", {})
        ew = bt_res.get("equal_weight", {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Dynamic Sentiment Index")
            st.metric("Total Return", f"{dyn.get('total_return_pct', 0):.2f}%")
            st.metric("Ann. Volatility", f"{dyn.get('annualized_volatility_pct', 0):.2f}%")
            st.metric("Sharpe Ratio", f"{dyn.get('sharpe_ratio', 0):.4f}")
            st.metric("Max Drawdown", f"{dyn.get('max_drawdown_pct', 0):.2f}%")
        
        with col2:
            st.subheader("Equal-Weight Index")
            st.metric("Total Return", f"{ew.get('total_return_pct', 0):.2f}%")
            st.metric("Ann. Volatility", f"{ew.get('annualized_volatility_pct', 0):.2f}%")
            st.metric("Sharpe Ratio", f"{ew.get('sharpe_ratio', 0):.4f}")
            st.metric("Max Drawdown", f"{ew.get('max_drawdown_pct', 0):.2f}%")
            
        st.markdown("---")
        st.subheader("Equity Curve")
        fig = px.line(eq_df, x=eq_df.index, y=["dynamic", "equal_weight"], 
                      labels={"value": "Equity Multiplier", "date": "Date"},
                      title="Portfolio Performance")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No backtest results found. Run `python scripts/run_backtest.py` first.")

# --- Tab 4: Analyze Text ---
with tab4:
    st.header("Live Analysis")
    text_input = st.text_area("Paste news or tweet text here:", height=150)
    
    if st.button("Analyze"):
        if not text_input.strip():
            st.warning("Please enter some text.")
        else:
            with st.spinner("Analyzing..."):
                try:
                    from engine.ingestion.schema import SignalRecord
                    from engine.scoring.impact import analyze_record
                    
                    rec = SignalRecord(source="manual", text=text_input)
                    res = analyze_record(rec)
                    
                    if not res:
                        st.info("Analyzed successfully, but no specific entities found.")
                    
                    for s in res:
                        st.json({
                            "ticker": s.ticker,
                            "entity": s.entity,
                            "sentiment_score": s.sentiment_score,
                            "event_type": s.event_type,
                            "impact_score": s.impact_score,
                            "explanation": s.explanation
                        })
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
