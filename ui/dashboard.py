import numpy as np
import pandas as pd
import streamlit as st

from storage import safe_float, safe_int
from data_sources import get_hist
from strategy import (
    dividend_metrics,
    net_pl_price_only,
    recommend_signal,
    stock_type,
    regime_asx200,
    choose_best_horizon,
    days_to_profit_again_from_history,
    estimate_daily_return_stats,
)

SIG_RANK = {
    "SELL ✅ (Target)": 0,
    "SELL ❌ (Stop)": 1,
    "HOLD ✅ (Strong)": 2,
    "HOLD ✅": 3,
    "HOLD ⚠️": 4,
    "DATA ⚠️": 9,
}


def render_dashboard(portfolio, horizons, target_atr_mult, stop_atr_mult, default_buy_fee, default_sell_fee):
    st.subheader("Portfolio Dashboard")

    trend, vol = regime_asx200()
    st.caption(f"Market regime (ASX200 proxy): **{trend} / {vol}**")

    if portfolio is None or portfolio.empty:
        st.info("Portfolio is empty. Use MANAGE → Add BUY.")
        return

    open_trades = portfolio[portfolio["Status"] == "OPEN"].copy()

    rows = []
    rejected = []

    invested_total = 0.0
    total_pl_incl_div = 0.0
    total_div_paid = 0.0
    total_div_12m = 0.0

    # Toggle: show drift/vol columns
    show_stats = st.toggle("Show drift/vol stats", value=False)

    for _, t in open_trades.iterrows():
        ticker = str(t.get("Ticker", "")).upper().strip().replace(".AX", "")
        buy_date = str(t.get("BuyDate", ""))
        buy_price = safe_float(t.get("BuyPrice", 0.0))
        shares = safe_int(t.get("Shares", 0))
        buy_fee = safe_float(t.get("BuyFee", default_buy_fee))
        sell_fee = safe_float(t.get("SellFee", default_sell_fee))

        if not ticker or shares <= 0 or buy_price <= 0:
            rejected.append(
                {"Ticker": ticker, "Reason": "INVALID_ROW", "Shares": shares, "BuyPrice": buy_price, "Status": t.get("Status", "")}
            )
            continue

        invested = buy_price * shares + buy_fee
        invested_total += invested

        # ONE history call per ticker (cached in data_sources)
        h = get_hist(f"{ticker}.AX", period="400d")

        # dividends
        _, annual_div, paid_div, div_yield = dividend_metrics(ticker, shares, buy_date)
        total_div_paid += paid_div
        total_div_12m += annual_div

        # current price + day change (from same history)
        if h is not None and not h.empty and "Close" in h.columns:
            cp = float(h["Close"].iloc[-1])
            prev = float(h["Close"].iloc[-2]) if len(h) >= 2 else np.nan
            day_pct = ((cp - prev) / prev) * 100 if np.isfinite(prev) and prev > 0 else np.nan
        else:
            cp = np.nan
            day_pct = np.nan

        # P/L
        pl_price = net_pl_price_only(buy_price, cp, shares, buy_fee, sell_fee) if np.isfinite(cp) else np.nan
        pl_total = (pl_price + paid_div) if np.isfinite(pl_price) else np.nan
        if np.isfinite(pl_total):
            total_pl_incl_div += pl_total

        # Targets/stops/confidence (may reject)
        best = choose_best_horizon(ticker, horizons, target_atr_mult, stop_atr_mult)

        if "RejectReason" in best or not np.isfinite(cp):
            target = np.nan
            stop = np.nan
            conf = np.nan
            horizon = horizons[0] if horizons else 20
            rsi = np.nan
            sig = "DATA ⚠️"
            ttype = "—"
        else:
            target = safe_float(best.get("Target", np.nan))
            stop = safe_float(best.get("Stop", np.nan))
            conf = safe_float(best.get("ConfidencePct", np.nan))
            horizon = safe_int(best.get("HorizonDays", 20), 20)
            rsi = safe_float(best.get("RSI", np.nan), np.nan)

            atr = safe_float(best.get("ATR", np.nan), np.nan)
            ttype = stock_type(cp, atr if np.isfinite(atr) else 0.0, div_yield)

            sig = recommend_signal(cp, target, stop, conf if np.isfinite(conf) else 0.0, rsi)

        # P/L percent
        pl_pct = (pl_price / max(0.0001, buy_price * shares) * 100) if np.isfinite(pl_price) else np.nan

        # Days to profit again (REAL: based on history drift)
        dte = None
        mu = np.nan
        sigma = np.nan
        if np.isfinite(cp) and h is not None and not h.empty:
            dte = days_to_profit_again_from_history(
                buy_price=buy_price,
                now_price=cp,
                h=h,
                lookback_days=90,
                max_days_cap=365,
            )
            mu, sigma = estimate_daily_return_stats(h, lookback_days=90)

        row = {
            "Ticker": ticker,
            "Type": ttype,
            "Shares": shares,
            "Buy Date": buy_date,
            "Buy": round(buy_price, 4),
            "Now": round(cp, 4) if np.isfinite(cp) else np.nan,
            "Day %": round(day_pct, 2) if np.isfinite(day_pct) else np.nan,
            "Target": round(target, 4) if np.isfinite(target) else np.nan,
            "Stop": round(stop, 4) if np.isfinite(stop) else np.nan,
            "Confidence %": round(conf, 1) if np.isfinite(conf) else np.nan,
            "Div Yield %": round(div_yield, 2),
            "Expected Div 12M $": round(annual_div, 2),
            "Div Paid (since buy) $": round(paid_div, 2),
            "P/L $ (incl div)": round(pl_total, 2) if np.isfinite(pl_total) else np.nan,
            "P/L % (price)": round(pl_pct, 2) if np.isfinite(pl_pct) else np.nan,
            "Days to Profit Again": dte,
            "Signal": sig,
        }

        if show_stats:
            row["Avg %/day"] = round(mu * 100, 3) if np.isfinite(mu) else np.nan
            row["Vol %/day"] = round(sigma * 100, 3) if np.isfinite(sigma) else np.nan

        rows.append(row)

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Open positions", f"{len(open_trades)}")
    c2.metric("Invested (est)", f"${invested_total:,.2f}")
    c3.metric("P/L (incl div)", f"${total_pl_incl_div:,.2f}")
    c4.metric("Div 12M (expected)", f"${total_div_12m:,.2f}")

    if not rows:
        st.warning("No OPEN positions found or all rows invalid.")
        if rejected:
            with st.expander("Why rows were rejected"):
                st.dataframe(pd.DataFrame(rejected), use_container_width=True)
        return

    df = pd.DataFrame(rows)
    df["_sig_rank"] = df["Signal"].map(SIG_RANK).fillna(99)
    df = df.sort_values(["_sig_rank", "P/L $ (incl div)"], ascending=[True, False]).drop(columns=["_sig_rank"])

    st.dataframe(df, use_container_width=True)

    if rejected:
        with st.expander("Why rows were rejected / missing data (debug)"):
            st.dataframe(pd.DataFrame(rejected), use_container_width=True)
