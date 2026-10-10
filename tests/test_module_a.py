"""
Tests for Module A (Rebalancer and Backtest).
"""
import pytest
import math
from module_a.rebalancer import water_fill_normalise, Rebalancer
from engine.config import WEIGHT_LOWER_BOUND, WEIGHT_UPPER_BOUND
from hypothesis import given, strategies as st
from typing import Dict

def test_water_fill_normalise_bounds():
    # 10 tickers
    tickers = [f"T{i}" for i in range(10)]
    
    # Case 1: All equal, within bounds
    raw = {t: 1.0 for t in tickers}
    norm = water_fill_normalise(raw)
    assert math.isclose(sum(norm.values()), 1.0, rel_tol=1e-9)
    for v in norm.values():
        assert WEIGHT_LOWER_BOUND <= v <= WEIGHT_UPPER_BOUND

    # Case 2: One is massive, should be clamped to upper
    raw = {t: 1.0 for t in tickers}
    raw["T0"] = 1000.0
    norm = water_fill_normalise(raw)
    assert math.isclose(sum(norm.values()), 1.0, rel_tol=1e-9)
    assert math.isclose(norm["T0"], WEIGHT_UPPER_BOUND, rel_tol=1e-9)
    
    # Case 3: One is tiny, should be clamped to lower
    raw = {t: 1.0 for t in tickers}
    raw["T0"] = 0.0001
    norm = water_fill_normalise(raw)
    assert math.isclose(sum(norm.values()), 1.0, rel_tol=1e-9)
    assert math.isclose(norm["T0"], WEIGHT_LOWER_BOUND, rel_tol=1e-9)

@given(
    st.lists(st.floats(min_value=0.01, max_value=100.0), min_size=15, max_size=15)
)
def test_water_fill_property(raw_vals):
    tickers = [f"T{i}" for i in range(15)]
    raw = {t: v for t, v in zip(tickers, raw_vals)}
    
    norm = water_fill_normalise(raw)
    assert math.isclose(sum(norm.values()), 1.0, rel_tol=1e-5)
    for v in norm.values():
        assert v >= WEIGHT_LOWER_BOUND - 1e-5
        assert v <= WEIGHT_UPPER_BOUND + 1e-5

def test_rebalancer_ewma_update():
    reb = Rebalancer(tickers=["AAPL", "MSFT"])
    reb.current_weights = {"AAPL": 0.5, "MSFT": 0.5}
    
    signals = [
        {"ticker": "AAPL", "sentiment_score": 1.0, "impact_score": 10},
    ]
    
    # ewma before
    assert reb.ewma["AAPL"] == 0.0
    reb.update_ewma(signals)
    # ewma after
    assert reb.ewma["AAPL"] > 0.0
    assert reb.ewma["MSFT"] == 0.0
