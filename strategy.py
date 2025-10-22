from __future__ import annotations
import pandas as pd

def breakout_signals(df: pd.DataFrame, prefix: str = "KC_") -> pd.DataFrame:
    u, l, m = df[f"{prefix}Upper"], df[f"{prefix}Lower"], df[f"{prefix}Middle"]
    c = df["Close"]
    ema200 = c.ewm(span=200, adjust=False, min_periods=200).mean()

    long_entry = (c.shift(1) <= u.shift(1)) & (c > u) & (c > ema200)
    short_entry = (c.shift(1) >= l.shift(1)) & (c < l) & (c < ema200)

    long_exit = (c.shift(1) >= m.shift(1)) & (c < m)
    short_exit = (c.shift(1) <= m.shift(1)) & (c > m)

    sig = pd.DataFrame(index=df.index)
    sig["long_entry"] = long_entry.fillna(False)
    sig["short_entry"] = short_entry.fillna(False)
    sig["long_exit"] = long_exit.fillna(False)
    sig["short_exit"] = short_exit.fillna(False)
    return sig
