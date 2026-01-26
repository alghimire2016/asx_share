import numpy as np
import pandas as pd

def compute_atr(h: pd.DataFrame, n=14) -> float:
    """True ATR (includes gaps)"""
    try:
        high = h["High"]
        low = h["Low"]
        close = h["Close"]
        prev_close = close.shift(1)

        tr = pd.concat([
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)

        atr = tr.rolling(n).mean().iloc[-1]
        return float(atr) if np.isfinite(atr) else np.nan
    except:
        return np.nan

def compute_rsi(close: pd.Series, n=14) -> float:
    try:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(n).mean()
        loss = (-delta.clip(upper=0)).rolling(n).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        v = float(rsi.iloc[-1])
        return v if np.isfinite(v) else np.nan
    except:
        return np.nan
