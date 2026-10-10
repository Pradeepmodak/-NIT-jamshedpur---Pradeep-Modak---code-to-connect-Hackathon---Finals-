"""
Tests for the SentinelRisk Engine.
"""
import pytest
from engine.nlp.entity_extractor import extract_entities
from engine.nlp.sentiment import _keyword_sentiment, analyze_sentiment
from engine.nlp.event_classifier import classify_event, _rule_classify
from engine.scoring.impact import compute_impact
from hypothesis import given, strategies as st

def test_entity_extraction_multi_ticker():
    text = "Apple and Microsoft reported earnings. $AMZN also did well."
    entities = extract_entities(text)
    tickers = {t[1] for t in entities}
    assert "AAPL" in tickers
    assert "MSFT" in tickers
    assert "AMZN" in tickers
    assert "MARKET" not in tickers

def test_entity_extraction_cashtags():
    text = "Buying $TSLA and $NVDA"
    entities = extract_entities(text)
    tickers = {t[1] for t in entities}
    assert "TSLA" in tickers
    assert "NVDA" in tickers

def test_entity_extraction_no_match():
    text = "The quick brown fox jumps over the lazy dog."
    entities = extract_entities(text)
    assert len(entities) == 1
    assert entities[0] == ("MARKET", "MARKET")

def test_sentiment_bounds():
    s, c = _keyword_sentiment("Apple surges and jumps to record high!")
    assert 0 <= s <= 1
    
    s, c = _keyword_sentiment("Market crashes and falls into bankruptcy")
    assert -1 <= s <= 0

    s, c = _keyword_sentiment("random words with no meaning")
    assert s == 0.0

@given(
    sentiment=st.floats(min_value=-1.0, max_value=1.0),
)
def test_impact_score_bounds(sentiment):
    impact, expl = compute_impact(sentiment, "Other", "Some text")
    assert 1 <= impact <= 10

def test_impact_score_logic():
    # Max sentiment, max event, max severity
    impact, expl = compute_impact(1.0, "Geopolitical", "crash surge bankrupt crisis scandal")
    assert impact == 10
    
    # Zero everything
    impact, expl = compute_impact(0.0, "Other", "hello world")
    assert impact == 1
