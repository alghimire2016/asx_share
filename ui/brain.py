import pandas as pd
import streamlit as st
import numpy as np

from storage import load_csv, save_csv, today_str, normalise_brain, safe_float
from strategy import success_score
from data_sources import get_hist

def render_brain(brain_file):
    st.subheader("Brain → Success Score /100 (auto-evaluated)")

    brain = normalise_brain(load_csv(brain_file))
    if brain.empty:
        st.info("No predictions yet. Run the scanner.")
        return

    updated = []
    for _, row in brain.iterrows():
        try:
            if str(row["Status"]) == "PENDING" and str(row["TargetDate"]).strip():
                td = pd.to_datetime(row["TargetDate"], errors="coerce")
                if pd.notna(td) and td <= pd.Timestamp.now():
                    ticker = str(row["Ticker"]).upper().strip()
                    entry_date = pd.to_datetime(row["EntryDate"], errors="coerce")
                    target = safe_float(row["TargetPrice"])

                    h = get_hist(f"{ticker}.AX", period="400d")
                    if h is None or h.empty or pd.isna(entry_date):
                        updated.append(row)
                        continue

                    hs = h.copy()
                    hs.index = pd.to_datetime(hs.index)
                    window = hs.loc[(hs.index >= (entry_date - pd.Timedelta(days=2))) & (hs.index <= (td + pd.Timedelta(days=2)))]

                    max_high = float(window["High"].max()) if not window.empty else float(hs["High"].iloc[-1])

                    if max_high >= target:
                        row["Status"] = "MET"
                        row["MissPct"] = 0.0
                    else:
                        row["Status"] = "MISSED"
                        miss_pct = ((target - max_high) / target) * 100.0 if target > 0 else 100.0
                        row["MissPct"] = round(max(0.0, miss_pct), 2)

                    row["CheckedOn"] = today_str()
        except:
            pass
        updated.append(row)

    brain2 = pd.DataFrame(updated)
    save_csv(brain2, brain_file)

    done = brain2[brain2["Status"].isin(["MET","MISSED"])].copy()
    sc = success_score(done)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Success Score", f"{sc}/100")
    c2.metric("Completed", f"{len(done)}")
    c3.metric("Pending", f"{len(brain2) - len(done)}")
    hit_rate = (done["Status"] == "MET").mean() * 100.0 if len(done) else 0.0
    c4.metric("Hit Rate", f"{hit_rate:.1f}%")

    if len(done):
        avg_miss = done.loc[done["Status"] == "MISSED", "MissPct"].mean()
        avg_miss = float(avg_miss) if np.isfinite(avg_miss) else 0.0
        st.metric("Avg Miss % (when missed)", f"{avg_miss:.2f}%")

    st.dataframe(brain2.sort_values(["EntryDate","Ticker"], ascending=[False, True]), use_container_width=True)
