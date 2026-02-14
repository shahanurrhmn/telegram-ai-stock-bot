import os
import yfinance as yf
import requests
import feedparser
from textblob import TextBlob
from datetime import datetime

# ================== ENV VARIABLES ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ================== TELEGRAM SENDER ==================
def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    r = requests.post(url, data=payload)
    print("Telegram API response:", r.text)

# ================== NEWS & AI ==================
def get_sector_news(sector):
    feed = feedparser.parse(
        f"https://news.google.com/rss/search?q={sector}+sector+india+stock"
    )
    return [entry.title for entry in feed.entries[:6]]

def analyze_sentiment(headlines):
    if not headlines:
        return "Neutral 🟡"

    score = 0
    for h in headlines:
        score += TextBlob(h).sentiment.polarity

    avg = score / len(headlines)

    if avg > 0.1:
        return "Positive 🟢"
    elif avg < -0.1:
        return "Negative 🔴"
    else:
        return "Neutral 🟡"

# ================== MARKET SUMMARY ==================
def market_summary():
    nifty = yf.Ticker("^NSEI").history(period="1d")
    sensex = yf.Ticker("^BSESN").history(period="1d")

    nifty_change = nifty["Close"][-1] - nifty["Open"][-1]
    sensex_change = sensex["Close"][-1] - sensex["Open"][-1]

    msg = f"""
📊 Indian Market AI Summary
📅 {datetime.now().strftime('%d %b %Y')}

NIFTY 50: {round(nifty['Close'][-1],2)} ({round(nifty_change,2)})
SENSEX: {round(sensex['Close'][-1],2)} ({round(sensex_change,2)})

🏭 Sector News Sentiment:
"""

    sectors = ["Power", "Defence", "IT", "Banking"]

    for sector in sectors:
        news = get_sector_news(sector)
        sentiment = analyze_sentiment(news)
        msg += f"• {sector}: {sentiment}\n"

    msg += "\n⚠ Educational AI analysis only. Not SEBI registered advice."
    return msg

# ================== RUN ==================
send_message("✅ BOT STARTED: Telegram connection test")
send_message(market_summary())
