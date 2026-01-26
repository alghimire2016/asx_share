import time
import streamlit as st
import yfinance as yf
import pandas as pd
from yfinance.exceptions import YFRateLimitError

from asx_calendar import get_asx_status


def _backoff(attempt: int):
    time.sleep(min(3.0, 0.8 * (2 ** attempt)))


@st.cache_data(ttl=60 * 5, show_spinner=False)
def _get_hist_live(symbol: str, period="400d") -> pd.DataFrame:
    # shorter TTL during market hours
    for attempt in range(2):
        try:
            return yf.Ticker(symbol).history(period=period)
        except YFRateLimitError:
            _backoff(attempt)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def _get_hist_closed(symbol: str, period="400d") -> pd.DataFrame:
    # long TTL after-hours (12h) to avoid repeated hits
    try:
        return yf.Ticker(symbol).history(period=period)
    except Exception:
        return pd.DataFrame()


def get_hist(symbol: str, period="400d") -> pd.DataFrame:
    status = get_asx_status()
    if status.is_open:
        return _get_hist_live(symbol, period=period)
    return _get_hist_closed(symbol, period=period)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def get_dividends(symbol: str) -> pd.Series:
    for attempt in range(2):
        try:
            return yf.Ticker(symbol).dividends
        except YFRateLimitError:
            _backoff(attempt)
        except Exception:
            return pd.Series(dtype="float64")
    return pd.Series(dtype="float64")


def validate_asx_ticker(ticker: str) -> bool:
    h = get_hist(f"{ticker}.AX", period="10d")
    return h is not None and not h.empty


def last_close(symbol: str) -> float:
    h = get_hist(symbol, period="10d")
    if h is None or h.empty:
        return float("nan")
    return float(h["Close"].iloc[-1])
