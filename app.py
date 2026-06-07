from __future__ import annotations
import os, io, json
from datetime import datetime
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
import plotly.graph_objects as go
import plotly.express as px

from data import fetch_ohlc, interval_limit
from indicators import keltner_channel
from strategy import keltner_signals
from backtester import run_backtest, BTParams, run_buy_and_hold

st.set_page_config(page_title="Keltner Backtester", layout="wide")

def make_dirs(root: str, ticker: str):
    os.makedirs(root, exist_ok=True)
    run_dir = os.path.join(root, ticker)
    os.makedirs(run_dir, exist_ok=True)
    base = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    return run_dir, base

def dd_series(equity: pd.Series):
    return equity / equity.cummax() - 1.0

def safe_read_csv(path: str, parse_date_cols: tuple[str, ...] = ()) -> pd.DataFrame | None:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return None
    for c in parse_date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
    return df

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
    x = kc.index  # robust, no reset_index games
    fig = go.Figure([
        go.Candlestick(
            x=x,
            open=kc["Open"],
            high=kc["High"],
            low=kc["Low"],
            close=kc["Close"],
            name="OHLC"
        )
    ])
    fig.add_trace(go.Scatter(x=x, y=kc["KC_Middle"], name="KC Mid"))
    fig.add_trace(go.Scatter(x=x, y=kc["KC_Upper"],  name="KC Upper"))
    fig.add_trace(go.Scatter(x=x, y=kc["KC_Lower"],  name="KC Lower"))

    if trades is not None and not trades.empty:
        L = trades[trades["side"] == "long"]
        S = trades[trades["side"] == "short"]
        if not L.empty:
            fig.add_trace(go.Scatter(x=L["entry_time"], y=L["entry_px"], mode="markers",
                                     name="Long In", marker_symbol="triangle-up", marker_size=8))
            fig.add_trace(go.Scatter(x=L["exit_time"], y=L["exit_px"], mode="markers",
                                     name="Long Out", marker_symbol="triangle-down", marker_size=8))
        if not S.empty:
            fig.add_trace(go.Scatter(x=S["entry_time"], y=S["entry_px"], mode="markers",
                                     name="Short In", marker_symbol="triangle-down", marker_size=8))
            fig.add_trace(go.Scatter(x=S["exit_time"], y=S["exit_px"], mode="markers",
                                     name="Short Out", marker_symbol="triangle-up", marker_size=8))

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
def read_all_runs_logs(root_outdir: str) -> pd.DataFrame:
    if not os.path.isdir(root_outdir):
        return pd.DataFrame()
    frames = []
    for name in sorted(os.listdir(root_outdir)):
        p = os.path.join(root_outdir, name)
        f = os.path.join(p, "runs_log.csv")
        if os.path.isdir(p) and os.path.exists(f) and os.path.getsize(f) > 0:
            df = safe_read_csv(f)
            if df is not None:
                df["ticker_folder"] = name
                frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

st.markdown("""
<style>
.kc-box {border:1px solid var(--secondary-background-color);
         border-radius:0.5rem;padding:0.35rem 0.6rem;margin:0.3rem 0;}
</style>
""", unsafe_allow_html=True)

def dual(label, lo, hi, default, step, fmt, *, is_int=False):
    key = label.replace(" ", "_")
    slider_key = f"{key}_slider"
    input_key  = f"{key}_input"
    val_key    = f"{key}_val"

    def _clamp_cast(x):
        x = max(lo, min(hi, x))
        if is_int:
            x = int(round(x))
        return x

    if val_key not in st.session_state:
        st.session_state[val_key] = _clamp_cast(default)
    if slider_key not in st.session_state:
        st.session_state[slider_key] = st.session_state[val_key]
    if input_key not in st.session_state:
        st.session_state[input_key] = st.session_state[val_key]

    def _from_slider():
        v = _clamp_cast(st.session_state[slider_key])
        st.session_state[input_key] = v
        st.session_state[val_key] = v

    def _from_input():
        v = _clamp_cast(st.session_state[input_key])
        st.session_state[slider_key] = v
        st.session_state[val_key] = v

    v_now = st.session_state[val_key]
    st.slider(label, lo, hi, step=step, key=slider_key, on_change=_from_slider)
    with st.container():
        st.markdown('<div class="kc-box">', unsafe_allow_html=True)
        st.number_input(label + " ", lo, hi,
                        step=step, format=fmt, key=input_key,
                        label_visibility="collapsed", on_change=_from_input)
        st.markdown('</div>', unsafe_allow_html=True)

    return st.session_state[val_key]

