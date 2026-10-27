import time
import streamlit as st
import pandas as pd
import yfinance as yf
from screener import calculate_squeeze_signals, get_option_metrics

st.set_page_config(page_title="Vol Squeeze Screener", layout="wide")
st.title("🎯 Volatility Squeeze Scanner")

DEFAULT_TICKERS = "SPY, QQQ, IWM, SMH, XBI, XLF, XLE, GLD, COIN, PLTR, NFLX, CRWD, ARM, SMCI, SHOP, PANW, AAPL, MSFT, NVDA, AMZN, TSLA, META, AMD, NFLX, COIN, KRMN, PFE, TSM, GE, PWR, LRCX, DDOG, ETN, FPS, SNPS, STRL, ANET, CRM, HONA, FN, GE, GEV, BA, CECO, SPCX, GLD, GLW, CAT, KTOS, CIEN, AVGO, RKLB, RGTI, QNT, QCOM, DE, CRDO, IBM, MRVL, NOW, IONQ, RVMD,  JNJ, MEDP"
user_input = st.text_area("Watchlist (comma separated)", value=DEFAULT_TICKERS)
tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# Option to show only qualified squeeze setups (Score >= 3) or everything
show_all = st.checkbox("Show all tickers (including non-squeezes)", value=False)

if st.button("🚀 Run Squeeze Scan", use_container_width=True):
    with st.spinner("Analyzing volatility regimes & options data..."):
        results = []
        progress_bar = st.progress(0)

        for i, sym in enumerate(tickers):
            try:
                df = yf.download(sym, period="1y", interval="1d", progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                sig = calculate_squeeze_signals(df)
                if sig:
                    is_candidate = sig["qualified"] if not show_all else True

                    if is_candidate:
                        # Pull option chain using known price
                        opt = get_option_metrics(sym, current_price=sig["price"])
                        time.sleep(0.15)  # Prevents Yahoo rate limiting

                        results.append({
                            "Symbol": sym,
                            "Price": sig["price"],
                            "Score": sig["score"],
                            "TTM Squeeze": "🔥 YES" if sig["ttm_squeeze"] else "NO",
                            "BBW Pctile": f"{sig['bbw_pct']}%",
                            "ATR Ratio": sig["atr_ratio"],
                            "ADX": sig["adx"],
                            "ATM IV": opt["atm_iv"],
                            "Target Exp": opt["expiry"],
                            "DTE": opt["dte"]
                        })
            except Exception:
                pass
            finally:
                progress_bar.progress((i + 1) / len(tickers))

        progress_bar.empty()

        if results:
            res_df = pd.DataFrame(results)

            # --- SORTING ENHANCEMENT ---
            # Extract raw numeric BBW percentile for clean mathematical sorting
            res_df["_sort_bbw"] = (
                res_df["BBW Pctile"]
                .astype(str)
                .str.rstrip("%")
                .replace("N/A", "999")
                .astype(float)
            )

            # Sort: highest Score first (e.g. 3/4 before 2/4), then tightest BBW (ascending)
            res_df = res_df.sort_values(
                by=["Score", "_sort_bbw"],
                ascending=[False, True]
            ).drop(columns=["_sort_bbw"])
            # ---------------------------
            st.dataframe(res_df, use_container_width=True)
        else:
            st.info("No tickers currently meet the criteria.")
