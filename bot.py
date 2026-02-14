import os
import yfinance as yf
import requests
import feedparser
from textblob import TextBlob
from datetime import datetime
import random

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ================= TELEGRAM =================
def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    })

# ================= NEWS =================
def get_news(query, limit=5):
    feed = feedparser.parse(
        f"https://news.google.com/rss/search?q={query}+india+stock"
    )
    return [e.title for e in feed.entries[:limit]]

def sentiment(headlines):
    if not headlines:
        return 0
    return sum(TextBlob(h).sentiment.polarity for h in headlines) / len(headlines)

def sentiment_label(s):
    if s > 0.15: return "Bullish 🟢"
    if s < -0.15: return "Bearish 🔴"
    return "Neutral 🟡"

# ================= STOCK RATING =================
def rate_stock(symbol, name):
    data = yf.Ticker(symbol).history(period="1y")
    if data.empty:
        return None

    price_growth = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]
    news_score = sentiment(get_news(name))
    rating = round(min(10, max(1, (price_growth * 10) + (news_score * 5))), 1)
    return rating

# ================= SECTORS =================
SECTORS = {
    "Power": ["TATAPOWER.NS", "NTPC.NS"],
    "Defence": ["HAL.NS", "BEL.NS"],
    "IT": ["INFY.NS", "TCS.NS"],
    "Banking": ["HDFCBANK.NS", "SBIN.NS"],
    "Infra": ["L&T.NS", "RVNL.NS"]
}

# ================= STOCK OF THE DAY =================
def stock_of_the_day():
    candidates = {
        "TATA POWER": "TATAPOWER.NS",
        "HAL": "HAL.NS",
        "BEL": "BEL.NS",
        "RVNL": "RVNL.NS",
        "NTPC": "NTPC.NS"
    }

    best = None
    best_score = -1

    for name, sym in candidates.items():
        s = sentiment(get_news(name))
        if s > best_score:
            best_score = s
            best = (name, sym, s)

    if not best:
        return

    name, sym, score = best
    rating = rate_stock(sym, name)
    news = get_news(name, 2)

    msg = f"""🌅 STOCK OF THE DAY (AI Pick)
📅 {datetime.now().strftime('%d %b %Y')}

📌 {name}
Rating: ⭐ {rating}/10
Trend: {sentiment_label(score)}

Why Bullish Today?
• Positive news sentiment
• Sector momentum
• Market participation

Top News:
• {news[0] if news else "No major negative news"}

⚠ Educational AI analysis only
"""
    send(msg)

# ================= MARKET CLOSE REPORT =================
def market_report():
    nifty = yf.Ticker("^NSEI").history(period="1d")
    sensex = yf.Ticker("^BSESN").history(period="1d")

    msg = f"""📊 INDIAN MARKET AI REPORT
📅 {datetime.now().strftime('%d %b %Y')}

NIFTY 50: {round(nifty['Close'].iloc[-1],2)} ({round(nifty['Close'].iloc[-1]-nifty['Open'].iloc[-1],2)})
SENSEX: {round(sensex['Close'].iloc[-1],2)} ({round(sensex['Close'].iloc[-1]-sensex['Open'].iloc[-1],2)})

🏭 SECTOR ANALYSIS
"""

    for sector, stocks in SECTORS.items():
        sector_sent = sentiment(get_news(sector))
        msg += f"\n{sector}: {sentiment_label(sector_sent)}\n"
        for sym in stocks:
            name = sym.replace(".NS","")
            r = rate_stock(sym, name)
            if r:
                msg += f"• {name}: ⭐ {r}/10\n"

    msg += "\n⚠ Educational AI analysis only. Not SEBI advice."
    send(msg)

# ================= WEEKLY =================
def weekly_outlook():
    send("""📅 WEEKLY AI OUTLOOK

Best Sectors:
• Defence 🟢
• Infra 🟢

Avoid:
• Weak IT momentum

Strategy:
• Focus on PSU + Capex themes
• Avoid overvalued stocks
""")

# ================= RUN =================
now = datetime.now()
weekday = now.weekday()
hour = now.hour

# 9 AM Stock of the Day
if hour == 9:
    stock_of_the_day()

# Market close
if hour == 15:
    market_report()

# Sunday weekly
if weekday == 6 and hour == 9:
    weekly_outlook()
