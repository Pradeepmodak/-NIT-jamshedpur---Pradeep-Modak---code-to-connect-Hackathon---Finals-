@echo off
REM Install dependencies
pip install -r requirements.txt

REM Setup environment if it doesn't exist
if not exist .env (
    copy .env.example .env
)

REM Warm the cache
python scripts/warm_cache.py

REM Run the Backtest Pipeline
python scripts/run_backtest.py

REM Generate Presentation
python scripts/make_ppt.py

REM Launch the Dashboard
streamlit run dashboard/app.py
