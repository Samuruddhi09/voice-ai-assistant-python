import MetaTrader5 as mt5
import pandas as pd



#  Get Gold Trading Signal (EMA Strategy)

def get_gold_signal():
    symbol = "XAUUSD"

    # Init MT5
    if not mt5.initialize():
        return {
            "success": False,
            "signal": None,
            "error": f"MT5 initialization failed: {mt5.last_error()}"
        }

    # Select XAUUSD
    if not mt5.symbol_select(symbol, True):
        mt5.shutdown()
        return {
            "success": False,
            "signal": None,
            "error": f"Failed to select symbol {symbol}"
        }

    # Get candle data
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)
    tick = mt5.symbol_info_tick(symbol)
    last_price = round(tick.last, 2) if tick and tick.last else None

    # Not enough data
    if rates is None or len(rates) < 20:
        mt5.shutdown()
        return {
            "success": True,
            "signal": None,
            "message": "Not enough data to calculate EMAs",
            "price": last_price
        }

    df = pd.DataFrame(rates)
    df["ema_9"]  = df["close"].ewm(span=9, adjust=False).mean()
    df["ema_15"] = df["close"].ewm(span=15, adjust=False).mean()

    latest   = df.iloc[-1]
    previous = df.iloc[-2]

    entry_price = round(float(latest["close"]), 2)

    # EMA crossover strategy
    signal = None
    if previous["ema_9"] < previous["ema_15"] and latest["ema_9"] > latest["ema_15"] and latest["close"] > latest["open"]:
        signal = "BUY"
    elif previous["ema_9"] > previous["ema_15"] and latest["ema_9"] < latest["ema_15"] and latest["close"] < latest["open"]:
        signal = "SELL"

    # No signal case
    if not signal:
        mt5.shutdown()
        return {
            "success": True,
            "signal": None,
            "price": entry_price,
            "ema9": round(latest["ema_9"], 2),
            "ema15": round(latest["ema_15"], 2),
            "message": "No signal based on EMA crossover"
        }

    # Risk model (1 USD SL, 2 USD TP)
    risk = 1.0
    if signal == "BUY":
        sl = round(entry_price - risk, 2)
        tp = round(entry_price + 2 * risk, 2)
    else:
        sl = round(entry_price + risk, 2)
        tp = round(entry_price - 2 * risk, 2)

    mt5.shutdown()

    return {
        "success": True,
        "signal": signal,
        "entry": entry_price,
        "tp": tp,
        "sl": sl,
        "ema9": round(latest["ema_9"], 2),
        "ema15": round(latest["ema_15"], 2),
        "price": entry_price
    }



#  Get Gold Candles for Chart (5m timeframe)

def get_gold_candles():
    symbol = "XAUUSD"

    if not mt5.initialize():
        return None

    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 200)
    mt5.shutdown()

    if rates is None:
        return None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)
    return df
