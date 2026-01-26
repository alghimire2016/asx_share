import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime

from storage import today_str, load_csv, save_csv, normalise_brain
from strategy import choose_best_horizon, dividend_metrics, stock_type, regime_asx200
from data_sources import validate_asx_ticker, get_hist
from indicators import compute_atr

def render_scanner(brain_file, horizons, target_atr_mult, stop_atr_mult, top_n):
    st.subheader("Scanner → Top Picks → Save to Brain")

    tickers_text = st.text_area(
        "Paste ASX tickers (space/comma separated)",
        value="CBA BHP RIO FMG WES XRO MQG WOW ANZ NAB WBC CSL PLS"
    ).strip()

    tickers = [t.upper().strip() for t in tickers_text.replace(",", " ").split() if t.strip()]
    tickers = list(dict.fromkeys(tickers))

    st.caption("Rules: RR>=1.5, Confidence>=55%. Growth in BEAR/STORM is blocked.")
    run = st.button("🔥 RUN SCAN", type="primary")

    if not run:
        st.markdown("<div class='smallNote'>Tip: Start with 10–20 tickers to avoid Yahoo rate limits.</div>", unsafe_allow_html=True)
        return

    scan_rows = []
    rejected_rows = []
    trend, vol = regime_asx200()

    prog = st.progress(0, text="Scanning...")
    for i, t in enumerate(tickers):
        prog.progress(int((i+1)/max(1,len(tickers))*100), text=f"Scanning {t}...")

        if not validate_asx_ticker(t):
            rejected_rows.append({"Ticker": t, "Reason": "INVALID_TICKER"})
            continue

        best = choose_best_horizon(t, horizons, target_atr_mult, stop_atr_mult)
        if "RejectReason" in best:
            rejected_rows.append({"Ticker": t, "Reason": best["RejectReason"]})
            continue

        _, _, _, div_yield = dividend_metrics(t, 1, today_str())
        h = get_hist(f"{t}.AX", period="260d")
        atr_val = compute_atr(h, 14) if (h is not None and not h.empty) else best["ATR"]
        ttype = stock_type(float(best["Price"]), float(atr_val), float(div_yield))

        if ttype == "🔥 Growth" and (trend == "BEAR" or vol == "STORM"):
            rejected_rows.append({"Ticker": t, "Reason": f"REGIME_BLOCK({trend}/{vol})"})
            continue

        rr = float(best["RR"])
        conf = float(best["ConfidencePct"])
        if rr < 1.5:
            rejected_rows.append({"Ticker": t, "Reason": "LOW_RR"})
            continue
        if conf < 55:
            rejected_rows.append({"Ticker": t, "Reason": "LOW_CONF"})
            continue

        scan_rows.append({
            "Ticker": t,
            "Type": ttype,
            "Price": best["Price"],
            "Target": best["Target"],
            "Stop": best["Stop"],
            "RR": best["RR"],
            "Confidence %": best["ConfidencePct"],
            "Horizon": f'{best["HorizonDays"]}d',
            "Target Date": best["TargetDate"],
            "RSI": round(best["RSI"], 1) if np.isfinite(best.get("RSI", np.nan)) else np.nan,
            "Div Yield %": round(div_yield, 2),
            "_score": best["score"]
        })

    prog.empty()

    if not scan_rows:
        st.warning("No tickers passed filters. Check rejected list below.")
    else:
        scan_df = pd.DataFrame(scan_rows).sort_values("_score", ascending=False).head(top_n)
        st.dataframe(scan_df.drop(columns=["_score"]), use_container_width=True)

        brain = normalise_brain(load_csv(brain_file))

        new_entries = []
        for _, r in scan_df.iterrows():
            pred_id = f"P{int(datetime.now().timestamp())}_{r['Ticker']}"

            entry_price = float(r["Price"])
            target_price = float(r["Target"])
            stop_price = float(r["Stop"])
            conf_pct = float(r["Confidence %"])

            new_entries.append({
                "PredID": pred_id,
                "Ticker": r["Ticker"],
                "EntryDate": today_str(),
                "EntryPrice": entry_price,
                "TargetPrice": target_price,
                "StopPrice": stop_price,
                "TargetDate": r["Target Date"],
                "HorizonDays": int(str(r["Horizon"]).replace("d","")),
                "ExpectedProfit": round(target_price - entry_price, 3),
                "ConfidencePct": conf_pct,
                "Type": r["Type"],
                "Status": "PENDING",
                "MissPct": np.nan,
                "CheckedOn": "",
                "RejectReason": ""
            })

        brain2 = pd.concat([brain, pd.DataFrame(new_entries)], ignore_index=True)
        brain2 = brain2.drop_duplicates(subset=["Ticker","EntryDate","TargetDate"], keep="last")
        save_csv(brain2, brain_file)
        st.success(f"Saved {len(new_entries)} predictions to Brain ✅")

    if rejected_rows:
        with st.expander("Rejected tickers (why)"):
            st.dataframe(pd.DataFrame(rejected_rows), use_container_width=True)
