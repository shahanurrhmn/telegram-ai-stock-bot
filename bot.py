import os
import yfinance as yf
import requests
import feedparser
from textblob import TextBlob
from datetime import datetime
import json

# ================= ENV =================
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

# ================= NEWS UTIL =================
NEWS_CACHE_FILE = "sent_news.json"

def load_sent_news():
    if not os.path.exists(NEWS_CACHE_FILE):
        return set()
    with open(NEWS_CACHE_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))

def save_sent_news(sent):
    with open(NEWS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent), f)

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

# ================= INDIAN STOCK UNIVERSE =================
INDIAN_STOCKS = [
    "ONGC","RELIANCE","TCS","INFOSYS","HDFC","ICICI","SBIN","ITC",
    "TATAPOWER","NTPC","HAL","BEL","BHEL","ADANI","RVNL","IREDA"
]

# ================= HOURLY NEWS ALERT =================
def hourly_stock_news():
    sent = load_sent_news()
    feed = feedparser.parse(
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^NSEI&region=IN&lang=en-IN"
    )

    for entry in feed.entries:
        title = entry.title
        upper = title.upper()

        if title in sent:
            continue

        for stock in INDIAN_STOCKS:
            if stock in upper:
                msg = f"""📰 HOURLY STOCK NEWS ALERT
⏰ {datetime.now().strftime('%d %b %Y %I:%M %p')}

Stock: {stock}
Headline:
{title}

Source: Yahoo Finance
⚠ Educational purpose only
"""
                send(msg)
                sent.add(title)
                break

    save_sent_news(sent)

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
    best = None
    best_score = -1

    for stock in INDIAN_STOCKS:
        s = sentiment(get_news(stock))
        if s > best_score:
            best_score = s
            best = stock

    if not best:
        return

    rating = rate_stock(best + ".NS", best)
    news = get_news(best, 2)

    msg = f"""🌅 STOCK OF THE DAY (AI Pick)
📅 {datetime.now().strftime('%d %b %Y')}

📌 {best}
Rating: ⭐ {rating}/10
Trend: {sentiment_label(best_score)}

Why Bullish Today?
• Strong positive news sentiment
• Sector momentum
• No major negative triggers

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
        sec_sent = sentiment(get_news(sector))
        msg += f"\n{sector}: {sentiment_label(sec_sent)}\n"
        for sym in stocks:
            name = sym.replace(".NS","")
            r = rate_stock(sym, name)
            if r:
                msg += f"• {name}: ⭐ {r}/10\n"

    msg += "\n⚠ Educational AI analysis only. Not SEBI advice."
    send(msg)

# ================= WEEKLY =================
def weekly_outlook():
    send("""📅 WEEKLY AI MARKET OUTLOOK

Best Sectors:
• Defence 🟢
• Infra 🟢

Weak:
• IT 🟡

Strategy:
• Focus on PSU & capex themes
• Avoid overhyped momentum

⚠ Educational purpose only
""")

# ================= RUN =================
now = datetime.now()
weekday = now.weekday()
hour = now.hour

# Hourly news
hourly_stock_news()

# Morning window (8–9 AM IST)
if 8 <= hour <= 9:
    stock_of_the_day()

# Market close window (3–4 PM IST)
if 15 <= hour <= 16:
    market_report()

# Sunday weekly
if weekday == 6 and 8 <= hour <= 9:
    weekly_outlook()