with st.sidebar:
    st.header("Inputs")
    ticker = st.text_input("Ticker", "AAPL").strip().upper()

    # select interval
    interval = st.selectbox(
        "Interval",
        ["1m","2m","5m","15m","30m","1h","1d","1wk","1mo"],
        index=6
    )
    lim = interval_limit(interval)
    st.info(f"Max lookback for {interval} is {lim['period_hint']}  {lim['note']}")

    # map interval to allowed periods
    if interval in ["1m"]:
        # ~7 days data
        period_opts = ["1d","2d","3d","5d","7d"]
    elif interval in ["2m","5m","15m","30m","90m"]:
        # up to ~60 days
        period_opts = ["1d","2d","3d","5d","10d","15d","30d","45d","60d"]
    elif interval in ["1h"]:
        # up to ~730 days (~2 years)
        period_opts = ["1mo","2mo","3mo","6mo","9mo","1y","18mo","2y"]
    elif interval in ["1d"]:
        # full range daily
        period_opts = ["1mo","2mo","3mo","6mo","9mo","1y","2y","3y","5y","10y","ytd","max"]
    elif interval in ["1wk"]:
        # weekly long lookback
        period_opts = ["3mo","6mo","1y","2y","3y","5y","10y","ytd","max"]
    elif interval in ["1mo"]:
        # monthly long lookback
        period_opts = ["1y","2y","3y","5y","10y","ytd","max"]
    else:
        period_opts = ["1mo","3mo","6mo","1y","2y","5y","10y","max"]

    period = st.selectbox("Period", [""] + period_opts, index=8)

    c1, c2 = st.columns(2)
    with c1: start = st.text_input("Start YYYY-MM-DD", "")
    with c2: end   = st.text_input("End YYYY-MM-DD", "")
    if period and lim["max_days"] is not None:
        st.warning(f"{interval} returns only about {lim['period_hint']} of data, reduce Period or use Start/End if empty result.")

    side = st.selectbox("Side", ["long_only","short_only","long_short"], index=2)
    execution = st.selectbox("Execution", ["next_open","next_close"], index=0)
    strategy_mode = st.selectbox(
        "Strategy",
        ["momentum","mean_reversion","percentb","pullback","regime_switch"],
        index=0
    )

    st.markdown("Parameters")
    ema_len   = dual("EMA", 5, 200, 20, 1, "%d", is_int=True)
    atr_len   = dual("ATR", 5, 100, 10, 1, "%d", is_int=True)
    mult      = dual("Multiplier", 1.0, 5.0, 2.0, 0.1, "%.1f")
    trend_ema = dual("Trend EMA", 20, 500, 200, 10, "%d", is_int=True)

    pb_low = pb_high = None
    slope_len = strong_mult = None
    if strategy_mode == "percentb":
        pb_low  = dual("PercentB low", 0.00, 0.50, 0.20, 0.01, "%.2f")
        pb_high = dual("PercentB high", 0.50, 1.00, 0.80, 0.01, "%.2f")
    if strategy_mode in ("pullback","regime_switch"):
        slope_len   = dual("Slope len", 2, 100, 20, 1, "%d", is_int=True)
    if strategy_mode == "regime_switch":
        strong_mult = dual("Strength x STD", 0.2, 3.0, 1.0, 0.1, "%.1f")

    risk      = dual("Risk per trade", 0.001, 0.100, 0.010, 0.001, "%.3f")
    stop_mult = dual("Stop x ATR", 0.5, 10.0, 2.0, 0.1, "%.1f")
    tp_enable = st.checkbox("Enable Take Profit x ATR", value=False)
    tp_mult   = dual("Take Profit x ATR", 0.5, 10.0, 4.0, 0.1, "%.1f") if tp_enable else None
    ts_enable = st.checkbox("Enable Trailing Stop", value=False)
    ts_atr_mult = dual("Trailing Stop x ATR", 0.5, 10.0, 2.5, 0.1, "%.1f") if ts_enable else 2.5
    bh_enable = st.checkbox("Show Buy & Hold benchmark", value=False)

    st.markdown("Save location")
    root_outdir = st.text_input("Save root folder", "runs", key="root_outdir")

    st.markdown("Costs and Run")
    capital = st.number_input("Capital ($)", 1000.0, 10000000.0, 100000.0, step=1000.0, format="%.0f")
    max_lev = st.slider("Max Leverage", 1.0, 5.0, 1.0, step=0.25)
    fee_bps = st.number_input("Fee bps", 0.0, 50.0, 1.0, 0.1)
    slip_bps = st.number_input("Slip bps", 0.0, 100.0, 2.0, 0.1)
    warm_override = st.number_input("Warmup override bars", 0, 500, 0, 1)

    run_btn = st.button("Run Backtest", width='stretch')

