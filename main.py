
import time
import schedule
import pandas as pd
from binance.client import Client
from binance.enums import *
from ta.momentum import StochasticOscillator
from ta.trend import EMAIndicator
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

client = Client(API_KEY, API_SECRET)
client.API_URL = 'https://testnet.binance.vision/api'

SYMBOL = "ETHUSDT"
QUANTITY = 0.01
TIMEFRAME = "4h"

position = None
entry_price = None

def fetch_data(symbol, interval="4h", limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close',
        'volume', 'close_time', 'quote_asset_volume',
        'num_trades', 'taker_buy_base_volume',
        'taker_buy_quote_volume', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df

def strategy():
    global position, entry_price

    df = fetch_data(SYMBOL, interval=TIMEFRAME)
    df.dropna(inplace=True)

    ema12 = EMAIndicator(df['close'], window=12).ema_indicator()
    ema26 = EMAIndicator(df['close'], window=26).ema_indicator()
    stoch = StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
    k = stoch.stoch()
    d = stoch.stoch_signal()

    if len(df) < 2:
        return
    last_close = df['close'].iloc[-1]
    prev_ema12 = ema12.iloc[-2]
    prev_ema26 = ema26.iloc[-2]
    curr_ema12 = ema12.iloc[-1]
    curr_ema26 = ema26.iloc[-1]
    k_now = k.iloc[-1]
    d_now = d.iloc[-1]

    if position is None:
        bullish_crossover = prev_ema12 <= prev_ema26 and curr_ema12 > curr_ema26
        stochastic_bull = k_now > d_now

        if bullish_crossover and stochastic_bull:
            order = client.create_order(
                symbol=SYMBOL,
                side=SIDE_BUY,
                type=ORDER_TYPE_MARKET,
                quantity=QUANTITY
            )
            position = "LONG"
            entry_price = last_close
            print(f"🟢 BUY @ {last_close:.2f}")
    else:
        gain = (last_close - entry_price) / entry_price

        if gain >= 0.6:
            client.create_order(
                symbol=SYMBOL,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=QUANTITY
            )
            print(f"✅ TAKE PROFIT @ {last_close:.2f} | Gain: {gain:.2%}")
            position = None
            entry_price = None

        elif gain <= -0.15:
            client.create_order(
                symbol=SYMBOL,
                side=SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=QUANTITY
            )
            print(f"❌ STOP LOSS @ {last_close:.2f} | Loss: {gain:.2%}")
            position = None
            entry_price = None

schedule.every(1).hours.do(strategy)

print("🚀 Bot iniciado...")
while True:
    schedule.run_pending()
    time.sleep(60)
