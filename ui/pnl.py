import numpy as np
import pandas as pd
import streamlit as st

from storage import load_csv, normalise_portfolio, safe_float, safe_int, today_str
from strategy import net_pl_price_only, dividend_metrics

def render_pnl(db_file, default_buy_fee, default_sell_fee):
    st.subheader("P&L History (Closed Trades)")

    portfolio = normalise_portfolio(load_csv(db_file))
    closed = portfolio[portfolio["Status"] == "CLOSED"].copy()

    if closed.empty:
        st.info("No CLOSED trades yet. Use MANAGE → SELL.")
        return

    rows = []
    wins = 0
    total_closed_pl = 0.0
    total_closed_inv = 0.0
    total_closed_div = 0.0

    for _, t in closed.iterrows():
        try:
            ticker = str(t["Ticker"]).upper().strip()
            buy_date = str(t["BuyDate"])
            sell_date = str(t["SellDate"]) if str(t["SellDate"]).strip() else today_str()
            buy_price = safe_float(t["BuyPrice"])
            sell_price = safe_float(t["SellPrice"])
            shares = safe_int(t["Shares"])
            buy_fee = safe_float(t.get("BuyFee", default_buy_fee))
            sell_fee = safe_float(t.get("SellFee", default_sell_fee))

            if shares <= 0 or buy_price <= 0 or sell_price <= 0:
                continue

            pl_price = net_pl_price_only(buy_price, sell_price, shares, buy_fee, sell_fee)
            _, _, paid_div, _ = dividend_metrics(ticker, shares, buy_date, sell_date)

            pl_total = pl_price + paid_div

            invested = buy_price * shares + buy_fee
            total_closed_inv += invested
            total_closed_pl += pl_total
            total_closed_div += paid_div

            if pl_total > 0:
                wins += 1

            rows.append({
                "TradeID": t.get("TradeID",""),
                "Ticker": ticker,
                "BuyDate": buy_date,
                "SellDate": sell_date,
                "Shares": shares,
                "BuyPrice": round(buy_price, 3),
                "SellPrice": round(sell_price, 3),
                "Div Paid $": round(paid_div, 2),
                "Net P/L Price $": round(pl_price, 2),
                "Net P/L incl Div $": round(pl_total, 2),
            })
        except:
            continue

    pnl_df = pd.DataFrame(rows).sort_values("SellDate", ascending=False)

    profit_score = (wins / len(pnl_df)) * 100.0 if len(pnl_df) else 0.0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Closed Trades", f"{len(pnl_df)}")
    c2.metric("Profit Score", f"{profit_score:.1f}%")
    c3.metric("Total Closed P/L (incl div)", f"${total_closed_pl:,.2f}")
    c4.metric("Total Closed Div", f"${total_closed_div:,.2f}")

    if total_closed_inv > 0:
        st.metric("Closed Total Return %", f"{(total_closed_pl / total_closed_inv) * 100:.2f}%")

    st.dataframe(
        pnl_df.style.applymap(
            lambda v: "color:#3fb950; font-weight:900" if isinstance(v,(int,float)) and v > 0 else
                      "color:#f85149; font-weight:900" if isinstance(v,(int,float)) and v < 0 else "",
            subset=["Net P/L Price $", "Net P/L incl Div $"]
        ),
        use_container_width=True
    )