if period and (start or end):
    st.info("Period selected, start and end will be ignored.")

state = st.session_state
if "last" not in state: state["last"] = None

if run_btn:
    run_dir, base = make_dirs(root_outdir.strip() or "runs", ticker)
    try:
        df = fetch_ohlc(ticker, start=None if period else (start or None),
                        end=None if period else (end or None),
                        period=period or None,
                        interval=interval)
    except Exception as e:
        st.error(f"Data fetch failed: {e}"); st.stop()

    kc = keltner_channel(df, ema_len=int(ema_len), atr_len=int(atr_len), mult=float(mult))

    sig_kwargs = {}
    if strategy_mode == "percentb":
        sig_kwargs = {"low": float(pb_low), "high": float(pb_high)}
    if strategy_mode == "pullback":
        sig_kwargs = {"slope_len": int(slope_len)}
    if strategy_mode == "regime_switch":
        sig_kwargs = {"slope_len": int(slope_len), "strong_mult": float(strong_mult), "trend_ema_len": int(trend_ema)}
    if strategy_mode in ("momentum", "breakout", "trend"):
        sig_kwargs = {"trend_ema_len": int(trend_ema)}

    sig = keltner_signals(kc, mode=strategy_mode, **sig_kwargs)

    warmup = int(warm_override) if warm_override > 0 else max(int(ema_len), int(atr_len))
    bt = BTParams(
        execution=execution, initial_capital=float(capital), side=side,
        fee_bps=float(fee_bps), slip_bps=float(slip_bps), risk_per_trade=float(risk),
        atr_stop_mult=float(stop_mult), take_profit_mult=float(tp_mult) if tp_enable else None,
        warmup_bars=warmup, max_leverage=float(max_lev),
        trailing_stop=ts_enable,
        trailing_atr_mult=float(ts_atr_mult) if ts_enable else 2.5,
    )
    res = run_backtest(kc, sig, bt)
    bh_res = run_buy_and_hold(df, initial_capital=float(capital)) if bh_enable else None
    trades = res["trades"]; equity = res["equity"]; metrics = res["metrics"]

    kc_out = kc.copy(); kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
    kc_csv = os.path.join(run_dir, f"{base}_kc.csv")
    trades_csv = os.path.join(run_dir, f"{base}_trades.csv")
    kc_out.to_csv(kc_csv); trades.to_csv(trades_csv, index=False)

    params = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "base": base, "ticker": ticker, "period": period or "", "interval": interval,
        "start": start or "", "end": end or "",
        "side": side, "execution": execution, "strategy": strategy_mode,
        "ema_len": int(ema_len), "atr_len": int(atr_len), "multiplier": float(mult),
        "risk_per_trade": float(risk), "atr_stop_mult": float(stop_mult),
        "take_profit_mult_enabled": tp_enable, "take_profit_mult": float(tp_mult) if tp_enable else None,
        "trend_ema_len": int(trend_ema),
        "fee_bps": float(fee_bps), "slip_bps": float(slip_bps), "warmup_override": int(warmup),
        "initial_capital": float(capital), "max_leverage": float(max_lev),
        "trailing_stop": ts_enable, "trailing_atr_mult": float(ts_atr_mult) if ts_enable else None,
    }
    if strategy_mode == "percentb":
        params.update({"pb_low": float(pb_low), "pb_high": float(pb_high)})
    if strategy_mode in ("pullback","regime_switch"):
        params.update({"slope_len": int(slope_len)})
    if strategy_mode == "regime_switch":
        params.update({"strong_mult": float(strong_mult)})

    with open(os.path.join(run_dir, f"{base}_params.json"), "w", encoding="utf-8") as f: json.dump(params, f, indent=2)
    metrics_clean = {k: float(v) if hasattr(v, "__float__") else v for k, v in metrics.items()}
    with open(os.path.join(run_dir, f"{base}_metrics.json"), "w", encoding="utf-8") as f: json.dump(metrics_clean, f, indent=2)
    pd.DataFrame([metrics_clean]).to_csv(os.path.join(run_dir, f"{base}_metrics.csv"), index=False)

    f_price = mpl_price(kc, trades, ticker); f_eq = mpl_equity(equity, ticker); f_dd = mpl_drawdown(equity, ticker)
    state["last"] = {"run_dir": run_dir, "base": base, "kc": kc, "trades": trades, "equity": equity,
                     "bh_equity": bh_res["equity"] if bh_res else None,
                     "bh_metrics": bh_res["metrics"] if bh_res else None,
                     "params": params, "metrics": metrics_clean, "mpl": {"price": f_price, "equity": f_eq, "dd": f_dd}}
    st.success(f"Saved in: {run_dir}")

