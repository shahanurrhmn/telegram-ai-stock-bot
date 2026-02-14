import os
import yfinance as yf
import requests
import feedparser
from textblob import TextBlob
from datetime import datetime
import pandas as pd

# ================== ENV ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ================== TELEGRAM ==================
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    requests.post(url, data=payload)

# ================== NEWS & SENTIMENT ==================
def get_news(query, limit=6):
    feed = feedparser.parse(
        f"https://news.google.com/rss/search?q={query}+india+stock"
    )
    return [e.title for e in feed.entries[:limit]]

def sentiment_score(headlines):
    if not headlines:
        return 0
    return sum(TextBlob(h).sentiment.polarity for h in headlines) / len(headlines)

def sentiment_label(score):
    if score > 0.15:
        return "Positive 🟢"
    elif score < -0.15:
        return "Negative 🔴"
    return "Neutral 🟡"

# ================== MARKET SUMMARY ==================
def market_summary():
    nifty = yf.Ticker("^NSEI").history(period="1d")
    sensex = yf.Ticker("^BSESN").history(period="1d")

    msg = f"""📊 Indian Market AI Summary
📅 {datetime.now().strftime('%d %b %Y')}

NIFTY 50: {round(nifty['Close'].iloc[-1],2)} ({round(nifty['Close'].iloc[-1]-nifty['Open'].iloc[-1],2)})
SENSEX: {round(sensex['Close'].iloc[-1],2)} ({round(sensex['Close'].iloc[-1]-sensex['Open'].iloc[-1],2)})

📌 Sector Sentiment:
"""

    sectors = ["Power", "Defence", "IT", "Banking", "AI"]
    for s in sectors:
        score = sentiment_score(get_news(s))
        msg += f"• {s}: {sentiment_label(score)}\n"

    msg += "\n⚠ Educational AI analysis only. Not SEBI registered advice."
    return msg

# ================== MULTIBAGGER SCAN ==================
def multibagger_scan():
    stocks = {
        "TATA POWER": "TATAPOWER.NS",
        "IREDA": "IREDA.NS",
        "RVNL": "RVNL.NS",
        "COCHIN SHIP": "COCHINSHIP.NS",
        "BHEL": "BHEL.NS"
    }

    msg = "🚀 AI Multibagger Radar\n\n"
    for name, symbol in stocks.items():
        data = yf.Ticker(symbol).history(period="6mo")
        if len(data) < 50:
            continue
        growth = ((data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]) * 100
        if growth > 25:
            msg += f"• {name}: +{round(growth,1)}% 📈\n"

    return msg + "\n(High momentum stocks, not buy advice)"

# ================== STOCK RATING ==================
def rate_stock(symbol, name):
    data = yf.Ticker(symbol).history(period="1y")
    if data.empty:
        return None

    price_score = min(5, ((data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]) * 10)
    news_score = sentiment_score(get_news(name)) * 5
    rating = round(min(10, max(1, price_score + news_score)), 1)

    return f"⭐ {name} Rating: {rating}/10"

def stock_ratings():
    stocks = {
        "TATA POWER": "TATAPOWER.NS",
        "HDFC BANK": "HDFCBANK.NS",
        "INFOSYS": "INFY.NS",
        "RVNL": "RVNL.NS"
    }

    msg = "📈 AI Stock Ratings\n\n"
    for name, sym in stocks.items():
        r = rate_stock(sym, name)
        if r:
            msg += f"{r}\n"

    return msg

# ================== WEEKLY REPORT ==================
def weekly_report():
    return f"""📅 Weekly AI Market Outlook

Best Sectors:
• Defence 🟢
• Banking 🟢

Weak Sector:
• IT 🔴

Strategy:
• Focus on PSU + Infra
• Avoid high valuation tech stocks

⚠ Long-term investors only
"""

# ================== RUN ==================
today = datetime.now().weekday()

send_message(market_summary())
send_message(multibagger_scan())
send_message(stock_ratings())

# Sunday weekly report
if today == 6:
    send_message(weekly_report())
