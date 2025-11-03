from __future__ import annotations
import pandas as pd
import numpy as np

def ema(s: pd.Series, length: int) -> pd.Series:
    return s.ewm(span=length, adjust=False, min_periods=length).mean()

def true_range(h: pd.Series, l: pd.Series, c: pd.Series) -> pd.Series:
    pc = c.shift(1)
    return pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)

def atr(h: pd.Series, l: pd.Series, c: pd.Series, length: int) -> pd.Series:
    tr = true_range(h, l, c)
    return tr.ewm(alpha=1.0/length, adjust=False, min_periods=length).mean()

def _get(df: pd.DataFrame, name: str) -> pd.Series:
    # robust access, case insensitive
    for col in df.columns:
        if str(col).strip().lower() == name.lower():
            return df[col].astype(float)
    raise KeyError(f"Column '{name}' not found. Available: {list(df.columns)}")

def keltner_channel(df: pd.DataFrame, ema_len: int = 20, atr_len: int = 10, mult: float = 2.0) -> pd.DataFrame:
    out = df.copy()
    h, l, c = _get(out,"High"), _get(out,"Low"), _get(out,"Close")
    typ = (h + l + c) / 3.0
    mid = ema(typ, ema_len)
    a = atr(h, l, c, atr_len)
    up = mid + mult * a
    lo = mid - mult * a
    width = (up - lo).replace(0, np.nan)
    out["KC_Middle"] = mid
    out["KC_Upper"] = up
    out["KC_Lower"] = lo
    out["KC_Width"] = width
    out["KC_ATR"] = (up - lo) / (2.0 * mult)
    with np.errstate(divide="ignore", invalid="ignore"):
        out["KC_PercentB"] = ((c - lo) / width).clip(0, 1)
    return out