tabs = st.tabs(["Backtest", "KC CSV", "Trades Explorer", "Run History", "Report Builder", "GBM Simulation"])

with tabs[0]:
    if state["last"] is None:
        st.info("Run a backtest to see results.")
    else:
        last = state["last"]; kc = last["kc"]; trades = last["trades"]; equity = last["equity"]
        metrics = last["metrics"]; ticker = last["params"]["ticker"]
        st.subheader("Metrics")
        st.write(f"CAGR {metrics['CAGR']:.2%} | Sharpe {metrics['Sharpe']:.2f} | Sortino {metrics['Sortino']:.2f}")
        st.write(f"MaxDD {metrics['MaxDrawdown']:.2%} | Exposure {metrics['Exposure']:.2%} | Trades {metrics['NumTrades']}")
        st.write(f"Expectancy {metrics.get('Expectancy', 0):.3f}R | WinRate {metrics.get('WinRate', 0):.1%} | AvgWin {metrics.get('AvgWinR', 0):.2f}R | AvgLoss {metrics.get('AvgLossR', 0):.2f}R | PerYear {metrics.get('TradesPerYear', 0):.1f}")
        if last.get("bh_equity") is not None:
            bh_metrics = last["bh_metrics"]
            st.write(f"--- B&H --- CAGR {bh_metrics['CAGR']:.2%} | Sharpe {bh_metrics['Sharpe']:.2f} | MaxDD {bh_metrics['MaxDrawdown']:.2%}")
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(plotly_price_ohlc(kc, trades, ticker), width='stretch')
            st.plotly_chart(plotly_equity(equity, ticker), width='stretch')
        with c2:
            st.plotly_chart(plotly_dd(equity), width='stretch')

        run_dir = last["run_dir"]; base = last["base"]
        kc_csv = os.path.join(run_dir, f"{base}_kc.csv")
        trades_csv = os.path.join(run_dir, f"{base}_trades.csv")
        if os.path.exists(kc_csv):
            with open(kc_csv, "rb") as f: st.download_button("Download KC CSV", f, file_name=os.path.basename(kc_csv), mime="text/csv")
        if os.path.exists(trades_csv):
            with open(trades_csv, "rb") as f: st.download_button("Download Trades CSV", f, file_name=os.path.basename(trades_csv), mime="text/csv")

with tabs[1]:
    if state["last"] is None:
        st.info("Run a backtest first.")
    else:
        run_dir = state["last"]["run_dir"]; base = state["last"]["base"]
        kc_csv = os.path.join(run_dir, f"{base}_kc.csv")
        kdf = safe_read_csv(kc_csv)
        if kdf is None:
            st.warning("KC CSV missing or empty.")
        else:
            st.subheader("Keltner Channel CSV")
            st.dataframe(kdf, width='stretch', height=480)

