import os
import yfinance as yf
import requests
from datetime import datetime
import json

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
        return {"signals": [], "performance": {"win": 0, "loss": 0}}
    return json.load(open(CACHE_FILE))

def save_cache(data):
    json.dump(data, open(CACHE_FILE, "w"))

# ================= STOCKS =================
STOCKS = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS",
    "ICICIBANK.NS","SBIN.NS","ITC.NS","TATAPOWER.NS",
    "NTPC.NS","HAL.NS","BEL.NS","RVNL.NS"
]

# ================= TRADE SIGNAL =================
def trade_signals(cache):
    msg = "🎯 AI TRADE SIGNALS\n\n"
    found = False

    for stock in STOCKS:
        df = yf.Ticker(stock).history(period="10d")

        if len(df) < 5:
            continue

        close = df['Close']
        change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
        trend = close.iloc[-1] - close.iloc[-5]
        vol = close.pct_change().std()

        entry = round(close.iloc[-1], 2)

        # BUY
        if change > 0.02 and trend > 0:
            target = round(entry * 1.02, 2)
            stop = round(entry * 0.98, 2)

            confidence = min(90, int((change * 1000)))
            risk = "Low 🟢" if vol < 0.015 else "Medium 🟡"

            cache["signals"].append({
                "stock": stock,
                "type": "BUY",
                "entry": entry,
                "target": target,
                "stop": stop
            })

            msg += f"""📈 BUY: {stock.replace('.NS','')}
Entry: {entry}
Target: {target}
Stoploss: {stop}
Confidence: {confidence}%
Risk: {risk}

"""
            found = True

        # SELL
        elif change < -0.02 and trend < 0:
            target = round(entry * 0.98, 2)
            stop = round(entry * 1.02, 2)

            confidence = min(90, int(abs(change * 1000)))
            risk = "High 🔴" if vol > 0.02 else "Medium 🟡"

            cache["signals"].append({
                "stock": stock,
                "type": "SELL",
                "entry": entry,
                "target": target,
                "stop": stop
            })

            msg += f"""📉 SELL: {stock.replace('.NS','')}
Entry: {entry}
Target: {target}
Stoploss: {stop}
Confidence: {confidence}%
Risk: {risk}

"""
            found = True

    if found:
        send(msg)

# ================= PERFORMANCE TRACK =================
def check_performance(cache):
    if not cache["signals"]:
        return

    for s in cache["signals"]:
        df = yf.Ticker(s["stock"]).history(period="2d")
        if len(df) < 1:
            continue

        current = df['Close'].iloc[-1]

        if s["type"] == "BUY":
            if current >= s["target"]:
                cache["performance"]["win"] += 1
            elif current <= s["stop"]:
                cache["performance"]["loss"] += 1

        if s["type"] == "SELL":
            if current <= s["target"]:
                cache["performance"]["win"] += 1
            elif current >= s["stop"]:
                cache["performance"]["loss"] += 1

    cache["signals"] = []

# ================= REPORT =================
def performance_report(cache):
    win = cache["performance"]["win"]
    loss = cache["performance"]["loss"]
    total = win + loss

    if total == 0:
        return

    acc = round((win / total) * 100, 2)

    msg = f"""📊 AI PERFORMANCE REPORT

Total Trades: {total}
Wins: {win}
Loss: {loss}
Accuracy: {acc}%

"""
    send(msg)

# ================= US MARKET =================
def us_market():
    nasdaq = yf.Ticker("^IXIC").history(period="1d")
    sp500 = yf.Ticker("^GSPC").history(period="1d")

    nas = (nasdaq['Close'].iloc[-1] - nasdaq['Open'].iloc[-1]) / nasdaq['Open'].iloc[-1] * 100
    sp = (sp500['Close'].iloc[-1] - sp500['Open'].iloc[-1]) / sp500['Open'].iloc[-1] * 100

    send(f"""🇺🇸 US MARKET UPDATE

NASDAQ: {round(nas,2)}%
S&P500: {round(sp,2)}%
""")

# ================= RUN =================
cache = load_cache()
now = datetime.now()
hour = now.hour

# Signals
if 10 <= hour <= 14:
    trade_signals(cache)

# Performance check
if hour == 15:
    check_performance(cache)
    performance_report(cache)

# US market
if 19 <= hour <= 20:
    us_market()

save_cache(cache)
