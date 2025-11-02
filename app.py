from __future__ import annotations
import os, io, json, shutil, tempfile
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
import plotly.express as px

from data import fetch_ohlc
from indicators import keltner_channel
from strategy import breakout_signals
from backtester import run_backtest, BTParams

# ---------------- base setup ----------------
st.set_page_config(page_title="Keltner Backtester", layout="wide")

def make_dirs(root: str, ticker: str):
    os.makedirs(root, exist_ok=True)
    run_dir = os.path.join(root, ticker)
    os.makedirs(run_dir, exist_ok=True)
    base = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return run_dir, base

def dd_series(equity: pd.Series):
    return equity / equity.cummax() - 1.0

def mpl_price(kc: pd.DataFrame, trades: pd.DataFrame, ticker: str) -> Figure:
    fig = Figure(figsize=(8,3)); ax = fig.add_subplot(111)
    ax.plot(kc.index, kc["Close"], label="Close")
    ax.plot(kc.index, kc["KC_Middle"], label="KC Mid")
    ax.plot(kc.index, kc["KC_Upper"], label="KC Upper")
    ax.plot(kc.index, kc["KC_Lower"], label="KC Lower")
    if not trades.empty:
        L = trades[trades["side"]=="long"]; S = trades[trades["side"]=="short"]
        ax.scatter(L["entry_time"], L["entry_px"], marker="^", s=20, label="Long In")
        ax.scatter(L["exit_time"], L["exit_px"], marker="v", s=20, label="Long Out")
        ax.scatter(S["entry_time"], S["entry_px"], marker="v", s=20, label="Short In")
        ax.scatter(S["exit_time"], S["exit_px"], marker="^", s=20, label="Short Out")
    ax.legend(loc="best", fontsize=8); ax.grid(True, alpha=0.3); fig.tight_layout()
    return fig

def mpl_equity(eq: pd.Series, ticker: str) -> Figure:
    fig = Figure(figsize=(8,3)); ax = fig.add_subplot(111)
    ax.plot(eq.index, eq.values, label="Equity"); ax.legend(loc="best", fontsize=8)
    ax.set_title(f"Equity Curve, {ticker}"); ax.grid(True, alpha=0.3); fig.tight_layout()
    return fig

def mpl_drawdown(eq: pd.Series, ticker: str) -> Figure:
    dd = dd_series(eq); fig = Figure(figsize=(8,3)); ax = fig.add_subplot(111)
    ax.fill_between(dd.index, dd.values, 0, step="pre"); ax.set_title(f"Drawdown, {ticker}")
    ax.grid(True, alpha=0.3); fig.tight_layout(); return fig

def plotly_price_ohlc(kc: pd.DataFrame, trades: pd.DataFrame, ticker: str) -> go.Figure:
    df = kc.reset_index().rename(columns={"index":"Date"})
    fig = go.Figure([go.Candlestick(x=df["Date"], open=df["Open"], high=df["High"],
                                    low=df["Low"], close=df["Close"], name="OHLC")])
    fig.add_trace(go.Scatter(x=df["Date"], y=df["KC_Middle"], name="KC Mid"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["KC_Upper"], name="KC Upper"))
    fig.add_trace(go.Scatter(x=df["Date"], y=df["KC_Lower"], name="KC Lower"))
    if not trades.empty:
        L = trades[trades["side"]=="long"]; S = trades[trades["side"]=="short"]
        fig.add_trace(go.Scatter(x=L["entry_time"], y=L["entry_px"], mode="markers", name="Long In",
                                 marker_symbol="triangle-up", marker_size=8))
        fig.add_trace(go.Scatter(x=L["exit_time"], y=L["exit_px"], mode="markers", name="Long Out",
                                 marker_symbol="triangle-down", marker_size=8))
        fig.add_trace(go.Scatter(x=S["entry_time"], y=S["entry_px"], mode="markers", name="Short In",
                                 marker_symbol="triangle-down", marker_size=8))
        fig.add_trace(go.Scatter(x=S["exit_time"], y=S["exit_px"], mode="markers", name="Short Out",
                                 marker_symbol="triangle-up", marker_size=8))
    fig.update_layout(title=f"{ticker} Keltner Channel", xaxis_rangeslider_visible=False, height=420)
    return fig

def plotly_equity(eq: pd.Series, ticker: str) -> go.Figure:
    df = eq.reset_index(); df.columns = ["Date","Equity"]
    fig = px.line(df, x="Date", y="Equity", title=f"Equity Curve, {ticker}")
    fig.update_layout(height=320); return fig