with tabs[2]:
    if state["last"] is None:
        st.info("Run a backtest first.")
    else:
        run_dir = state["last"]["run_dir"]; base = state["last"]["base"]
        trades_csv = os.path.join(run_dir, f"{base}_trades.csv")
        tdf = safe_read_csv(trades_csv, parse_date_cols=("entry_time","exit_time"))
        if tdf is None:
            st.warning("Trades CSV missing or empty.")
        else:
            st.subheader("Trades Explorer")
            colf = st.columns(4)
            with colf[0]: side_f = st.multiselect("Side", ["long","short"], default=["long","short"])
            with colf[1]: min_rr = st.number_input("Min R multiple", value=-5.0, step=0.5)
            with colf[2]: min_p = st.number_input("Min PnL", value=float(tdf.get("pnl", pd.Series([0])).min()), step=10.0)
            with colf[3]: max_p = st.number_input("Max PnL", value=float(tdf.get("pnl", pd.Series([0])).max()), step=10.0)
            if "side" in tdf.columns: tdf = tdf[tdf["side"].isin(side_f)]
            if "R" in tdf.columns:    tdf = tdf[tdf["R"] >= min_rr]
            if "pnl" in tdf.columns:  tdf = tdf[(tdf["pnl"] >= min_p) & (tdf["pnl"] <= max_p)]
            st.dataframe(tdf, width='stretch', height=420)
            if "R" in tdf.columns and len(tdf) > 0:
                st.plotly_chart(px.histogram(tdf, x="R", nbins=30, title="Distribution of R multiples"), width='stretch')

with tabs[3]:
    root = st.session_state.get("root_outdir", "runs").strip()
    dfhist = read_all_runs_logs(root)
    st.subheader("Run History")
    if dfhist.empty:
        st.info("No runs_log.csv files found under the save root.")
    else:
        tickers = sorted((dfhist["ticker"] if "ticker" in dfhist.columns else dfhist["ticker_folder"]).dropna().astype(str).unique())
        t_sel = st.multiselect("Ticker filter", tickers, default=tickers[:1] if tickers else [])
        if "ticker" in dfhist.columns:
            base_df = dfhist[dfhist["ticker"].astype(str).isin(t_sel)] if t_sel else dfhist
        else:
            base_df = dfhist[dfhist["ticker_folder"].astype(str).isin(t_sel)] if t_sel else dfhist
        st.dataframe(base_df, width='stretch', height=480)
        if {"Sharpe","MaxDrawdown"}.issubset(base_df.columns):
            st.plotly_chart(px.scatter(base_df, x="MaxDrawdown", y="Sharpe",
                                       color=(base_df["ticker"] if "ticker" in base_df.columns else base_df["ticker_folder"]),
                                       hover_data=["base"] if "base" in base_df.columns else None,
                                       title="Sharpe vs Max Drawdown"), width='stretch')

with tabs[4]:
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

