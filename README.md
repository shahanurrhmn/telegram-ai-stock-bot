# 🤖 AI Indian Stock Signal Bot

A free, self‑learning AI bot that sends **Buy/Sell signals** for Indian stocks (NSE/BSE) directly to your Telegram — powered by deep learning, financial sentiment analysis, and technical indicators.  
Runs automatically on GitHub Actions with zero cost.

---

## 🚀 How It Works

- **LSTM Neural Network** – predicts next‑day price direction from 5 years of historical data.  
- **FinBERT Sentiment** – reads real‑time Google News headlines and scores market mood.  
- **Fusion Engine** – combines technical rules, LSTM, and sentiment into a single **AI Confidence Score**.  
- **Telegram Alerts** – sends high‑conviction signals with entry, target, stoploss, and confidence.

---

## 📁 Setup (Do Once)

1. **Create a Telegram bot** via `@BotFather` and get your `BOT_TOKEN` and `CHAT_ID`.  
2. **Train the LSTM model** in [Google Colab](https://colab.research.google.com/drive/1d3jvP80x2-XkzzxLiH1GZHq_hO4YF_ZB?usp=sharing) → download `lstm_model.h5` and `scaler.pkl`.  
3. **Upload** those two files into the `models/` folder of this repo.  
4. **Add secrets** in GitHub (`Settings → Secrets → Actions`):  
   - `BOT_TOKEN`  
   - `CHAT_ID`  
5. **Run the workflow** manually once from the **Actions** tab (or wait for the scheduled time).

---

## 🕒 Schedule

The bot runs automatically on weekdays at:  
- 9:15 AM IST (market open)  
- 11:00 AM IST  
- 3:00 PM IST (market close)  
- 7:30 PM IST (US market update)

---

## ⚠️ Disclaimer

**For educational and personal use only.** Not SEBI‑registered investment advice. Trade at your own risk.

---

## 🧠 Tech Stack

Python · TensorFlow/LSTM · FinBERT (Hugging Face) · yfinance · GitHub Actions · Telegram API
