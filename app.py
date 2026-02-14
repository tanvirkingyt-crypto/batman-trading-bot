import pandas as pd
import yfinance as yf
import requests
import os
import pytz
from datetime import datetime
import streamlit as st
import time

# ================= CONFIGURATION =================
PASSWORD_REQUIRED = "BATMAN99"
SYMBOL = "EURUSD=X"
TELEGRAM_TOKEN = os.getenv("API_TOKEN") # Env থেকে নিবে
CHAT_ID = os.getenv("CHAT_ID")

# ================= UI & THEME (Matching Image) =================
st.set_page_config(page_title="BATMAN TRADING FX BOT", page_icon="🦇", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #040d14; color: #00d4ff; }
    .stTextInput>div>div>input { background-color: #0a192f; color: white; border: 1px solid #00d4ff; }
    .stButton>button { background-color: #00d4ff; color: black; width: 100%; border-radius: 10px; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

st.image("https://i.imgur.com/your_batman_logo.png", width=150) # আপনার লোগো ইউআরএল দিন
st.title("BATMAN TRADING FX BOT")

# ================= SESSION STATE =================
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# ================= 1. PASSWORD CHECK =================
if not st.session_state['authenticated']:
    pwd = st.text_input("PASSWORD", type="password", placeholder="Enter Password")
    if st.button("LOGIN"):
        if pwd == PASSWORD_REQUIRED:
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Wrong Password!")
    st.stop()

# ================= 2. TIME & F*** YOU MESSAGE =================
tz = pytz.timezone('Asia/Dhaka')
now = datetime.now(tz)
current_time = now.time()

# ২:৩০ PM থেকে ১০:০০ PM
start_time = datetime.strptime("14:30", "%H:%M").time()
end_time = datetime.strptime("22:00", "%H:%M").time()

if not (start_time <= current_time <= end_time):
    st.warning("🖕 F*** YOU! মার্কেট সেশন এখন বন্ধ। দুপুর ২:৩০ থেকে রাত ১০টার মধ্যে আসুন।")
    st.stop()

# ================= 3. NEWS CHECK (Forex Factory API) =================
def check_high_impact_news():
    try:
        # এটি একটি ফ্রি ক্যালেন্ডার API (উদাহরণস্বরূপ)
        r = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json")
        news_data = r.json()
        for event in news_data:
            if event['impact'] == 'High' and event['currency'] in ['EUR', 'USD']:
                # ইভেন্টের সময় চেক করে নিউজ চলাকালীন ট্রেড বন্ধ রাখা ভালো
                return True
        return False
    except:
        return False

# ================= 4. SMC & ICT LOGIC (Calculations) =================
def get_smc_signals():
    df = yf.download(SYMBOL, period="2d", interval="15m", progress=False)
    df_h1 = yf.download(SYMBOL, period="5d", interval="1h", progress=False)
    
    # Clean Columns
    df.columns = df.columns.get_level_values(0) if isinstance(df.columns, pd.MultiIndex) else df.columns

    # 4.1 Trend & MSS (Market Structure Shift)
    sma_200 = df['Close'].rolling(200).mean().iloc[-1]
    trend = "BULLISH" if df['Close'].iloc[-1] > sma_200 else "BEARISH"

    # 4.2 Order Block & Supply/Demand
    recent_high = df['High'].iloc[-20:-1].max()
    recent_low = df['Low'].iloc[-20:-1].min()
    
    # 4.3 Fair Value Gap (FVG)
    fvg_detected = False
    if df['Low'].iloc[-3] > df['High'].iloc[-1]: # Bearish FVG
        fvg_detected = True
    elif df['High'].iloc[-3] < df['Low'].iloc[-1]: # Bullish FVG
        fvg_detected = True

    # 4.4 Liquidity (Sweep)
    liquidity_sweep = df['Low'].iloc[-1] < df['Low'].iloc[-5:-1].min()

    # 4.5 CHoCH & BOS
    choch = df['Close'].iloc[-1] > recent_high or df['Close'].iloc[-1] < recent_low

    return {
        "trend": trend,
        "fvg": fvg_detected,
        "sweep": liquidity_sweep,
        "price": df['Close'].iloc[-1],
        "low": recent_low,
        "high": recent_high,
        "choch": choch
    }

# ================= 7. TRIPLE CONFIRMATION & SIGNALS =================
data = get_smc_signals()
news_danger = check_high_impact_news()

st.subheader(f"LIVE EUR/USD: {data['price']:.5f}")
st.write(f"Trend: **{data['trend']}** | News: {'⚠️ High Impact' if news_danger else '✅ Clear'}")

# ৩ বার কনফার্মেশন লজিক (Trend + Liquidity + FVG/CHoCH)
signal_text = None
if data['trend'] == "BULLISH" and data['sweep'] and data['choch']:
    signal_text = f"🚀 BATMAN BUY\nEntry: {data['price']}\nSL: {data['low']}\nTP: {data['price'] + 0.0020}"
elif data['trend'] == "BEARISH" and data['sweep'] and data['choch']:
    signal_text = f"📉 BATMAN SELL\nEntry: {data['price']}\nSL: {data['high']}\nTP: {data['price'] - 0.0020}"

# ================= 10. NOTIFICATION & REFRESH =================
if signal_text:
    st.success("🔥 HIGH ACCURACY SIGNAL FOUND!")
    st.code(signal_text)
    # Telegram Notification
    if TELEGRAM_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": f"🦇 BATMAN ALERT\n{signal_text}"})
else:
    st.info("⌛ মার্কেট এনালাইসিস চলছে... সঠিক সেটআপের অপেক্ষায়।")

# ================= 8. AUTO REFRESH =================
time.sleep(60) # প্রতি ১ মিনিট পর পর অটো রিফ্রেশ হবে
st.rerun()