with tabs[5]:
    st.subheader("GBM Monte Carlo Simulation")
    st.markdown("Tests strategy robustness across 1,000+ synthetic price paths using Geometric Brownian Motion.")

    sim_col1, sim_col2 = st.columns(2)
    with sim_col1:
        sim_mu = st.slider("Drift (mu)", -0.15, 0.15, 0.08, step=0.01, help="Annual drift. 0.08 = +8pct/yr bull market, -0.08 = -8pct/yr bear market, 0 = random walk")
    with sim_col2:
        sim_sigma = st.slider("Volatility (sigma)", 0.05, 0.50, 0.20, step=0.01, help="Annual volatility. 0.20 = 20pct annualized vol")

    sim_col3, sim_col4 = st.columns(2)
    with sim_col3:
        sim_paths = st.slider("Number of paths", 100, 2000, 500, step=50, help="500 paths = ~60s, 1000 paths = ~2min")
    with sim_col4:
        sim_days = st.slider("Trading days", 252, 5040, 2520, step=252, help="1 year = 252 days, 10 years = 2520")

    sim_strategy = st.selectbox("Simulate strategy", ["momentum", "mean_reversion", "percentb", "pullback", "regime_switch"], index=0)

    if st.button("Run GBM Simulation", width='stretch'):
        kc_params = {"ema_len": int(ema_len), "atr_len": int(atr_len), "mult": float(mult)}
        sig_params = {"mode": sim_strategy}
        if sim_strategy == "percentb":
            sig_params["low"] = float(pb_low)
            sig_params["high"] = float(pb_high)
        elif sim_strategy in ("pullback", "regime_switch"):
            sig_params["slope_len"] = int(slope_len) if slope_len else 20
        elif sim_strategy in ("momentum", "breakout", "trend"):
            sig_params["trend_ema_len"] = int(trend_ema)

        bt_sim = BTParams(
            execution="next_open", initial_capital=float(capital), side="long_only",
            fee_bps=1.0, slip_bps=2.0, risk_per_trade=0.01,
            atr_stop_mult=2.0, warmup_bars=20, max_leverage=1.0,
        )

        n_paths_val = int(sim_paths)
        n_days_val = int(sim_days)
        progress_bar = st.progress(0, text=f"Running 0/{n_paths_val} paths...")
        status_text = st.empty()

        def progress_callback(current, total):
            progress_bar.progress(current / total)
            if current % 50 == 0 or current == total:
                status_text.text(f"Running path {current}/{total}...")

        with st.spinner("Simulating GBM paths..."):
            from simulation import run_gbm_simulation
            result = run_gbm_simulation(
                kc_params=kc_params,
                bt_params=bt_sim,
                sig_params=sig_params,
                mu=float(sim_mu),
                sigma=float(sim_sigma),
                n_days=n_days_val,
                n_paths=n_paths_val,
                S0=100.0,
                progress_callback=progress_callback,
            )

        progress_bar.empty()
        status_text.empty()

        n_failed = result.get("failed", 0)
        if result["all_results"].empty:
            st.error(f"Simulation failed — all {n_paths_val} paths errored. Check console for details.")
        else:
            n_succeeded = len(result["all_results"])
            st.success(f"Completed {n_succeeded}/{n_paths_val} simulations across {n_days_val} trading days." + (f" ({n_failed} paths failed)" if n_failed > 0 else ""))
            if n_failed > 0:
                st.warning(f"{n_failed} paths failed due to NaN or errors — they are excluded from results.")

            summary = result["summary"]
            st.subheader("Distribution Results (Percentiles)")

            pct_cols = ["p5", "p25", "p50", "p75", "p95", "mean", "std"]
            metrics_display = ["CAGR", "Sharpe", "MaxDrawdown", "NumTrades", "Expectancy"]

            for m in metrics_display:
                if m in summary:
                    row = {p: f"{summary[m][p]:.3f}" for p in pct_cols if p in summary[m]}
                    st.write(f"**{m}**: {row}")

            st.subheader("CAGR Distribution")
            cagr_data = result["all_results"]["CAGR"].dropna()
            fig_cagr = px.histogram(cagr_data, nbins=50, title="CAGR Distribution across Simulated Paths")
            fig_cagr.update_layout(height=300)
            st.plotly_chart(fig_cagr, width='stretch')

            st.subheader("Sharpe Distribution")
            sharpe_data = result["all_results"]["Sharpe"].dropna()
            fig_sharpe = px.histogram(sharpe_data, nbins=50, title="Sharpe Ratio Distribution")
            fig_sharpe.update_layout(height=300)
            st.plotly_chart(fig_sharpe, width='stretch')

            st.subheader("Max Drawdown Distribution")
            dd_data = result["all_results"]["MaxDrawdown"].dropna()
            fig_dd = px.histogram(dd_data, nbins=50, title="Max Drawdown Distribution")
            fig_dd.update_layout(height=300)
            st.plotly_chart(fig_dd, width='stretch')

            st.subheader("Sample Equity Paths")
            paths_sample = result["paths"][:n_days_val, :100].T  # (100 paths, 2520 days)
            paths_df = pd.DataFrame(paths_sample, index=range(100), columns=pd.bdate_range("2015-01-01", periods=n_days_val))
            sample_paths = paths_df.sample(min(20, 100), axis=0)
            fig_paths = go.Figure()
            for _, row in sample_paths.iterrows():
                fig_paths.add_trace(go.Scatter(y=row.values, mode="lines", opacity=0.4, showlegend=False))
            fig_paths.update_layout(title="20 Sample Simulated Price Paths", height=300)
            st.plotly_chart(fig_paths, width='stretch')