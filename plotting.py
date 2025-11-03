from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd

def plot_price_kc(df: pd.DataFrame, ticker: str, out_png: str | None = None, trades: pd.DataFrame | None = None):
    plt.figure(figsize=(12,5))
    plt.plot(df.index, df["Close"], label="Close")
    plt.plot(df.index, df["KC_Middle"], label="KC Middle")
    plt.plot(df.index, df["KC_Upper"], label="KC Upper")
    plt.plot(df.index, df["KC_Lower"], label="KC Lower")

    if trades is not None and not trades.empty:
        longs = trades[trades["side"] == "long"]
        shorts = trades[trades["side"] == "short"]
        plt.scatter(longs["entry_time"], longs["entry_px"], marker="^", s=60, label="Long Entry")
        plt.scatter(longs["exit_time"], longs["exit_px"], marker="v", s=60, label="Long Exit")
        plt.scatter(shorts["entry_time"], shorts["entry_px"], marker="v", s=60, label="Short Entry")
        plt.scatter(shorts["exit_time"], shorts["exit_px"], marker="^", s=60, label="Short Exit")

    plt.title(f"{ticker} Keltner Channel")
    plt.xlabel("Date"); plt.ylabel("Price"); plt.legend(); plt.tight_layout()
    if out_png:
        plt.savefig(out_png, dpi=150)
        plt.close()
    else:
        plt.show()

def plot_equity(curve: pd.Series, ticker: str, out_png: str | None = None):
    plt.figure(figsize=(10,4))
    plt.plot(curve.index, curve.values, label="Equity")
    plt.title(f"Equity Curve, {ticker}")
    plt.xlabel("Date"); plt.ylabel("Equity"); plt.legend(); plt.tight_layout()
    if out_png:
        plt.savefig(out_png, dpi=150)
        plt.close()
    else:
        plt.show()

def plot_drawdown(curve: pd.Series, ticker: str, out_png: str | None = None):
    dd = curve / curve.cummax() - 1.0
    plt.figure(figsize=(10,3))
    plt.fill_between(dd.index, dd.values, 0, step="pre")
    plt.title(f"Drawdown, {ticker}")
    plt.tight_layout()
    if out_png:
        plt.savefig(out_png, dpi=150)
        plt.close()
    else:
        plt.show()
