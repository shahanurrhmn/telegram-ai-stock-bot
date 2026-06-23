import os
import time
import json
import pickle
import numpy as np
import pandas as pd
import yfinance as yf
import requests
import feedparser
from datetime import datetime

# AI module – only LSTM (no transformers)
from tensorflow.keras.models import load_model

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

CACHE_FILE = "cache.json"

# ================= TELEGRAM =================
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

# ================= CACHE =================
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {"last_signals": {}, "signals": [], "performance": {"win": 0, "loss": 0}, "date": ""}
    with open(CACHE_FILE) as f:
        return json.load(f)

def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def reset_daily(cache):
    today = str(datetime.now().date())
    if cache.get("date") != today:
        cache["last_signals"] = {}
        cache["date"] = today

# ================= STOCK UNIVERSE =================
CORE_STOCKS = [
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN",
    "LT","HCLTECH","AXISBANK","KOTAKBANK","ITC","BAJFINANCE",
    "ASIANPAINT","MARUTI","SUNPHARMA","TITAN","ULTRACEMCO",
    "NESTLEIND","WIPRO","POWERGRID","NTPC","ONGC","ADANIENT",
    "TATAMOTORS","JSWSTEEL","COALINDIA","HINDUNILVR"
]

def get_dynamic_stocks():
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/trending/IN"
        data = requests.get(url, timeout=10).json()
        stocks = []
        for item in data['finance']['result'][0]['quotes']:
            symbol = item['symbol']
            if symbol.endswith(".NS"):
                stocks.append(symbol.replace(".NS", ""))
        return stocks[:10]
    except:
        return []

def get_all_stocks():
    return list(set(CORE_STOCKS + get_dynamic_stocks()))

# ================= INDICATORS (for LSTM) =================
def compute_indicators(df):
    df = df.copy()
    df.columns = [c.capitalize() for c in df.columns]
    close = df['Close']
    df['SMA_20'] = close.rolling(20).mean()
    df['SMA_50'] = close.rolling(50).mean()
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0.0).rolling(14).mean()
    loss = loss.replace(0, np.nan)
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    df['MACD'] = ema12 - ema26
    df['Volume_Change'] = df['Volume'].pct_change()
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    return df

# ================= LSTM =================
LSTM_MODEL_PATH = "models/lstm_model.h5"
SCALER_PATH = "models/scaler.pkl"
FEATURE_COLS = ['Close','SMA_20','SMA_50','RSI','MACD','Volume_Change']

lstm_model = None
scaler = None
def load_lstm():
    global lstm_model, scaler
    if lstm_model is None:
        lstm_model = load_model(LSTM_MODEL_PATH)
        with open(SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)

def get_lstm_probability(stock):
    try:
        load_lstm()
        df = yf.Ticker(stock+".NS").history(period="6mo")
        if df.empty or len(df) < 60:
            return None
        df = compute_indicators(df)
        df = df[FEATURE_COLS].dropna()
        if len(df) < 60:
            return None
        last_60 = df.tail(60).values
        scaled = scaler.transform(last_60)
        X = scaled.reshape(1, 60, len(FEATURE_COLS))
        prob = lstm_model.predict(X, verbose=0)[0][0]
        return float(prob)
    except:
        return None

# ================= SIGNAL GENERATION (LSTM + Tech only) =================
def trade_signals(cache):
    msg = "🎯 <b>AI SIGNALS</b> (LSTM + Technical)\n\n"
    found = False

    for stock in get_all_stocks():
        time.sleep(0.5)
        try:
            df = yf.Ticker(stock + ".NS").history(period="1mo")
            if df.empty or len(df) < 20:
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
                tech_conf = min(rsi_val, 90)
            elif entry < ema20 and rsi_val < 40 and change < -0.015:
                signal_type = "SELL"
                target = round(entry * 0.96, 2)
                stop = round(entry * 1.03, 2)
                tech_conf = min(100 - rsi_val, 90)

            if not signal_type:
                continue

            if cache["last_signals"].get(stock) == signal_type:
                continue
            cache["last_signals"][stock] = signal_type

            # --- AI: LSTM only ---
            lstm_prob = get_lstm_probability(stock)
            lstm_conf = 50
            if lstm_prob is not None:
                lstm_conf = lstm_prob * 100 if signal_type == "BUY" else (1 - lstm_prob) * 100

            # Simple fusion (no sentiment)
            final_conf = 0.4 * tech_conf + 0.6 * lstm_conf   # give more weight to LSTM
            if final_conf < 65:
                continue

            cache["signals"].append({
                "stock": stock,
                "type": signal_type,
                "entry": entry,
                "target": target,
                "stop": stop
            })

            msg += f"""📊 <b>{signal_type}: {stock}</b>
Entry: {entry}
Target: {target}
Stoploss: {stop}
🤖 AI Confidence: {int(final_conf)}%
<code>Tech:{tech_conf:.0f} LSTM:{lstm_conf:.0f}</code>

"""
            found = True
        except Exception as e:
            print(f"Error {stock}: {e}")

    if found:
        send(msg)
    else:
        send("ℹ️ No AI‑conviction trades right now")

# ================= BROKER CALLS (unchanged) =================
def broker_calls():
    feed = feedparser.parse("https://feeds.feedburner.com/ndtvprofit-latest")
    msg = "📊 BROKER CONSENSUS\n\n"
    found = False
    for entry in feed.entries[:10]:
        title = entry.title.lower()
        for stock in get_all_stocks():
            if stock.lower() in title and ("buy" in title or "target" in title):
                msg += f"🟢 {stock}\n{entry.title}\n\n"
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
    send(f"📊 PERFORMANCE REPORT\n\nTrades: {total}\nWins: {win}\nLoss: {loss}\nAccuracy: {acc}%\n")

# ================= US MARKET =================
def us_market():
    nas = yf.Ticker("^IXIC").history(period="1d")
    sp = yf.Ticker("^GSPC").history(period="1d")
    if nas.empty or sp.empty:
        return
    nas_change = (nas['Close'].iloc[-1] - nas['Open'].iloc[-1]) / nas['Open'].iloc[-1] * 100
    sp_change = (sp['Close'].iloc[-1] - sp['Open'].iloc[-1]) / sp['Open'].iloc[-1] * 100
    send(f"🇺🇸 US MARKET UPDATE\n\nNASDAQ: {round(nas_change,2)}%\nS&P500: {round(sp_change,2)}%")

# ================= MAIN =================
if __name__ == "__main__":
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
