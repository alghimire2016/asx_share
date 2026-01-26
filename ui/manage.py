import streamlit as st
import pandas as pd
from datetime import datetime

from storage import load_csv, save_csv, normalise_portfolio, today_str, safe_int, safe_float
from data_sources import validate_asx_ticker

def render_manage(db_file, brain_file, default_buy_fee, default_sell_fee):
    st.subheader("Manage Portfolio")

    portfolio = normalise_portfolio(load_csv(db_file))
    open_trades = portfolio[portfolio["Status"] == "OPEN"].copy()

    st.markdown("### Add BUY")
    with st.form("add_buy", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        in_t = c1.text_input("ASX Ticker").upper().strip()
        in_d = c2.date_input("Buy Date", value=datetime.now())
        in_s = c3.number_input("Shares", min_value=1, value=100, step=1)

        c4, c5 = st.columns(2)
        in_p = c4.number_input("Buy Price", min_value=0.001, value=1.000, format="%.3f")
        in_bf = c5.number_input("Buy Fee ($)", min_value=0.0, value=float(default_buy_fee), step=0.5)

        if st.form_submit_button("Register BUY"):
            if not in_t or not validate_asx_ticker(in_t):
                st.error("Invalid ASX ticker.")
            else:
                trade_id = f"T{int(datetime.now().timestamp())}_{in_t}"
                new_row = pd.DataFrame([{
                    "TradeID": trade_id,
                    "Ticker": in_t,
                    "BuyDate": in_d.strftime("%Y-%m-%d"),
                    "BuyPrice": float(in_p),
                    "Shares": int(in_s),
                    "OriginalShares": int(in_s),
                    "BuyFee": float(in_bf),
                    "SellFee": float(default_sell_fee),
                    "Status": "OPEN",
                    "SellDate": "",
                    "SellPrice": 0.0,
                    "CreatedOn": today_str()
                }])
                portfolio2 = pd.concat([portfolio, new_row], ignore_index=True)
                save_csv(portfolio2, db_file)
                st.success(f"Added OPEN trade: {in_t} ✅")
                st.rerun()

    st.divider()
    st.markdown("### SELL (choose from OPEN positions)")

    if open_trades.empty:
        st.info("No OPEN positions to sell.")
    else:
        open_disp = open_trades.reset_index(drop=False)
        open_disp["display"] = open_disp.apply(
            lambda r: f"{r['Ticker']} | Buy {r['BuyDate']} | Remaining {safe_int(r['Shares'])} @ {safe_float(r['BuyPrice']):.3f}",
            axis=1
        )
        pick = st.selectbox("Select position", open_disp["display"].tolist())
        chosen = open_disp.loc[open_disp["display"] == pick].iloc[0]
        row_index = int(chosen["index"])

        ticker = str(chosen["Ticker"]).upper().strip()
        remaining = safe_int(chosen["Shares"])
        orig = safe_int(chosen.get("OriginalShares", remaining))
        buy_fee_remaining = safe_float(chosen.get("BuyFee", default_buy_fee))

        c1, c2, c3, c4 = st.columns(4)
        sell_date = c1.date_input("Sell date", value=datetime.now())
        sell_price = c2.number_input("Sell price", min_value=0.001, value=float(chosen["BuyPrice"]), format="%.3f")
        units_sold = c3.number_input("Units sold", min_value=1, max_value=max(1, remaining), value=min(remaining, 10), step=1)
        sell_fee = c4.number_input("Sell fee ($)", min_value=0.0, value=float(default_sell_fee), step=0.5)

        if st.button("Execute SELL", type="primary"):
            if units_sold > remaining:
                st.error("Units sold cannot exceed remaining shares.")
            else:
                denom = orig if orig > 0 else remaining
                frac = units_sold / denom
                alloc_buy_fee = round(buy_fee_remaining * frac, 6)
                new_buy_fee_remaining = max(0.0, buy_fee_remaining - alloc_buy_fee)

                closed_id = f"S{int(datetime.now().timestamp())}_{ticker}"
                closed_row = pd.DataFrame([{
                    "TradeID": closed_id,
                    "Ticker": ticker,
                    "BuyDate": str(chosen["BuyDate"]),
                    "BuyPrice": float(chosen["BuyPrice"]),
                    "Shares": int(units_sold),
                    "OriginalShares": int(units_sold),
                    "BuyFee": float(alloc_buy_fee),
                    "SellFee": float(sell_fee),
                    "Status": "CLOSED",
                    "SellDate": sell_date.strftime("%Y-%m-%d"),
                    "SellPrice": float(sell_price),
                    "CreatedOn": today_str()
                }])

                portfolio2 = portfolio.copy()
                new_remaining = remaining - int(units_sold)

                # clean: if fully sold, DROP open row
                if new_remaining <= 0:
                    portfolio2 = portfolio2.drop(index=row_index).reset_index(drop=True)
                else:
                    portfolio2.at[row_index, "Shares"] = int(new_remaining)
                    portfolio2.at[row_index, "BuyFee"] = float(new_buy_fee_remaining)

                portfolio2 = pd.concat([portfolio2, closed_row], ignore_index=True)
                save_csv(portfolio2, db_file)
                st.success(f"SELL recorded ✅ {ticker} sold {units_sold} @ {sell_price:.3f}")
                st.rerun()

    st.divider()
    st.subheader("Utilities (danger)")
    c1, c2 = st.columns(2)
    if c1.button("Clear Brain (danger)"):
        save_csv(pd.DataFrame(), brain_file)
        st.warning("Brain cleared.")
    if c2.button("Clear Portfolio (danger)"):
        save_csv(pd.DataFrame(), db_file)
        st.warning("Portfolio cleared.")
