import streamlit as st
import pandas as pd
import yfinance as yf
from screener import calculate_squeeze_signals, get_option_metrics

st.set_page_config(page_title="Vol Squeeze Screener", layout="wide")
st.title("🎯 Volatility Squeeze Scanner")

DEFAULT_TICKERS = "SPY, QQQ, IWM, AAPL, MSFT, NVDA, AMZN, TSLA, META, AMD, NFLX, JNJ, PFE, NVDA, RVMD, DYN, ARGX, VSTM, BMY, SOLS, SNY, URGN, KRMN, KNSA, JAZZ, BLLN, AZN, GRAL, IONQ, GILD, NTRA, VRTX, NOW, MEDP, HD, GH, MRVL, TSM, MP, NKE, IBM, GSK, CRDO, COIN"
user_input = st.text_area("Watchlist (comma separated)", value=DEFAULT_TICKERS)
tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]

if st.button("🚀 Run Squeeze Scan", use_container_width=True):
    with st.spinner("Analyzing volatility regimes..."):
        results = []
        for sym in tickers:
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                sig = calculate_squeeze_signals(df)
                if sig and sig["qualified"]:
                    opt = get_option_metrics(sym)
                    results.append({
                        "Symbol": sym,
                        "Price": sig["price"],
                        "Score": sig["score"],
                        "TTM Squeeze": "🔥 YES" if sig["ttm_squeeze"] else "NO",
                        "BBW Pctile": f"{sig['bbw_pct']}%",
                        "ATR Ratio": sig["atr_ratio"],
                        "ADX": sig["adx"],
                        "ATM IV": opt["atm_iv"],
                        "Target Exp": opt["expiry"]
                    })
            except Exception:
                continue

        if results:
            res_df = pd.DataFrame(results)
            st.dataframe(res_df, use_container_width=True)
        else:
            st.info("No tickers currently meet 3+ squeeze conditions.")