def plotly_dd(eq: pd.Series) -> go.Figure:
    dd = dd_series(eq).reset_index(); dd.columns = ["Date","Drawdown"]
    fig = go.Figure(); fig.add_trace(go.Scatter(x=dd["Date"], y=dd["Drawdown"], fill="tozeroy", name="Drawdown"))
    fig.update_layout(title="Drawdown", height=320); return fig

def build_pdf(params: dict, metrics: dict, fig_price: Figure, fig_equity: Figure, fig_dd: Figure,
              include_text=True, include_price=True, include_equity=True, include_dd=True) -> bytes:
    buf = io.BytesIO()
    with PdfPages(buf) as pp:
        if include_text:
            page = Figure(figsize=(8.27, 11.69)); ax = page.add_subplot(111); ax.axis("off")
            def fmt_block(title, d):
                lines = [title] + [f"{k}: {v}" for k,v in d.items()]
                return "\n".join(lines)
            txt = f"Run: {params.get('base','')}\nTimestamp: {params['timestamp']}\n\n"
            txt += fmt_block("Parameters", params) + "\n\n" + fmt_block("Metrics", metrics)
            page.text(0.05, 0.95, "Keltner Channel Backtest Report", fontsize=16, va="top")
            page.text(0.05, 0.90, txt, fontsize=9, va="top", ha="left", family="monospace")
            pp.savefig(page, bbox_inches="tight")
        if include_price:  pp.savefig(fig_price,  bbox_inches="tight")
        if include_equity: pp.savefig(fig_equity, bbox_inches="tight")
        if include_dd:     pp.savefig(fig_dd,     bbox_inches="tight")
    buf.seek(0); return buf.read()

@st.cache_data
def read_runs_log(root_outdir: str) -> pd.DataFrame:
    path = os.path.join(root_outdir, "runs_log.csv")
    if not os.path.exists(path): return pd.DataFrame()
    df = pd.read_csv(path)
    for col in ["timestamp","Timestamp"]:
        if col in df.columns:
            with pd.option_context("mode.chained_assignment", None):
                df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

# ---- LOCAL WINDOWS FOLDER PICKER (works only when running locally) ----
def browse_for_folder_local() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        path = filedialog.askdirectory(title="Select output root folder")
        root.destroy()
        return path if path else None
    except Exception:
        return None

# ---------------- sidebar ----------------
with st.sidebar:
    st.header("Inputs")
    ticker = st.text_input("Ticker", "AAPL").strip().upper()
    period = st.selectbox("Period", ["", "1mo","3mo","6mo","1y","2y","5y","10y","max"], index=6)
    c1, c2 = st.columns(2)
    with c1: start = st.text_input("Start YYYY-MM-DD", "")
    with c2: end   = st.text_input("End YYYY-MM-DD", "")

    side = st.selectbox("Side", ["long_only","short_only","long_short"], index=2)
    execution = st.selectbox("Execution", ["next_open","next_close"], index=0)

    st.markdown("**Parameters**")
    def dual(label, lo, hi, default, step, fmt):
        c3, c4 = st.columns([3,1])
        with c3: v = st.slider(label, lo, hi, default, step)
        with c4: v = st.number_input(label+" ", lo, hi, v, step=step, format=fmt)
        return v
    ema_len   = dual("EMA", 5, 200, 20, 1, "%d")
    atr_len   = dual("ATR", 5, 100, 10, 1, "%d")
    mult      = dual("Multiplier", 1.0, 5.0, 2.0, 0.1, "%.1f")
    risk      = dual("Risk per trade", 0.001, 0.100, 0.010, 0.001, "%.3f")
    stop_mult = dual("Stop x ATR", 0.5, 10.0, 2.0, 0.1, "%.1f")
    tp_enable = st.checkbox("Enable Take Profit x ATR", value=False)
    tp_mult   = dual("Take Profit x ATR", 0.5, 10.0, 4.0, 0.1, "%.1f") if tp_enable else None

    st.markdown("**Save location**")
    if "root_outdir" not in st.session_state:
        st.session_state.root_outdir = "runs"
    st.text_input("Save root folder", key="root_outdir")

    col_b = st.columns(2)
    with col_b[0]:
        if st.button("Browse… (local only)"):
            chosen = browse_for_folder_local()
            if chosen:
                st.session_state.root_outdir = chosen
    with col_b[1]:
        st.caption("Opens Windows folder picker when running locally. Remote deploys cannot open Explorer.")

    st.markdown("**Costs & Run**")
    fee_bps = st.number_input("Fee bps", 0.0, 50.0, 1.0, 0.1)
    slip_bps = st.number_input("Slip bps", 0.0, 100.0, 2.0, 0.1)
    warm_override = st.number_input("Warmup override bars", 0, 500, 0, 1)

    run_btn = st.button("Run Backtest", use_container_width=True)

