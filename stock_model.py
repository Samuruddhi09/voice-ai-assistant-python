import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

#  Nifty 50 symbols
nifty50_symbols = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","HINDUNILVR.NS",
    "SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS","LT.NS","AXISBANK.NS","ITC.NS",
    "HCLTECH.NS","MARUTI.NS","ASIANPAINT.NS","TITAN.NS","ULTRACEMCO.NS",
    "SUNPHARMA.NS","WIPRO.NS","POWERGRID.NS","BAJFINANCE.NS","BAJAJFINSV.NS",
    "ADANIENT.NS","ADANIPORTS.NS"
]

#  Duration to days mapping
duration_days = {
    "1day": 1,
    "15days": 15,
    "1week": 7,
    "1month": 30,
    "3months": 90,
    "6months": 180,
    "1year": 365,
    "2year": 730,
    "5year": 1825
}

#  Fetch stock data
def get_data(symbol):
    df = yf.download(symbol, period="1y", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df.dropna(subset=["Close"]).ffill()

#  Add indicators
def add_indicators(df):
    df["SMA_20"] = df["Close"].rolling(20).mean()
    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["EMA_20"] = df["Close"].ewm(span=20).mean()

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ma = df["Close"].rolling(20).mean()
    std = df["Close"].rolling(20).std()
    df["BB_High"] = ma + 2 * std
    df["BB_Low"] = ma - 2 * std
    return df

#  ML price predictor
def predict_price(df, future_days):
    df = df.dropna(subset=["Close"])
    df["Index"] = np.arange(len(df))
    data = df.tail(60)  # last 60 candles
    X = data["Index"].values.reshape(-1,1)
    y = data["Close"].values
    try:
        model = LinearRegression().fit(X, y)
        future_index = np.array([[data["Index"].iloc[-1] + future_days]])
        return model.predict(future_index)[0]
    except:
        return data["Close"].iloc[-1]

#  Stock analysis logic
def analyze_stock(symbol, future_days, capital):
    try:
        df = add_indicators(get_data(symbol))
        pred = predict_price(df, future_days)
        last = df.iloc[-1]
        current = last["Close"]

        score = 0
        if last["SMA_20"] > last["SMA_50"]: score += 1
        if last["EMA_20"] > last["SMA_20"]: score += 1
        if last["RSI"] < 30: score += 1
        if last["RSI"] > 70: score -= 1
        if last["Close"] < last["BB_Low"]: score += 1
        if last["Close"] > last["BB_High"]: score -= 1

        expected = ((pred - current) / current) * 100
        qty = int(capital // current)

        return {
            "Stock": symbol,
            "Price": round(current,2),
            "Predicted": round(pred,2),
            "Expected Return (%)": round(expected,2),
            "Score": score,
            "Quantity": qty
        }
    except:
        return None

#  Main recommendation function
def get_stock_recommendation(duration="1month", capital=20000, risk="low", top_n=5):
    days = duration_days.get(duration, 30)

    results = [
        analyze_stock(sym, days, capital)
        for sym in nifty50_symbols
    ]
    results = [r for r in results if r]

    df = pd.DataFrame(results)

    if df.empty:
        return pd.DataFrame()

    # Filter based on risk preference
    if risk == "low":
        df = df[df["Score"] >= 0]

    #  Sort by expected return
    df = df.sort_values(by="Expected Return (%)", ascending=False)

    return df.head(top_n)
