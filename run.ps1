# Install dependencies
pip install -r requirements.txt

# Setup environment if it doesn't exist
if (-Not (Test-Path .env)) {
    Copy-Item .env.example .env
}

# Warm the cache
python scripts/warm_cache.py

# Run the Backtest Pipeline
python scripts/run_backtest.py

# Generate Presentation
python scripts/make_ppt.py

# Launch the Dashboard
streamlit run dashboard/app.py