# ---------------- warnings ----------------
if period and (start or end):
    st.info("Period selected, start and end will be ignored.")

state = st.session_state
if "last" not in state: state["last"] = None

# ---------------- run backtest ----------------
if run_btn:
    root_outdir = st.session_state.root_outdir.strip() or "runs"
    if not ticker:
        st.error("Ticker required"); st.stop()

    run_dir, base = make_dirs(root_outdir, ticker)
    try:
        df = fetch_ohlc(ticker, start=None if period else (start or None),
                        end=None if period else (end or None),
                        period=period or None)
    except Exception as e:
        st.error(f"Data fetch failed: {e}"); st.stop()

    kc = keltner_channel(df, ema_len=int(ema_len), atr_len=int(atr_len), mult=float(mult))
    sig = breakout_signals(kc)
    warmup = int(warm_override) if warm_override > 0 else max(int(ema_len), int(atr_len))
    bt = BTParams(
        execution=execution, initial_capital=100000.0, side=side,
        fee_bps=float(fee_bps), slip_bps=float(slip_bps), risk_per_trade=float(risk),
        atr_stop_mult=float(stop_mult), take_profit_mult=float(tp_mult) if tp_enable else None,
        warmup_bars=warmup, max_leverage=1.0,
    )
    res = run_backtest(kc, sig, bt)
    trades = res["trades"]; equity = res["equity"]; metrics = res["metrics"]

    kc_out = kc.copy(); kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
    kc_csv = os.path.join(run_dir, f"{base}_kc.csv")
    trades_csv = os.path.join(run_dir, f"{base}_trades.csv")
    kc_out.to_csv(kc_csv); trades.to_csv(trades_csv, index=False)

    params = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "base": base, "ticker": ticker, "period": period or "", "start": start or "", "end": end or "",
        "side": side, "execution": execution, "ema_len": int(ema_len), "atr_len": int(atr_len),
        "multiplier": float(mult), "risk_per_trade": float(risk), "atr_stop_mult": float(stop_mult),
        "take_profit_mult_enabled": tp_enable, "take_profit_mult": float(tp_mult) if tp_enable else None,
        "fee_bps": float(fee_bps), "slip_bps": float(slip_bps), "warmup_override": int(warm_override),
    }
    with open(os.path.join(run_dir, f"{base}_params.json"), "w", encoding="utf-8") as f: json.dump(params, f, indent=2)
    metrics_clean = {k: float(v) if hasattr(v, "__float__") else v for k, v in metrics.items()}
    with open(os.path.join(run_dir, f"{base}_metrics.json"), "w", encoding="utf-8") as f: json.dump(metrics_clean, f, indent=2)
    pd.DataFrame([metrics_clean]).to_csv(os.path.join(run_dir, f"{base}_metrics.csv"), index=False)

    registry_csv = os.path.join(root_outdir, "runs_log.csv")
    row = {**{"base": base}, **params, **metrics_clean}
    df_row = pd.DataFrame([row])
    if os.path.exists(registry_csv):
        try: pd.concat([pd.read_csv(registry_csv), df_row], ignore_index=True).to_csv(registry_csv, index=False)
        except Exception: df_row.to_csv(registry_csv, index=False)
    else: df_row.to_csv(registry_csv, index=False)

    f_price = mpl_price(kc, trades, ticker); f_eq = mpl_equity(equity, ticker); f_dd = mpl_drawdown(equity, ticker)
    state["last"] = {"run_dir": run_dir, "base": base, "kc": kc, "trades": trades, "equity": equity,
                     "params": params, "metrics": metrics_clean, "mpl": {"price": f_price, "equity": f_eq, "dd": f_dd}}
    st.success(f"Saved in: {run_dir}")

# ---------------- tabs ----------------
tabs = st.tabs(["Backtest", "Trades Explorer", "Run History", "Report Builder"])

