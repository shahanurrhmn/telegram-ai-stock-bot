import os
import yfinance as yf
import requests
from datetime import datetime
import json
import feedparser

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

CACHE_FILE = "cache.json"

# ================= TELEGRAM =================
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ================= CACHE =================
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {"last_signals": {}, "signals": [], "performance": {"win": 0, "loss": 0}, "date": ""}
    return json.load(open(CACHE_FILE))

def save_cache(data):
    json.dump(data, open(CACHE_FILE, "w"))

def reset_daily(cache):
    today = str(datetime.now().date())
    if cache.get("date") != today:
        cache["last_signals"] = {}
        cache["date"] = today

# ================= CORE STOCKS =================
CORE_STOCKS = [
"RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN",
"LT","HCLTECH","AXISBANK","KOTAKBANK","ITC","BAJFINANCE",
"ASIANPAINT","MARUTI","SUNPHARMA","TITAN","ULTRACEMCO",
"NESTLEIND","WIPRO","POWERGRID","NTPC","ONGC","ADANIENT",
"TATAMOTORS","JSWSTEEL","COALINDIA","HINDUNILVR"
]

# ================= DYNAMIC STOCKS =================
def get_dynamic_stocks():
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/trending/IN"
        data = requests.get(url).json()

        stocks = []
        for item in data['finance']['result'][0]['quotes']:
            symbol = item['symbol']
            if symbol.endswith(".NS"):
                stocks.append(symbol.replace(".NS",""))

        return stocks[:10]
    except:
        return []

def get_all_stocks():
    return list(set(CORE_STOCKS + get_dynamic_stocks()))

# ================= HIGH-CONVICTION SIGNAL =================
def trade_signals(cache):
    msg = "🎯 HIGH CONVICTION SIGNALS\n\n"
    found = False

    for stock in get_all_stocks():
        df = yf.Ticker(stock + ".NS").history(period="1mo")

        if len(df) < 20:
            continue

        close = df['Close']

        ema20 = close.ewm(span=20).mean().iloc[-1]

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]

        change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]

        entry = round(close.iloc[-1], 2)

        signal_type = None

        if entry > ema20 and rsi_val > 60 and change > 0.015:
            signal_type = "BUY"
            target = round(entry * 1.04, 2)
            stop = round(entry * 0.97, 2)
            confidence = int(rsi_val)

        elif entry < ema20 and rsi_val < 40 and change < -0.015:
            signal_type = "SELL"
            target = round(entry * 0.96, 2)
            stop = round(entry * 1.03, 2)
            confidence = int(100 - rsi_val)

        if signal_type:
            if cache["last_signals"].get(stock) == signal_type:
                continue

            cache["last_signals"][stock] = signal_type

            cache["signals"].append({
                "stock": stock,
                "type": signal_type,
                "entry": entry,
                "target": target,
                "stop": stop
            })

            msg += f"""📊 {signal_type}: {stock}
Entry: {entry}
Target: {target}
Stoploss: {stop}
Confidence: {confidence}%

"""
            found = True

    if found:
        send(msg)
    else:
        send("ℹ️ No high-conviction trades right now")

# ================= BROKER =================
def broker_calls():
    feed = feedparser.parse("https://feeds.feedburner.com/ndtvprofit-latest")

    msg = "📊 BROKER CONSENSUS\n\n"
    found = False

    for entry in feed.entries[:10]:
        title = entry.title.lower()

        for stock in get_all_stocks():
            if stock.lower() in title and ("buy" in title or "target" in title):
                msg += f"""🟢 {stock}
{entry.title}

"""
                found = True

    if found:
        send(msg)

# ================= PERFORMANCE =================
def check_performance(cache):
    for s in cache["signals"]:
        df = yf.Ticker(s["stock"] + ".NS").history(period="2d")
        if df.empty:
            continue

        current = df['Close'].iloc[-1]

        if s["type"] == "BUY":
            if current >= s["target"]:
                cache["performance"]["win"] += 1
            elif current <= s["stop"]:
                cache["performance"]["loss"] += 1

        elif s["type"] == "SELL":
            if current <= s["target"]:
                cache["performance"]["win"] += 1
            elif current >= s["stop"]:
                cache["performance"]["loss"] += 1

    cache["signals"] = []

def performance_report(cache):
    win = cache["performance"]["win"]
    loss = cache["performance"]["loss"]
    total = win + loss

    if total == 0:
        return

    acc = round((win / total) * 100, 2)

    send(f"""📊 PERFORMANCE REPORT

Trades: {total}
Wins: {win}
Loss: {loss}
Accuracy: {acc}%
""")

# ================= US MARKET =================
def us_market():
    nas = yf.Ticker("^IXIC").history(period="1d")
    sp = yf.Ticker("^GSPC").history(period="1d")

    if nas.empty or sp.empty:
        return

    nas_change = (nas['Close'].iloc[-1] - nas['Open'].iloc[-1]) / nas['Open'].iloc[-1] * 100
    sp_change = (sp['Close'].iloc[-1] - sp['Open'].iloc[-1]) / sp['Open'].iloc[-1] * 100

    send(f"""🇺🇸 US MARKET UPDATE

NASDAQ: {round(nas_change,2)}%
S&P500: {round(sp_change,2)}%
""")

# ================= RUN =================
cache = load_cache()
reset_daily(cache)

now = datetime.now()
hour = now.hour

if 10 <= hour <= 14:
    trade_signals(cache)

if 11 <= hour <= 16:
    broker_calls()

if hour == 15:
    check_performance(cache)
    performance_report(cache)

if 19 <= hour <= 20:
    us_market()

save_cache(cache)
