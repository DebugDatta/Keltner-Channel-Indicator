from __future__ import annotations
import pandas as pd
import yfinance as yf

# Yahoo lookback limits per interval
INTERVAL_LIMITS = {
    "1m":  {"max_days": 7,    "period_hint": "7d",   "note": "1m supports ~7 days"},
    "2m":  {"max_days": 60,   "period_hint": "60d",  "note": "2m supports ~60 days"},
    "5m":  {"max_days": 60,   "period_hint": "60d",  "note": "5m supports ~60 days"},
    "15m": {"max_days": 60,   "period_hint": "60d",  "note": "15m supports ~60 days"},
    "30m": {"max_days": 730,  "period_hint": "730d", "note": "30m supports ~2 years"},
    "1h":  {"max_days": 730,  "period_hint": "730d", "note": "1h supports ~2 years"},
    "90m": {"max_days": 60,   "period_hint": "60d",  "note": "90m supports ~60 days"},
    "1d":  {"max_days": None, "period_hint": "max",  "note": "1d supports decades"},
    "1wk": {"max_days": None, "period_hint": "max",  "note": "1wk supports decades"},
    "1mo": {"max_days": None, "period_hint": "max",  "note": "1mo supports decades"},
}

def interval_limit(interval: str) -> dict:
    interval = (interval or "1d").lower()
    return INTERVAL_LIMITS.get(interval, INTERVAL_LIMITS["1d"])

def _is_ohlc_frame(df: pd.DataFrame) -> bool:
    lc = {str(c).strip().lower() for c in df.columns}
    needed = {"open","high","low","close"}
    return needed.issubset(lc)

def _flatten_columns(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        lvl0 = [str(x) for x in df.columns.get_level_values(0).unique()]
        if len(lvl0) == 1:
            df = df.droplevel(0, axis=1)
        else:
            if ticker in lvl0:
                df = df.xs(ticker, axis=1, level=0)
            else:
                df = df.xs(lvl0[0], axis=1, level=0)
        return df
    if len(df.columns) == 1:
        only = df.columns[0]
        sub = df[only]
        if isinstance(sub, pd.DataFrame) and sub.shape[1] >= 4:
            return sub
    return df

def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    lc_map = {str(c).strip().lower(): c for c in df.columns}
    def find(*names: str):
        for n in names:
            if n in lc_map:
                return lc_map[n]
        return None

    o = find("open")
    h = find("high")
    l = find("low")
    c = find("close")
    ac = find("adj close","adjclose","adjusted close")
    v = find("volume")

    missing = []
    if o is None: missing.append("Open")
    if h is None: missing.append("High")
    if l is None: missing.append("Low")
    if c is None: missing.append("Close")
    if missing:
        raise KeyError(f"Required columns missing: {missing}. Got columns: {list(df.columns)}")

    ren = {o:"Open", h:"High", l:"Low", c:"Close"}
    if ac is not None: ren[ac] = "Adj Close"
    if v is not None: ren[v] = "Volume"

    out = df.rename(columns=ren)
    keep = [x for x in ["Open","High","Low","Close","Adj Close","Volume"] if x in out.columns]
    return out[keep]

def _fetch_download(ticker: str, start: str|None, end: str|None, period: str|None, interval: str) -> pd.DataFrame:
    if period:
        raw = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False, group_by="column")
    else:
        raw = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=False, progress=False, group_by="column")
    if raw is None or raw.empty:
        raise ValueError(f"No data returned by yfinance.download for {ticker} interval={interval}.")
    return raw

def _fetch_history(ticker: str, start: str|None, end: str|None, period: str|None, interval: str) -> pd.DataFrame:
    tk = yf.Ticker(ticker)
    if period:
        raw = tk.history(period=period, interval=interval, auto_adjust=False)
    else:
        raw = tk.history(start=start, end=end, interval=interval, auto_adjust=False)
    if raw is None or raw.empty:
        raise ValueError(f"No data returned by yfinance.Ticker.history for {ticker} interval={interval}.")
    return raw

def fetch_ohlc(ticker: str, start: str|None = None, end: str|None = None,
               period: str|None = None, interval: str = "1d") -> pd.DataFrame:
    lim = interval_limit(interval)
    print(f"[info] Interval {interval}: max lookback {lim['period_hint']}  {lim['note']}")

    raw = _fetch_download(ticker, start, end, period, interval)
    df = _flatten_columns(raw, ticker)
    if not _is_ohlc_frame(df):
        raw2 = _fetch_history(ticker, start, end, period, interval)
        df2 = _flatten_columns(raw2, ticker)
        if not _is_ohlc_frame(df2):
            raise KeyError(
                f"Could not find OHLC columns after two fetch attempts. "
                f"download columns: {list(raw.columns)}, history columns: {list(raw2.columns)}"
            )
        df = df2

    df = _standardize_columns(df)
    if df[["Open","High","Low","Close"]].isna().all().all():
        raise ValueError(f"Downloaded data is all NaNs for {ticker}. Columns: {list(df.columns)}")
    return df