with tabs[0]:
    if state["last"] is None:
        st.info("Run a backtest to see results.")
    else:
        last = state["last"]; kc = last["kc"]; trades = last["trades"]; equity = last["equity"]
        metrics = last["metrics"]; ticker = last["params"]["ticker"]
        st.subheader("Metrics")
        st.write(f"CAGR {metrics['CAGR']:.2%} | Sharpe {metrics['Sharpe']:.2f} | Sortino {metrics['Sortino']:.2f}")
        st.write(f"MaxDD {metrics['MaxDrawdown']:.2%} | Exposure {metrics['Exposure']:.2%} | Trades {metrics['NumTrades']}")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(plotly_price_ohlc(kc, trades, ticker), use_container_width=True)
            st.plotly_chart(plotly_equity(equity, ticker), use_container_width=True)
        with c2:
            st.plotly_chart(plotly_dd(equity), use_container_width=True)

        # downloads
        run_dir = last["run_dir"]; base = last["base"]
        kc_csv = os.path.join(run_dir, f"{base}_kc.csv")
        trades_csv = os.path.join(run_dir, f"{base}_trades.csv")
        with open(kc_csv, "rb") as f: st.download_button("Download KC CSV", f, file_name=os.path.basename(kc_csv), mime="text/csv")
        with open(trades_csv, "rb") as f: st.download_button("Download Trades CSV", f, file_name=os.path.basename(trades_csv), mime="text/csv")

        # zip the whole run folder for quick sharing
        if st.button("Prepare ZIP of this run"):
            tmp_zip = os.path.join(tempfile.gettempdir(), f"{base}.zip")
            if os.path.exists(tmp_zip): os.remove(tmp_zip)
            shutil.make_archive(tmp_zip[:-4], "zip", run_dir, base_dir=run_dir)
            with open(tmp_zip, "rb") as fzip:
                st.download_button("Download Run ZIP", fzip, file_name=f"{base}.zip", mime="application/zip")

with tabs[1]:
    if state["last"] is None:
        st.info("Run a backtest first.")
    else:
        tdf = state["last"]["trades"].copy()
        if tdf.empty:
            st.warning("No trades generated.")
        else:
            st.subheader("Filters")
            colf = st.columns(4)
            with colf[0]: side_f = st.multiselect("Side", ["long","short"], default=["long","short"])
            with colf[1]: min_rr = st.number_input("Min R multiple", value=-5.0, step=0.5)
            with colf[2]: min_p = st.number_input("Min PnL", value=float(tdf["pnl"].min() if "pnl" in tdf.columns else 0.0), step=10.0)
            with colf[3]: max_p = st.number_input("Max PnL", value=float(tdf["pnl"].max() if "pnl" in tdf.columns else 0.0), step=10.0)
            if "side" in tdf.columns: tdf = tdf[tdf["side"].isin(side_f)]
            if "R" in tdf.columns:    tdf = tdf[tdf["R"] >= min_rr]
            if "pnl" in tdf.columns:  tdf = tdf[(tdf["pnl"] >= min_p) & (tdf["pnl"] <= max_p)]
            st.dataframe(tdf, use_container_width=True, height=360)
            if "R" in tdf.columns and len(tdf) > 0:
                st.plotly_chart(px.histogram(tdf, x="R", nbins=30, title="Distribution of R multiples"), use_container_width=True)

with tabs[2]:
    root_outdir = st.session_state.root_outdir.strip() or "runs"
    dfhist = read_runs_log(root_outdir)
    if dfhist.empty:
        st.info("No runs_log.csv yet. Run at least one backtest.")
    else:
        st.subheader("Run History")
        tickers = sorted(dfhist["ticker"].dropna().unique()) if "ticker" in dfhist.columns else []
        t_sel = st.multiselect("Ticker filter", tickers, default=tickers[:1] if tickers else [])
        dfhist_v = dfhist[dfhist["ticker"].isin(t_sel)] if t_sel and "ticker" in dfhist.columns else dfhist
        st.dataframe(dfhist_v, use_container_width=True, height=360)
        if {"Sharpe","MaxDrawdown"}.issubset(dfhist_v.columns):
            st.plotly_chart(px.scatter(dfhist_v, x="MaxDrawdown", y="Sharpe", color="ticker" if "ticker" in dfhist_v.columns else None,
                                       hover_data=["base"] if "base" in dfhist_v.columns else None,
                                       title="Sharpe vs Max Drawdown"), use_container_width=True)

with tabs[3]:
    if state["last"] is None:
        st.info("Run a backtest first.")
    else:
        last = state["last"]; params = last["params"]; metrics = last["metrics"]; figs = last["mpl"]
        st.subheader("Build Custom PDF Report")
        c = st.columns(2)
        with c[0]:
            inc_text = st.checkbox("Include summary text", value=True)
            inc_price = st.checkbox("Include price + KC chart", value=True)
            inc_eq = st.checkbox("Include equity chart", value=True)
            inc_dd = st.checkbox("Include drawdown chart", value=True)
        if st.button("Generate PDF"):
            pdf_bytes = build_pdf(params, metrics, figs["price"], figs["equity"], figs["dd"],
                                  include_text=inc_text, include_price=inc_price, include_equity=inc_eq, include_dd=inc_dd)
            st.download_button("Download PDF", data=pdf_bytes, file_name=f"{last['base']}_report.pdf", mime="application/pdf")
