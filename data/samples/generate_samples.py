import json
import csv
import random
import os
from datetime import datetime, timedelta

random.seed(42)

tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "JPM", "BAC", "XOM", "JNJ", "PG", "KO", "WMT", "DIS", "TSLA"]
companies = {
    "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon", "GOOGL": "Google", "META": "Meta",
    "NVDA": "Nvidia", "JPM": "JPMorgan", "BAC": "Bank of America", "XOM": "ExxonMobil",
    "JNJ": "Johnson & Johnson", "PG": "Procter & Gamble", "KO": "Coca-Cola", "WMT": "Walmart",
    "DIS": "Disney", "TSLA": "Tesla"
}

events = ["Geopolitical", "Macroeconomic", "Credit Event", "Merger/Acquisition", "Product Launch", "Other"]
sentiments = ["positive", "negative"]
start_date = datetime(2024, 6, 1)
end_date = datetime(2024, 8, 30)

def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def generate_news():
    news_data = []
    
    # At least 2 per ticker
    news_id = 1
    for ticker in tickers:
        for _ in range(3):
            dt = random_date(start_date, end_date)
            event = random.choice(events)
            sent = random.choice(sentiments)
            
            if sent == "positive":
                texts = [
                    f"{companies[ticker]} ({ticker}) shares surge on positive {event.lower()} news.",
                    f"Strong quarterly results expected for {companies[ticker]} following recent {event.lower()}.",
                    f"Analysts upgrade {ticker} citing strong demand and successful {event.lower()}."
                ]
            else:
                texts = [
                    f"{companies[ticker]} ({ticker}) faces headwinds due to unexpected {event.lower()} delays.",
                    f"Market reacts negatively to {ticker} amid broader {event.lower()} concerns.",
                    f"Regulatory scrutiny pressures {companies[ticker]} shares after a recent {event.lower()}."
                ]
                
            news_data.append({
                "id": f"news_{news_id:03d}",
                "source": "newsapi",
                "text": random.choice(texts),
                "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            })
            news_id += 1

    # Market wide
    market_texts = [
        "Federal Reserve issues unexpected statement on interest rates.",
        "Global markets tumble amid rising geopolitical tensions in Europe.",
        "Inflation data shows signs of cooling, boosting investor sentiment.",
        "New trade tariffs introduced, impacting global supply chains.",
        "Major credit event sends shockwaves through the financial sector."
    ]
    for text in market_texts:
        dt = random_date(start_date, end_date)
        news_data.append({
            "id": f"news_{news_id:03d}",
            "source": "newsapi",
            "text": text,
            "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        news_id += 1

    # Sort by timestamp
    news_data.sort(key=lambda x: x['timestamp'])
    return news_data

def generate_tweets():
    tweets = []
    
    templates = [
        "Just bought more ${ticker}. Looking good for next quarter! #bullish",
        "Can't believe the drop in ${ticker}. Sold all my bags.",
        "{company} is going to the moon! 🚀🚀🚀",
        "Earnings miss for {company}... expected this.",
        "Market looking weak today. Might rotate out of {company}.",
        "Why is nobody talking about ${ticker} product launch?",
        "Solid beat by {company}, strong guidance.",
        "${ticker} technicals look horrible right now. 📉",
        "I am so bullish on {company}, ${ticker} is incredibly undervalued.",
        "Fed decision is destroying my ${ticker} calls 😭",
        "Geopolitical tensions making {company} a risky bet right now."
    ]
    
    for _ in range(500):
        dt = random_date(start_date, end_date)
        ticker = random.choices(tickers, weights=[5, 3, 3, 3, 3, 5, 2, 2, 2, 2, 2, 2, 2, 2, 5])[0]
        company = companies[ticker]
        template = random.choice(templates)
        text = template.format(ticker=ticker, company=company)
        
        # Market-wide commentary without ticker
        if random.random() < 0.05:
            text = random.choice([
                "S&P 500 looking very frothy here. Careful out there.",
                "Inflation data is out and the market is NOT happy.",
                "Rate cuts priced in? I think not. Cash is king.",
                "Bears r fuk 🚀 market only goes up",
                "What a bloodbath today in the markets."
            ])
            ticker = ""
            company = ""
        
        tweets.append({
            "Date": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "Tweet": text,
            "Stock Name": ticker,
            "Company Name": company
        })
        
    # Sort by date
    tweets.sort(key=lambda x: x['Date'])
    return tweets

os.makedirs('d:/s&p/data/samples', exist_ok=True)

news_data = generate_news()
with open('d:/s&p/data/samples/news.json', 'w') as f:
    json.dump(news_data, f, indent=2)
    
tweets_data = generate_tweets()
with open('d:/s&p/data/samples/tweets.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=["Date", "Tweet", "Stock Name", "Company Name"])
    writer.writeheader()
    writer.writerows(tweets_data)
    
print(f'Generated News: {len(news_data)} items')
print(f'Generated Tweets: {len(tweets_data)} rows')
