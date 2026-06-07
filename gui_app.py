from __future__ import annotations
import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
from data import fetch_ohlc, interval_limit
from indicators import keltner_channel
from strategy import keltner_signals
from backtester import run_backtest, BTParams

class KCBacktestApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Keltner Channel Backtester")
        self.geometry("1200x800")
        self.outdir = tk.StringVar(value="")
        self._build_ui()
        self._init_plots()
        self._last_run_info = None

    def _build_ui(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=8, pady=8)
        root.columnconfigure(0, weight=1)

        ctrl = ttk.LabelFrame(root, text="Inputs")
        ctrl.grid(row=0, column=0, sticky="nsew")
        for c in range(14):
            ctrl.columnconfigure(c, weight=1, uniform="cols")

        r = 0
        ttk.Label(ctrl, text="Ticker").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.e_ticker = ttk.Entry(ctrl, width=10); self.e_ticker.insert(0, "AAPL")
        self.e_ticker.grid(row=r, column=1, sticky="we", padx=4, pady=4)

        ttk.Label(ctrl, text="Period").grid(row=r, column=2, sticky="w", padx=4)
        self.period = tk.StringVar(value="5y")
        period_choices = ["1mo","3mo","6mo","1y","2y","5y","10y","max"]
        self.dd_period = ttk.Combobox(ctrl, textvariable=self.period, values=period_choices, width=7, state="readonly")
        self.dd_period.grid(row=r, column=3, sticky="we", padx=4, pady=4)

        # NEW interval selector
        ttk.Label(ctrl, text="Interval").grid(row=r, column=4, sticky="w", padx=4)
        self.interval = tk.StringVar(value="1d")
        ival_choices = ["1m","2m","5m","15m","30m","1h","1d","1wk","1mo"]
        self.dd_interval = ttk.Combobox(ctrl, textvariable=self.interval, values=ival_choices, width=7, state="readonly")
        self.dd_interval.grid(row=r, column=5, sticky="we", padx=4, pady=4)

        # Start End shifted to the right
        ttk.Label(ctrl, text="Start").grid(row=r, column=6, sticky="w", padx=4)
        self.e_start = ttk.Entry(ctrl, width=12); self.e_start.insert(0, "")
        self.e_start.grid(row=r, column=7, sticky="we", padx=4)

        ttk.Label(ctrl, text="End").grid(row=r, column=8, sticky="w", padx=4)
        self.e_end = ttk.Entry(ctrl, width=12); self.e_end.insert(0, "")
        self.e_end.grid(row=r, column=9, sticky="we", padx=4)

        ttk.Label(ctrl, text="Side").grid(row=r, column=10, sticky="w", padx=4)
        self.side = tk.StringVar(value="long_short")
        self.dd_side = ttk.Combobox(ctrl, textvariable=self.side, values=["long_only","short_only","long_short"], width=12, state="readonly")
        self.dd_side.grid(row=r, column=11, sticky="we", padx=4, pady=4)

        ttk.Label(ctrl, text="Execution").grid(row=r, column=12, sticky="w", padx=4)
        self.execution = tk.StringVar(value="next_open")
        self.dd_exec = ttk.Combobox(ctrl, textvariable=self.execution, values=["next_open","next_close"], width=10, state="readonly")
        self.dd_exec.grid(row=r, column=13, sticky="we", padx=4, pady=4)

        # lookback limit note
        r += 1
        self.limit_note = ttk.Label(ctrl, foreground="#666")
        self.limit_note.grid(row=r, column=0, columnspan=14, sticky="w", padx=6, pady=(0,6))
        self.dd_interval.bind("<<ComboboxSelected>>", lambda _e=None: self._update_limit_note())
        self._update_limit_note()

        r += 1
        self._slider(ctrl, r, 0, "EMA", 20, 5, 200, 1.0)
        self._slider(ctrl, r, 2, "ATR", 10, 5, 100, 1.0)
        self._slider(ctrl, r, 4, "Multiplier", 2.0, 1.0, 5.0, 0.1)
        self._slider(ctrl, r, 6, "Risk", 0.010, 0.001, 0.100, 0.001)
        self._slider(ctrl, r, 8, "Stop x ATR", 2.0, 0.5, 10.0, 0.1)
        self._slider(ctrl, r, 10, "Trend EMA", 200, 20, 500, 10)

        ttk.Label(ctrl, text="TP x ATR").grid(row=r, column=10, sticky="w", padx=4)
        self.tp_enable = tk.BooleanVar(value=False)
        self.cb_tp = ttk.Checkbutton(ctrl, variable=self.tp_enable, command=self._toggle_tp)
        self.cb_tp.grid(row=r, column=11, sticky="w")
        r += 1

        self.tp_row = r
        self.tp_frame = ttk.Frame(ctrl)
        self.tp_frame.grid(row=r, column=0, columnspan=14, sticky="we", padx=4)
        self.tp_frame.columnconfigure(1, weight=1)
        ttk.Label(self.tp_frame, text="Take Profit x ATR").grid(row=0, column=0, sticky="w")
        self.tp_scale = ttk.Scale(self.tp_frame, from_=0.5, to=10.0, orient="horizontal")
        self.tp_scale.set(4.0)
        self.tp_scale.grid(row=0, column=1, sticky="we", padx=6)
        self._toggle_tp()
        r += 1

        ttk.Label(ctrl, text="Trailing Stop").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.ts_enable = tk.BooleanVar(value=False)
        self.cb_ts = ttk.Checkbutton(ctrl, variable=self.ts_enable, command=self._toggle_ts)
        self.cb_ts.grid(row=r, column=1, sticky="w")
        ttk.Label(ctrl, text="x ATR").grid(row=r, column=2, sticky="w", padx=2)
        self.e_ts_mult = ttk.Entry(ctrl, width=6); self.e_ts_mult.insert(0, "2.5")
        self.e_ts_mult.grid(row=r, column=3, sticky="we", padx=4)
        self._toggle_ts()

        r += 1
        ttk.Label(ctrl, text="Fee bps").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.e_fee = ttk.Entry(ctrl, width=8); self.e_fee.insert(0, "1.0")
        self.e_fee.grid(row=r, column=1, sticky="we", padx=4)

        ttk.Label(ctrl, text="Slip bps").grid(row=r, column=2, sticky="w", padx=4, pady=4)
        self.e_slip = ttk.Entry(ctrl, width=8); self.e_slip.insert(0, "2.0")
        self.e_slip.grid(row=r, column=3, sticky="we", padx=4)

        ttk.Label(ctrl, text="Warmup").grid(row=r, column=4, sticky="w", padx=4, pady=4)
        self.e_warm = ttk.Entry(ctrl, width=8); self.e_warm.insert(0, "0")
        self.e_warm.grid(row=r, column=5, sticky="we", padx=4)

        ttk.Label(ctrl, text="Strategy").grid(row=r, column=6, sticky="w", padx=4)
        self.strategy = tk.StringVar(value="momentum")
        self.dd_strategy = ttk.Combobox(
            ctrl, textvariable=self.strategy,
            values=["momentum","mean_reversion","percentb","pullback","regime_switch"],
            width=14, state="readonly"
        )
        self.dd_strategy.grid(row=r, column=7, sticky="we", padx=4, pady=4)
        self.dd_strategy.bind("<<ComboboxSelected>>", lambda _e=None: self._update_strategy_controls())

        r += 1
        self.pb_frame = ttk.Frame(ctrl)
        self.pb_frame.grid(row=r, column=0, columnspan=14, sticky="we", padx=4)
        self.pb_frame.columnconfigure(1, weight=1)
        ttk.Label(self.pb_frame, text="PercentB Low").grid(row=0, column=0, sticky="w")
        self.e_pb_low = ttk.Entry(self.pb_frame, width=6); self.e_pb_low.insert(0, "0.20")
        self.e_pb_low.grid(row=0, column=1, sticky="we", padx=4)
        ttk.Label(self.pb_frame, text="High").grid(row=0, column=2, sticky="w", padx=(12,0))
        self.e_pb_high = ttk.Entry(self.pb_frame, width=6); self.e_pb_high.insert(0, "0.80")
        self.e_pb_high.grid(row=0, column=3, sticky="we", padx=4)
        self._update_strategy_controls()

        r += 1
        ttk.Label(ctrl, text="Capital $").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.e_capital = ttk.Entry(ctrl, width=10); self.e_capital.insert(0, "100000")
        self.e_capital.grid(row=r, column=1, sticky="we", padx=4)
        ttk.Label(ctrl, text="Max Lev").grid(row=r, column=2, sticky="w", padx=4, pady=4)
        self.e_max_lev = ttk.Entry(ctrl, width=6); self.e_max_lev.insert(0, "1.0")
        self.e_max_lev.grid(row=r, column=3, sticky="we", padx=4)

        ttk.Label(ctrl, text="Save to").grid(row=r, column=8, sticky="w", padx=4, pady=4)
        self.e_outdir = ttk.Entry(ctrl, textvariable=self.outdir)
        self.e_outdir.grid(row=r, column=9, columnspan=3, sticky="we", padx=4)

        ttk.Button(ctrl, text="Choose Folder", command=self.choose_outdir).grid(row=r, column=12, sticky="we", padx=4)
        ttk.Button(ctrl, text="Run Backtest", command=self.run).grid(row=r, column=13, sticky="we", padx=4)

        r += 1
        ttk.Button(ctrl, text="Export PDF", command=self.export_pdf).grid(row=r, column=12, columnspan=2, sticky="we", padx=4, pady=(0,6))

        self.metrics_box = ttk.LabelFrame(root, text="Metrics")
        self.metrics_box.grid(row=1, column=0, sticky="we", pady=(8, 8))
        self.metrics_box.columnconfigure(0, weight=1)
        self.metrics_text = tk.Text(self.metrics_box, height=4)
        self.metrics_text.grid(row=0, column=0, sticky="we")

        self.plot_box = ttk.Notebook(root)
        self.plot_box.grid(row=2, column=0, sticky="nsew")
        root.rowconfigure(2, weight=1)

        self.fig_price = Figure(figsize=(6,3)); self.ax_price = self.fig_price.add_subplot(111)
        self.canvas_price = FigureCanvasTkAgg(self.fig_price, master=self.plot_box)
        self.canvas_price_widget = self.canvas_price.get_tk_widget()

        self.fig_equity = Figure(figsize=(6,3)); self.ax_equity = self.fig_equity.add_subplot(111)
        self.canvas_equity = FigureCanvasTkAgg(self.fig_equity, master=self.plot_box)
        self.canvas_equity_widget = self.canvas_equity.get_tk_widget()

        self.fig_dd = Figure(figsize=(6,3)); self.ax_dd = self.fig_dd.add_subplot(111)
        self.canvas_dd = FigureCanvasTkAgg(self.fig_dd, master=self.plot_box)
        self.canvas_dd_widget = self.canvas_dd.get_tk_widget()

        self.plot_box.add(self.canvas_price_widget, text="Price + Keltner")
        self.plot_box.add(self.canvas_equity_widget, text="Equity")
        self.plot_box.add(self.canvas_dd_widget, text="Drawdown")

    def _update_limit_note(self):
        lim = interval_limit(self.interval.get())
        self.limit_note.config(text=f"Max lookback for {self.interval.get()} is {lim['period_hint']}  {lim['note']}")

    def _slider(self, parent, row, col, label, default, lo, hi, res):
        cell = ttk.Frame(parent)
        cell.grid(row=row, column=col, columnspan=2, sticky="we", padx=4, pady=2)
        cell.columnconfigure(0, weight=1)
        cell.columnconfigure(1, weight=0)

        ttk.Label(cell, text=label).grid(row=0, column=0, sticky="w")

        def _decimals(x: float) -> int:
            s = f"{x:.10f}".rstrip("0").rstrip(".")
            return len(s.split(".")[1]) if "." in s else 0

        dec = _decimals(res)
        def _fmt(v: float) -> str:
            return f"{v:.{dec}f}" if dec > 0 else f"{int(round(v))}"

        def _snap(v: float) -> float:
            steps = round((v - lo) / res)
            sv = lo + steps * res
            if sv < lo: sv = lo
            if sv > hi: sv = hi
            return float(sv)

        val = tk.StringVar(value=_fmt(default))
        val_entry = ttk.Entry(cell, textvariable=val, width=max(4, dec + 3))
        val_entry.grid(row=0, column=1, sticky="e")

        scale = ttk.Scale(cell, from_=lo, to=hi, orient="horizontal")
        scale.set(default)
        scale.grid(row=1, column=0, columnspan=2, sticky="we")

        def _on_motion(v):
            try: val.set(_fmt(float(v)))
            except Exception: pass

        def _on_release(_evt=None):
            v = _snap(float(scale.get())); scale.set(v); val.set(_fmt(v))

        def _entry_update(_evt=None):
            try:
                v = float(val.get()); v = max(min(v, hi), lo); v = _snap(v)
                scale.set(v); val.set(_fmt(v))
            except Exception:
                val.set(_fmt(float(scale.get())))

        scale.configure(command=_on_motion)
        scale.bind("<ButtonRelease-1>", _on_release)
        val_entry.bind("<Return>", _entry_update)
        val_entry.bind("<FocusOut>", _entry_update)

        setattr(self, f"s_{label.replace(' ','_')}", scale)

    def _toggle_tp(self):
        if self.tp_enable.get():
            self.tp_frame.tkraise(); self.tp_frame.grid()
        else:
            self.tp_frame.grid_remove()

    def _toggle_ts(self):
        self.e_ts_mult.configure(state="normal" if self.ts_enable.get() else "disabled")

    def _update_strategy_controls(self):
        strategy = self.strategy.get()
        if strategy == "percentb":
            self.pb_frame.grid()
        else:
            self.pb_frame.grid_remove()

    def choose_outdir(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path: self.outdir.set(path)

    def _init_plots(self):
        self.ax_price.set_title("Price and Keltner Channel")
        self.ax_price.set_xlabel("Date"); self.ax_price.set_ylabel("Price")
        self.canvas_price.draw()
        self.ax_equity.set_title("Equity Curve")
        self.ax_equity.set_xlabel("Date"); self.ax_equity.set_ylabel("Equity")
        self.canvas_equity.draw()
        self.ax_dd.set_title("Drawdown"); self.canvas_dd.draw()

    def _clear_plots(self):
        self.ax_price.cla(); self.ax_equity.cla(); self.ax_dd.cla()

    def _collect_inputs(self, ticker, start, end, period):
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "ticker": ticker, "period": period, "interval": self.interval.get(),
            "start": start, "end": end,
            "side": self.side.get(), "execution": self.execution.get(),
            "strategy": self.strategy.get(),
            "ema_len": int(float(self.s_EMA.get())),
            "atr_len": int(float(self.s_ATR.get())),
            "multiplier": float(self.s_Multiplier.get()),
            "risk_per_trade": float(self.s_Risk.get()),
            "atr_stop_mult": float(self.s_Stop_x_ATR.get()),
            "take_profit_mult_enabled": self.tp_enable.get(),
            "take_profit_mult": float(self.tp_scale.get()) if self.tp_enable.get() else None,
            "trend_ema_len": int(float(self.s_Trend_EMA.get())),
            "fee_bps": float(self.e_fee.get()),
            "slip_bps": float(self.e_slip.get()),
            "warmup_override": int(self.e_warm.get()),
            "initial_capital": float(self.e_capital.get()),
            "max_leverage": float(self.e_max_lev.get()),
            "pb_low": float(self.e_pb_low.get()),
            "pb_high": float(self.e_pb_high.get()),
            "trailing_stop": self.ts_enable.get(),
            "trailing_atr_mult": float(self.e_ts_mult.get()) if self.ts_enable.get() else None,
        }

    def _save_params_and_metrics(self, outdir, base, params, metrics):
        params_path = os.path.join(outdir, f"{base}_params.json")
        metrics_path = os.path.join(outdir, f"{base}_metrics.json")
        with open(params_path, "w", encoding="utf-8") as f: json.dump(params, f, indent=2)
        with open(metrics_path, "w", encoding="utf-8") as f: json.dump(metrics, f, indent=2)
        met_csv = os.path.join(outdir, f"{base}_metrics.csv")
        pd.DataFrame([metrics]).to_csv(met_csv, index=False)
        registry_csv = os.path.join(os.path.dirname(outdir), "runs_log.csv")
        row = {**{"base": base}, **params, **metrics}
        df_row = pd.DataFrame([row])
        if os.path.exists(registry_csv):
            try:
                old = pd.read_csv(registry_csv)
                pd.concat([old, df_row], ignore_index=True).to_csv(registry_csv, index=False)
            except Exception:
                df_row.to_csv(registry_csv, index=False)
        else:
            df_row.to_csv(registry_csv, index=False)

    def run(self):
        ticker = self.e_ticker.get().strip()
        if not ticker:
            messagebox.showerror("Error", "Ticker is required"); return
        period = self.period.get().strip() or None
        start = self.e_start.get().strip() or None
        end = self.e_end.get().strip() or None
        if start and period:
            if not messagebox.askyesno("Confirm", "Both period and start are set. Use period and ignore dates?"):
                return
            start, end = None, None
        root_outdir = self.outdir.get().strip()
        if not root_outdir:
            messagebox.showerror("Error", "Choose an output folder"); return

        run_dir = os.path.join(root_outdir, ticker); os.makedirs(run_dir, exist_ok=True)

        try:
            df = fetch_ohlc(ticker, start=start, end=end, period=period, interval=self.interval.get())
        except Exception as e:
            messagebox.showerror("Ticker error", f"Failed to fetch data for {ticker}\n{e}")
            return

        ema_len = int(float(self.s_EMA.get())); atr_len = int(float(self.s_ATR.get()))
        mult = float(self.s_Multiplier.get()); risk = float(self.s_Risk.get())
        stop_mult = float(self.s_Stop_x_ATR.get())
        trend_ema = int(float(self.s_Trend_EMA.get()))
        tp = float(self.tp_scale.get()) if self.tp_enable.get() else None
        side = self.side.get(); execution = self.execution.get()
        strategy_mode = self.strategy.get()
        fee_bps = float(self.e_fee.get()); slip_bps = float(self.e_slip.get())
        warm = int(self.e_warm.get()); warmup = warm if warm > 0 else max(ema_len, atr_len)
        capital = float(self.e_capital.get())
        max_lev = float(self.e_max_lev.get())
        pb_low = float(self.e_pb_low.get()); pb_high = float(self.e_pb_high.get())
        trailing_stop = self.ts_enable.get()
        trailing_atr_mult = float(self.e_ts_mult.get()) if self.ts_enable.get() else 2.5

        kc = keltner_channel(df, ema_len=ema_len, atr_len=atr_len, mult=mult)

        sig_kwargs = {}
        if strategy_mode == "percentb":
            sig_kwargs = {"low": pb_low, "high": pb_high}
        if strategy_mode == "pullback":
            sig_kwargs = {"slope_len": 20}
        if strategy_mode == "regime_switch":
            sig_kwargs = {"slope_len": 20, "strong_mult": 1.0, "trend_ema_len": trend_ema}
        if strategy_mode in ("momentum", "breakout", "trend"):
            sig_kwargs = {"trend_ema_len": trend_ema}

        sig = keltner_signals(kc, mode=strategy_mode, **sig_kwargs)

        bt = BTParams(
            execution=execution, initial_capital=capital, side=side,
            fee_bps=fee_bps, slip_bps=slip_bps, risk_per_trade=risk,
            atr_stop_mult=stop_mult, take_profit_mult=tp,
            warmup_bars=warmup, max_leverage=max_lev,
            trailing_stop=trailing_stop,
            trailing_atr_mult=trailing_atr_mult,
        )
        res = run_backtest(kc, sig, bt)
        base = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        kc_out = kc.copy(); kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
        kc_csv = os.path.join(run_dir, f"{base}_kc.csv")
        trades_csv = os.path.join(run_dir, f"{base}_trades.csv")
        kc_out.to_csv(kc_csv); res["trades"].to_csv(trades_csv, index=False)
        met = res["metrics"]; metrics_clean = {k: (float(v) if hasattr(v, "__float__") else v) for k, v in met.items()}
        txt = (
            f"CAGR {met['CAGR']:.2%}  |  Sharpe {met['Sharpe']:.2f}  |  "
            f"Sortino {met['Sortino']:.2f}  |  MaxDD {met['MaxDrawdown']:.2%}  |  "
            f"Exposure {met['Exposure']:.2%}  |  Trades {met['NumTrades']}\n"
            f"Expectancy {met.get('Expectancy', 0):.3f}R  |  WinRate {met.get('WinRate', 0):.1%}  |  "
            f"AvgWin {met.get('AvgWinR', 0):.2f}R  |  AvgLoss {met.get('AvgLossR', 0):.2f}R  |  "
            f"PerYear {met.get('TradesPerYear', 0):.1f}\n"
            f"Saved to: {run_dir}"
        )
        self.metrics_text.delete("1.0", "end"); self.metrics_text.insert("end", txt)

        self._clear_plots()
        self.ax_price.plot(kc.index, kc["Close"], label="Close")
        self.ax_price.plot(kc.index, kc["KC_Middle"], label="KC Middle")
        self.ax_price.plot(kc.index, kc["KC_Upper"], label="KC Upper")
        self.ax_price.plot(kc.index, kc["KC_Lower"], label="KC Lower")
        tdf = res["trades"]
        if not tdf.empty:
            longs = tdf[tdf["side"]=="long"]; shorts = tdf[tdf["side"]=="short"]
            self.ax_price.scatter(longs["entry_time"], longs["entry_px"], marker="^", s=40, label="Long Entry")
            self.ax_price.scatter(longs["exit_time"], longs["exit_px"], marker="v", s=40, label="Long Exit")
            self.ax_price.scatter(shorts["entry_time"], shorts["entry_px"], marker="v", s=40, label="Short Entry")
            self.ax_price.scatter(shorts["exit_time"], shorts["exit_px"], marker="^", s=40, label="Short Exit")
        self.ax_price.legend(loc="best"); self.ax_price.set_title(f"{ticker} Keltner Channel")
        self.ax_price.set_xlabel("Date"); self.ax_price.set_ylabel("Price")
        self.canvas_price.draw()

        curve = res["equity"]
        self.ax_equity.plot(curve.index, curve.values, label="Equity")
        self.ax_equity.set_title(f"Equity Curve, {ticker}")
        self.ax_equity.set_xlabel("Date"); self.ax_equity.set_ylabel("Equity")
        self.ax_equity.legend(loc="best"); self.canvas_equity.draw()

        dd = curve / curve.cummax() - 1.0
        self.ax_dd.fill_between(dd.index, dd.values, 0, step="pre")
        self.ax_dd.set_title(f"Drawdown, {ticker}"); self.canvas_dd.draw()

        price_png = os.path.join(run_dir, f"{base}_kc.png")
        equity_png = os.path.join(run_dir, f"{base}_equity.png")
        dd_png = os.path.join(run_dir, f"{base}_drawdown.png")
        self.fig_price.savefig(price_png, dpi=150, bbox_inches="tight")
        self.fig_equity.savefig(equity_png, dpi=150, bbox_inches="tight")
        self.fig_dd.savefig(dd_png, dpi=150, bbox_inches="tight")

        params = self._collect_inputs(ticker, start, end, period)
        self._save_params_and_metrics(run_dir, base, params, metrics_clean)
        summary_txt = os.path.join(run_dir, f"{base}_summary.txt")
        with open(summary_txt, "w", encoding="utf-8") as f:
            f.write(f"Run: {base}\n")
            f.write(f"Timestamp: {params['timestamp']}\n")
            f.write("Parameters:\n")
            for k, v in params.items():
                f.write(f"  {k}: {v}\n")
            f.write("\nMetrics:\n")
            for k, v in metrics_clean.items():
                f.write(f"  {k}: {v}\n")

        self._last_run_info = {"run_dir": run_dir, "base": base, "params": params, "metrics": metrics_clean}
        messagebox.showinfo("Done", f"Backtest complete.\nFiles saved in:\n{run_dir}")

    def export_pdf(self):
        if not self._last_run_info:
            messagebox.showerror("Error", "Run a backtest first"); return
        run_dir = self._last_run_info["run_dir"]; base = self._last_run_info["base"]
        params = self._last_run_info["params"]; metrics = self._last_run_info["metrics"]
        pdf_path = os.path.join(run_dir, f"{base}_report.pdf")

        page = Figure(figsize=(8.27, 11.69))
        ax = page.add_subplot(111); ax.axis("off")

        def fmt_block(title, d):
            lines = [title] + [f"{k}: {v}" for k, v in d.items()]
            return "\n".join(lines)

        txt = f"Run: {base}\nTimestamp: {params['timestamp']}\n\n" + fmt_block("Parameters", params) + "\n\n" + fmt_block("Metrics", metrics)
        with PdfPages(pdf_path) as pp:
            ax.text(0.05, 0.95, "Keltner Channel Backtest Report", fontsize=16, va="top", ha="left")
            ax.text(0.05, 0.90, txt, fontsize=9, va="top", ha="left", family="monospace")
            pp.savefig(page, bbox_inches="tight")
            pp.savefig(self.fig_price, bbox_inches="tight")
            pp.savefig(self.fig_equity, bbox_inches="tight")
            pp.savefig(self.fig_dd, bbox_inches="tight")

        messagebox.showinfo("PDF Exported", f"Report saved to:\n{pdf_path}")

if __name__ == "__main__":
    app = KCBacktestApp()
    app.mainloop()
