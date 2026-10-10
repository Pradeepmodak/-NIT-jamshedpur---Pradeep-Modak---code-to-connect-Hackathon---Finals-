"""
Playwright script to capture dashboard screenshots.
"""
import os
import sys
import time
from pathlib import Path

# We will use a mock capture if Playwright isn't installed.
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    from PIL import Image, ImageDraw, ImageFont

def main():
    docs_dir = Path("docs/screenshots")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    if HAS_PLAYWRIGHT:
        print("Using Playwright to capture screenshots...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            
            # Assuming streamlit is running on 8501
            try:
                page.goto("http://localhost:8501")
                page.wait_for_timeout(5000)  # Wait for load
                
                # Tab 1
                page.screenshot(path=str(docs_dir / "tab1_live_feed.png"))
                
                # Click Tab 2
                page.locator("text=Tactical Index").click()
                page.wait_for_timeout(2000)
                page.screenshot(path=str(docs_dir / "tab2_weights.png"))
                
                # Click Tab 3
                page.locator("text=Backtest").click()
                page.wait_for_timeout(2000)
                page.screenshot(path=str(docs_dir / "tab3_backtest.png"))
                
                # Click Tab 4
                page.locator("text=Analyze Text").click()
                page.wait_for_timeout(2000)
                page.screenshot(path=str(docs_dir / "tab4_analyze.png"))
            except Exception as e:
                print(f"Failed to capture with Playwright: {e}")
            finally:
                browser.close()
    else:
        print("Playwright not installed. Creating placeholder screenshots using Pillow.")
        for name in ["tab1_live_feed.png", "tab2_weights.png", "tab3_backtest.png", "tab4_analyze.png"]:
            img = Image.new('RGB', (1920, 1080), color = (30, 30, 30))
            d = ImageDraw.Draw(img)
            d.text((800, 500), f"Placeholder for {name}\nRun streamlit to view.", fill=(255, 255, 255))
            img.save(docs_dir / name)
            
    print(f"Screenshots saved to {docs_dir}")

if __name__ == "__main__":
    main()
