from __future__ import annotations
import pandas as pd

__all__ = ["breakout_signals", "mean_reversion_signals", "percentb_signals", "pullback_signals", "regime_switch_signals", "keltner_signals"]

def breakout_signals(df: pd.DataFrame, prefix: str = "KC_", trend_ema_len: int = 200) -> pd.DataFrame:
    u, l, m = df[f"{prefix}Upper"], df[f"{prefix}Lower"], df[f"{prefix}Middle"]
    c = df["Close"]
    ema_trend = c.ewm(span=trend_ema_len, adjust=False, min_periods=trend_ema_len).mean()

    long_entry = (c.shift(1) <= u.shift(1)) & (c > u) & (c > ema_trend)
    short_entry = (c.shift(1) >= l.shift(1)) & (c < l) & (c < ema_trend)

    long_exit = (c.shift(1) >= m.shift(1)) & (c < m)
    short_exit = (c.shift(1) <= m.shift(1)) & (c > m)

    sig = pd.DataFrame(index=df.index)
    sig["long_entry"] = long_entry.fillna(False)
    sig["short_entry"] = short_entry.fillna(False)
    sig["long_exit"] = long_exit.fillna(False)
    sig["short_exit"] = short_exit.fillna(False)
    return sig

# Strategy: Momentum breakout — enter long/short when price breaks the Keltner bands in the direction of the 200 EMA trend; exit on a return through the midline.



def mean_reversion_signals(df: pd.DataFrame, prefix: str = "KC_") -> pd.DataFrame:
    u, l, m = df[f"{prefix}Upper"], df[f"{prefix}Lower"], df[f"{prefix}Middle"]
    c = df["Close"]

    long_entry = (c.shift(1) > l.shift(1)) & (c < l)
    short_entry = (c.shift(1) < u.shift(1)) & (c > u)

    long_exit = (c.shift(1) < m.shift(1)) & (c > m)
    short_exit = (c.shift(1) > m.shift(1)) & (c < m)

    sig = pd.DataFrame(index=df.index)
    sig["long_entry"] = long_entry.fillna(False)
    sig["short_entry"] = short_entry.fillna(False)
    sig["long_exit"] = long_exit.fillna(False)
    sig["short_exit"] = short_exit.fillna(False)
    return sig

# Strategy: Mean reversion fade — fade moves that breach the bands by taking positions expecting a reversion to the midline.



def percentb_signals(df: pd.DataFrame, low: float = 0.2, high: float = 0.8) -> pd.DataFrame:
    p = df["KC_PercentB"].clip(0, 1)
    long_entry = (p.shift(1) < low) & (p >= low)
    short_entry = (p.shift(1) > high) & (p <= high)
    long_exit = (p.shift(1) <= 0.5) & (p > 0.5)
    short_exit = (p.shift(1) >= 0.5) & (p < 0.5)

    sig = pd.DataFrame(index=df.index)
    sig["long_entry"] = long_entry.fillna(False)
    sig["short_entry"] = short_entry.fillna(False)
    sig["long_exit"] = long_exit.fillna(False)
    sig["short_exit"] = short_exit.fillna(False)
    return sig

# Strategy: PercentB crossover — use PercentB threshold crossovers to trigger entries; exit on crossing the center (0.5).



def pullback_signals(df: pd.DataFrame, slope_len: int = 20, prefix: str = "KC_") -> pd.DataFrame:
    u, l, m = df[f"{prefix}Upper"], df[f"{prefix}Lower"], df[f"{prefix}Middle"]
    c = df["Close"]
    slope = m - m.shift(slope_len)

    # uptrend pullback: cross back above midline while slope up
    long_entry = (slope > 0) & (c.shift(1) <= m.shift(1)) & (c > m)
    # downtrend pullback: cross back below midline while slope down
    short_entry = (slope < 0) & (c.shift(1) >= m.shift(1)) & (c < m)

    # exits: band touch or failure of midline
    long_exit = (c >= u) | ((c.shift(1) >= m.shift(1)) & (c < m))
    short_exit = (c <= l) | ((c.shift(1) <= m.shift(1)) & (c > m))

    sig = pd.DataFrame(index=df.index)
    sig["long_entry"] = long_entry.fillna(False)
    sig["short_entry"] = short_entry.fillna(False)
    sig["long_exit"] = long_exit.fillna(False)
    sig["short_exit"] = short_exit.fillna(False)
    return sig

# Strategy: Trend pullback — enter with the prevailing slope when price pulls back to and crosses the midline; exit on band touch or midline failure.



def regime_switch_signals(
    df: pd.DataFrame,
    slope_len: int = 20,
    strong_mult: float = 1.0,
    prefix: str = "KC_",
    trend_ema_len: int = 200
) -> pd.DataFrame:
    m = df[f"{prefix}Middle"]
    diff = m.diff(slope_len)
    ref = m.rolling(100, min_periods=50).std()
    strong = (diff.abs() > strong_mult * ref).fillna(False)

    sig_trend = breakout_signals(df, prefix=prefix, trend_ema_len=trend_ema_len)
    sig_revert = mean_reversion_signals(df, prefix=prefix)

    out = pd.DataFrame(index=df.index)
    for k in ["long_entry", "short_entry", "long_exit", "short_exit"]:
        out[k] = sig_trend[k].where(strong, sig_revert[k]).fillna(False)
    return out

# Strategy: Regime switch adaptive — use breakout signals when the midline slope is strong, otherwise use mean-reversion signals.



def keltner_signals(
    df: pd.DataFrame,
    mode: str = "momentum",
    prefix: str = "KC_",
    **kwargs
) -> pd.DataFrame:
    m = (mode or "momentum").strip().lower()
    if m in ("momentum", "breakout", "trend"):
        return breakout_signals(df, prefix=prefix, trend_ema_len=kwargs.get("trend_ema_len", 200))
    if m in ("mean_reversion", "reversion", "fade"):
        return mean_reversion_signals(df, prefix=prefix)
    if m in ("percentb", "percent_b", "pb"):
        return percentb_signals(df, **kwargs)
    if m in ("pullback", "trend_pullback", "mid_pullback"):
        return pullback_signals(df, **kwargs)
    if m in ("regime_switch", "switch", "adaptive"):
        return regime_switch_signals(df, prefix=prefix, **kwargs)
    raise ValueError(f"Unknown strategy mode: {mode}")

# Dispatcher: select a Keltner-based strategy by mode and forward parameters to the chosen signal generator.