from __future__ import annotations
import os
import io
import json
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages

from data import fetch_ohlc
from indicators import keltner_channel
from strategy import breakout_signals
from backtester import run_backtest, BTParams

# ---------- helpers ----------
def make_dirs(root: str, ticker: str) -> tuple[str, str]:
    os.makedirs(root, exist_ok=True)
    run_dir = os.path.join(root, ticker)
    os.makedirs(run_dir, exist_ok=True)
    base = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return run_dir, base

def dd_series(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0

def figure_price(kc: pd.DataFrame, trades: pd.DataFrame, ticker: str) -> Figure:
    fig = Figure(figsize=(8,3))
    ax = fig.add_subplot(111)
    ax.plot(kc.index, kc["Close"], label="Close")
    ax.plot(kc.index, kc["KC_Middle"], label="KC Middle")
    ax.plot(kc.index, kc["KC_Upper"], label="KC Upper")
    ax.plot(kc.index, kc["KC_Lower"], label="KC Lower")
    if not trades.empty:
        longs = trades[trades["side"]=="long"]
        shorts = trades[trades["side"]=="short"]
        ax.scatter(longs["entry_time"], longs["entry_px"], marker="^", s=20, label="Long Entry")
        ax.scatter(longs["exit_time"], longs["exit_px"], marker="v", s=20, label="Long Exit")
        ax.scatter(shorts["entry_time"], shorts["entry_px"], marker="v", s=20, label="Short Entry")
        ax.scatter(shorts["exit_time"], shorts["exit_px"], marker="^", s=20, label="Short Exit")
    ax.set_title(f"{ticker} Keltner Channel")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig

def figure_equity(equity: pd.Series, ticker: str) -> Figure:
    fig = Figure(figsize=(8,3))
    ax = fig.add_subplot(111)
    ax.plot(equity.index, equity.values, label="Equity")
    ax.set_title(f"Equity Curve, {ticker}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig

def figure_drawdown(equity: pd.Series, ticker: str) -> Figure:
    dd = dd_series(equity)
    fig = Figure(figsize=(8,3))
    ax = fig.add_subplot(111)
    ax.fill_between(dd.index, dd.values, 0, step="pre")
    ax.set_title(f"Drawdown, {ticker}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig

def build_pdf(params: dict, metrics: dict, fig_price: Figure, fig_equity: Figure, fig_dd: Figure) -> bytes:
    buf = io.BytesIO()
    # first page text summary + then figures
    with PdfPages(buf) as pp:
        page = Figure(figsize=(8.27, 11.69))  # A4
        ax = page.add_subplot(111)
        ax.axis("off")

        def fmt_block(title, d):
            lines = [title]
            for k, v in d.items():
                lines.append(f"{k}: {v}")
            return "\n".join(lines)

        txt = f"Run: {params.get('base','')}\nTimestamp: {params['timestamp']}\n\n"
        txt += fmt_block("Parameters", params) + "\n\n"
        txt += fmt_block("Metrics", metrics)

        page.text(0.05, 0.95, "Keltner Channel Backtest Report", fontsize=16, va="top", ha="left", weight="bold")
        page.text(0.05, 0.90, txt, fontsize=9, va="top", ha="left", family="monospace")
        pp.savefig(page, bbox_inches="tight")
        pp.savefig(fig_price, bbox_inches="tight")
        pp.savefig(fig_equity, bbox_inches="tight")
        pp.savefig(fig_dd, bbox_inches="tight")
    buf.seek(0)
    return buf.read()

# ---------- UI ----------
st.set_page_config(page_title="Keltner Channel Backtester", layout="wide")
st.title("Keltner Channel Backtester")

with st.sidebar:
    st.header("Inputs")
    ticker = st.text_input("Ticker", "AAPL").strip().upper()
    period = st.selectbox("Period", ["", "1mo","3mo","6mo","1y","2y","5y","10y","max"], index=6)
    col_start, col_end = st.columns(2)
    with col_start:
        start = st.text_input("Start YYYY-MM-DD", "")
    with col_end:
        end = st.text_input("End YYYY-MM-DD", "")

    side = st.selectbox("Side", ["long_only","short_only","long_short"], index=2)
    execution = st.selectbox("Execution", ["next_open","next_close"], index=0)

    ema_len = st.number_input("EMA", min_value=5, max_value=200, value=20, step=1)
    atr_len = st.number_input("ATR", min_value=5, max_value=100, value=10, step=1)
    mult = st.number_input("Multiplier", min_value=1.0, max_value=5.0, value=2.0, step=0.1, format="%.1f")
    risk = st.number_input("Risk per trade", min_value=0.001, max_value=0.100, value=0.010, step=0.001, format="%.3f")
    stop_mult = st.number_input("Stop x ATR", min_value=0.5, max_value=10.0, value=2.0, step=0.1, format="%.1f")
    tp_enable = st.checkbox("Enable Take Profit x ATR", value=False)
    tp_mult = st.number_input("Take Profit x ATR", min_value=0.5, max_value=10.0, value=4.0, step=0.1, format="%.1f", disabled=not tp_enable)

    fee_bps = st.number_input("Fee bps", min_value=0.0, max_value=50.0, value=1.0, step=0.1)
    slip_bps = st.number_input("Slip bps", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
    warm_override = st.number_input("Warmup override bars, 0 = auto", min_value=0, max_value=500, value=0, step=1)

    root_outdir = st.text_input("Save root folder", "runs")
    run_btn = st.button("Run Backtest", use_container_width=True)

# conflict guard
if period and (start or end):
    st.info("Period is set, start and end will be ignored.")

# ---------- run ----------
if run_btn:
    if not ticker:
        st.error("Ticker is required")
        st.stop()

    # paths
    run_dir, base = make_dirs(root_outdir, ticker)

    # data
    try:
        df = fetch_ohlc(ticker, start=None if period else (start or None),
                        end=None if period else (end or None),
                        period=period or None)
    except Exception as e:
        st.error(f"Failed to fetch data for {ticker}\n{e}")
        st.stop()

    # indicators, signals, backtest
    kc = keltner_channel(df, ema_len=int(ema_len), atr_len=int(atr_len), mult=float(mult))
    sig = breakout_signals(kc)

    warmup = int(warm_override) if warm_override > 0 else max(int(ema_len), int(atr_len))
    bt = BTParams(
        execution=execution,
        initial_capital=100000.0,
        side=side,
        fee_bps=float(fee_bps),
        slip_bps=float(slip_bps),
        risk_per_trade=float(risk),
        atr_stop_mult=float(stop_mult),
        take_profit_mult=float(tp_mult) if tp_enable else None,
        warmup_bars=warmup,
        max_leverage=1.0,
    )
    res = run_backtest(kc, sig, bt)

    # outputs
    kc_out = kc.copy()
    kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
    trades = res["trades"]
    equity = res["equity"]
    metrics = res["metrics"]

    # save files
    kc_csv = os.path.join(run_dir, f"{base}_kc.csv")
    trades_csv = os.path.join(run_dir, f"{base}_trades.csv")
    kc_out.to_csv(kc_csv)
    trades.to_csv(trades_csv, index=False)

    params = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "base": base,
        "ticker": ticker,
        "period": period or "",
        "start": start or "",
        "end": end or "",
        "side": side,
        "execution": execution,
        "ema_len": int(ema_len),
        "atr_len": int(atr_len),
        "multiplier": float(mult),
        "risk_per_trade": float(risk),
        "atr_stop_mult": float(stop_mult),
        "take_profit_mult_enabled": tp_enable,
        "take_profit_mult": float(tp_mult) if tp_enable else None,
        "fee_bps": float(fee_bps),
        "slip_bps": float(slip_bps),
        "warmup_override": int(warm_override),
    }
    with open(os.path.join(run_dir, f"{base}_params.json"), "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
    metrics_clean = {k: float(v) if hasattr(v, "__float__") else v for k, v in metrics.items()}
    with open(os.path.join(run_dir, f"{base}_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_clean, f, indent=2)
    pd.DataFrame([metrics_clean]).to_csv(os.path.join(run_dir, f"{base}_metrics.csv"), index=False)

    registry_csv = os.path.join(root_outdir, "runs_log.csv")
    row = {**{"base": base}, **params, **metrics_clean}
    df_row = pd.DataFrame([row])
    if os.path.exists(registry_csv):
        try:
            old = pd.read_csv(registry_csv)
            pd.concat([old, df_row], ignore_index=True).to_csv(registry_csv, index=False)
        except Exception:
            df_row.to_csv(registry_csv, index=False)
    else:
        df_row.to_csv(registry_csv, index=False)

    # figures
    f_price = figure_price(kc, trades, ticker)
    f_equity = figure_equity(equity, ticker)
    f_dd = figure_drawdown(equity, ticker)

    # save PNGs
    f_price.savefig(os.path.join(run_dir, f"{base}_kc.png"), dpi=150, bbox_inches="tight")
    f_equity.savefig(os.path.join(run_dir, f"{base}_equity.png"), dpi=150, bbox_inches="tight")
    f_dd.savefig(os.path.join(run_dir, f"{base}_drawdown.png"), dpi=150, bbox_inches="tight")

    # show metrics
    st.subheader("Metrics")
    m1 = f"CAGR {metrics['CAGR']:.2%}  |  Sharpe {metrics['Sharpe']:.2f}  |  Sortino {metrics['Sortino']:.2f}"
    m2 = f"MaxDD {metrics['MaxDrawdown']:.2%}  |  Exposure {metrics['Exposure']:.2%}  |  Trades {metrics['NumTrades']}"
    st.write(m1)
    st.write(m2)
    st.caption(f"Saved to {run_dir}")

    # show plots
    c1, c2 = st.columns(2)
    with c1:
        st.pyplot(f_price)
        st.pyplot(f_equity)
    with c2:
        st.pyplot(f_dd)

    # downloads
    with open(kc_csv, "rb") as f:
        st.download_button("Download KC CSV", f, file_name=os.path.basename(kc_csv), mime="text/csv")
    with open(trades_csv, "rb") as f:
        st.download_button("Download Trades CSV", f, file_name=os.path.basename(trades_csv), mime="text/csv")

    pdf_bytes = build_pdf(params, metrics_clean, f_price, f_equity, f_dd)
    st.download_button("Download PDF report", data=pdf_bytes, file_name=f"{base}_report.pdf", mime="application/pdf")
