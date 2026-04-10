import os
import yfinance as yf
import requests
from datetime import datetime
import pandas as pd

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ================= TELEGRAM =================
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })

# ================= STOCK LIST =================
STOCKS = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS",
    "ICICIBANK.NS","SBIN.NS","ITC.NS","TATAPOWER.NS",
    "NTPC.NS","HAL.NS","BEL.NS","RVNL.NS"
]

# ================= BREAKOUT =================
def breakout_scan():
    msg = "📈 BREAKOUT ALERTS\n\n"

    for stock in STOCKS:
        df = yf.Ticker(stock).history(period="1mo")

        if len(df) < 20:
            continue

        high = df['High'].rolling(20).max().iloc[-2]
        today = df['Close'].iloc[-1]

        volume_avg = df['Volume'].rolling(10).mean().iloc[-1]
        volume_now = df['Volume'].iloc[-1]

        if today > high and volume_now > 2 * volume_avg:
            msg += f"🔥 {stock.replace('.NS','')} breakout\n"

    if msg.strip() != "📈 BREAKOUT ALERTS":
        send(msg)

# ================= AI PREDICTION =================
def ai_prediction():
    msg = "🧠 AI SHORT-TERM BIAS\n\n"

    for stock in STOCKS:
        df = yf.Ticker(stock).history(period="15d")

        if len(df) < 10:
            continue

        trend = df['Close'].iloc[-1] - df['Close'].iloc[-5]

        if trend > 0:
            msg += f"{stock.replace('.NS','')}: Bullish 🟢\n"
        else:
            msg += f"{stock.replace('.NS','')}: Bearish 🔴\n"

    send(msg)

# ================= INTRADAY SIGNAL =================
def intraday_signal():
    msg = "💰 INTRADAY MOMENTUM\n\n"

    for stock in STOCKS:
        df = yf.Ticker(stock).history(period="5d")

        if len(df) < 3:
            continue

        change = (df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]

        if abs(change) > 0.02:
            msg += f"{stock.replace('.NS','')}: {round(change*100,2)}%\n"

    send(msg)

# ================= FII/DII PROXY =================
def fii_dii_proxy():
    nifty = yf.Ticker("^NSEI").history(period="5d")

    change = nifty['Close'].iloc[-1] - nifty['Close'].iloc[-2]

    msg = "🏦 MARKET FLOW (FII/DII PROXY)\n\n"

    if change > 0:
        msg += "FII Buying Pressure 🟢\n"
    else:
        msg += "FII Selling Pressure 🔴\n"

    send(msg)

# ================= US MARKET =================
def us_market():
    nasdaq = yf.Ticker("^IXIC").history(period="1d")
    sp500 = yf.Ticker("^GSPC").history(period="1d")

    nas_change = nasdaq['Close'].iloc[-1] - nasdaq['Open'].iloc[-1]
    sp_change = sp500['Close'].iloc[-1] - sp500['Open'].iloc[-1]

    msg = f"""🇺🇸 US MARKET UPDATE

NASDAQ: {round(nas_change,2)}
S&P500: {round(sp_change,2)}

Global sentiment indicator
"""

    send(msg)

# ================= RUN =================
now = datetime.now()
hour = now.hour

# Intraday hours (India market)
if 9 <= hour <= 15:
    breakout_scan()
    intraday_signal()

# AI prediction (daily)
if hour == 10:
    ai_prediction()

# FII/DII proxy (market close)
if hour == 15:
    fii_dii_proxy()

# US market (approx 7:45 PM IST)
if hour == 19:
    us_market()
