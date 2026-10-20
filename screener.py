import numpy as np
import pandas as pd
import yfinance as yf

def calculate_squeeze_signals(df: pd.DataFrame) -> dict:
    if len(df) < 130:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    # 1. Bollinger Bands
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = sma20 + (2.0 * std20)
    bb_lower = sma20 - (2.0 * std20)
    bbw = (bb_upper - bb_lower) / sma20

    # 2. True Range & ATR
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    atr50 = atr14.rolling(50).mean()

    # Keltner Channels (20, 1.5 ATR)
    kc_upper = sma20 + (1.5 * atr14)
    kc_lower = sma20 - (1.5 * atr14)

    # 3. ADX (14)
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr14)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr14)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx14 = dx.rolling(14).mean()

    # Rolling 6-month (126 days) BBW Percentile Rank
    bbw_pctile = bbw.rolling(126).apply(lambda s: (s.iloc[-1] >= s).mean(), raw=False)

    latest_bbw_pct = float(bbw_pctile.iloc[-1])
    is_ttm_squeeze = bool(bb_upper.iloc[-1] <= kc_upper.iloc[-1] and bb_lower.iloc[-1] >= kc_lower.iloc[-1])
    atr_ratio = float(atr14.iloc[-1] / atr50.iloc[-1]) if pd.notnull(atr50.iloc[-1]) else 1.0
    latest_adx = float(adx14.iloc[-1]) if pd.notnull(adx14.iloc[-1]) else 25.0

    c1_bbw = latest_bbw_pct <= 0.10
    c2_ttm = is_ttm_squeeze
    c3_atr = atr_ratio <= 0.70
    c4_adx = latest_adx <= 20.0

    score = sum([c1_bbw, c2_ttm, c3_atr, c4_adx])

    return {
        "price": round(float(close.iloc[-1]), 2),
        "score": f"{score}/4",
        "ttm_squeeze": c2_ttm,
        "bbw_pct": round(latest_bbw_pct * 100, 1),
        "atr_ratio": round(atr_ratio, 2),
        "adx": round(latest_adx, 1),
        "qualified": score >= 3
    }

def get_option_metrics(ticker_str: str) -> dict:
    tk = yf.Ticker(ticker_str)
    try:
        expirations = tk.options
        if not expirations:
            return {"atm_iv": "N/A", "expiry": "None"}
        
        target_exp = expirations[min(len(expirations)-1, 1)]
        chain = tk.option_chain(target_exp)
        calls = chain.calls
        
        current_price = tk.fast_info.get("lastPrice", None)
        if current_price is None or calls.empty:
            return {"atm_iv": "N/A", "expiry": target_exp}

        atm_call = calls.iloc[(calls["strike"] - current_price).abs().argsort()[:1]]
        atm_iv = round(float(atm_call["impliedVolatility"].iloc[0]) * 100, 1) if not atm_call.empty else "N/A"
        
        return {
            "atm_iv": f"{atm_iv}%",
            "expiry": target_exp
        }
    except Exception:
        return {"atm_iv": "N/A", "expiry": "None"}
