from __future__ import annotations
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from data import fetch_ohlc
from indicators import keltner_channel
from strategy import breakout_signals
from backtester import run_backtest, BTParams

class KCBacktestApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Keltner Channel Backtester")
        self.geometry("1200x800")
        self.outdir = tk.StringVar(value="")
        self._build_ui()
        self._init_plots()

    def _build_ui(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=8, pady=8)

        ctrl = ttk.LabelFrame(root, text="Inputs")
        ctrl.pack(side="top", fill="x")

        r = 0
        ttk.Label(ctrl, text="Ticker").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.e_ticker = ttk.Entry(ctrl, width=12)
        self.e_ticker.insert(0, "AAPL")
        self.e_ticker.grid(row=r, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(ctrl, text="Period").grid(row=r, column=2, sticky="w", padx=4)
        self.period = tk.StringVar(value="5y")
        period_choices = ["1mo","3mo","6mo","1y","2y","5y","10y","max"]
        self.dd_period = ttk.Combobox(ctrl, textvariable=self.period, values=period_choices, width=7, state="readonly")
        self.dd_period.grid(row=r, column=3, sticky="w", padx=4, pady=4)

        ttk.Label(ctrl, text="Start").grid(row=r, column=4, sticky="w", padx=4)
        self.e_start = ttk.Entry(ctrl, width=12)
        self.e_start.insert(0, "")
        self.e_start.grid(row=r, column=5, sticky="w", padx=4)

        ttk.Label(ctrl, text="End").grid(row=r, column=6, sticky="w", padx=4)
        self.e_end = ttk.Entry(ctrl, width=12)
        self.e_end.insert(0, "")
        self.e_end.grid(row=r, column=7, sticky="w", padx=4)

        ttk.Label(ctrl, text="Side").grid(row=r, column=8, sticky="w", padx=4)
        self.side = tk.StringVar(value="long_short")
        self.dd_side = ttk.Combobox(ctrl, textvariable=self.side, values=["long_only","short_only","long_short"], width=12, state="readonly")
        self.dd_side.grid(row=r, column=9, sticky="w", padx=4, pady=4)

        ttk.Label(ctrl, text="Execution").grid(row=r, column=10, sticky="w", padx=4)
        self.execution = tk.StringVar(value="next_open")
        self.dd_exec = ttk.Combobox(ctrl, textvariable=self.execution, values=["next_open","next_close"], width=10, state="readonly")
        self.dd_exec.grid(row=r, column=11, sticky="w", padx=4, pady=4)

        r += 1
        self._slider(ctrl, r, 0, "EMA", 20, 5, 200, 1)
        self._slider(ctrl, r, 2, "ATR", 10, 5, 100, 1)
        self._slider(ctrl, r, 4, "Multiplier", 2.0, 1.0, 5.0, 0.1)
        self._slider(ctrl, r, 6, "Risk", 0.01, 0.001, 0.1, 0.001)
        self._slider(ctrl, r, 8, "Stop x ATR", 2.0, 0.5, 10.0, 0.1)

        ttk.Label(ctrl, text="TP x ATR").grid(row=r, column=10, sticky="w", padx=4)
        self.tp_enable = tk.BooleanVar(value=False)
        self.cb_tp = ttk.Checkbutton(ctrl, variable=self.tp_enable, command=self._toggle_tp)
        self.cb_tp.grid(row=r, column=11, sticky="w")
        r += 1

        self.tp_row = r
        self.tp_frame = ttk.Frame(ctrl)
        self.tp_frame.grid(row=r, column=0, columnspan=12, sticky="w")
        self.tp_scale = tk.Scale(self.tp_frame, from_=0.5, to=10.0, resolution=0.1, orient="horizontal", length=200)
        ttk.Label(self.tp_frame, text="Take Profit x ATR").pack(side="left", padx=4)
        self.tp_scale.set(4.0)
        self.tp_scale.pack(side="left", padx=4)
        self._toggle_tp()
        r += 1

        ttk.Label(ctrl, text="Fee bps").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.e_fee = ttk.Entry(ctrl, width=8)
        self.e_fee.insert(0, "1.0")
        self.e_fee.grid(row=r, column=1, sticky="w")

        ttk.Label(ctrl, text="Slip bps").grid(row=r, column=2, sticky="w", padx=4, pady=4)
        self.e_slip = ttk.Entry(ctrl, width=8)
        self.e_slip.insert(0, "2.0")
        self.e_slip.grid(row=r, column=3, sticky="w")

        ttk.Label(ctrl, text="Warmup").grid(row=r, column=4, sticky="w", padx=4, pady=4)
        self.e_warm = ttk.Entry(ctrl, width=8)
        self.e_warm.insert(0, "0")
        self.e_warm.grid(row=r, column=5, sticky="w")

        ttk.Label(ctrl, text="Save to").grid(row=r, column=6, sticky="w", padx=4, pady=4)
        self.e_outdir = ttk.Entry(ctrl, textvariable=self.outdir, width=30)
        self.e_outdir.grid(row=r, column=7, columnspan=3, sticky="we", padx=4)
        ttk.Button(ctrl, text="Choose Folder", command=self.choose_outdir).grid(row=r, column=10, sticky="w", padx=4)
        ttk.Button(ctrl, text="Run Backtest", command=self.run).grid(row=r, column=11, sticky="we", padx=4)

        self.metrics_box = ttk.LabelFrame(root, text="Metrics")
        self.metrics_box.pack(side="top", fill="x", pady=(8, 8))
        self.metrics_text = tk.Text(self.metrics_box, height=4)
        self.metrics_text.pack(fill="x")

        self.plot_box = ttk.Notebook(root)
        self.plot_box.pack(fill="both", expand=True)
        self.fig_price = Figure(figsize=(6,3))
        self.ax_price = self.fig_price.add_subplot(111)
        self.canvas_price = FigureCanvasTkAgg(self.fig_price, master=self.plot_box)
        self.canvas_price_widget = self.canvas_price.get_tk_widget()

        self.fig_equity = Figure(figsize=(6,3))
        self.ax_equity = self.fig_equity.add_subplot(111)
        self.canvas_equity = FigureCanvasTkAgg(self.fig_equity, master=self.plot_box)
        self.canvas_equity_widget = self.canvas_equity.get_tk_widget()

        self.fig_dd = Figure(figsize=(6,3))
        self.ax_dd = self.fig_dd.add_subplot(111)
        self.canvas_dd = FigureCanvasTkAgg(self.fig_dd, master=self.plot_box)
        self.canvas_dd_widget = self.canvas_dd.get_tk_widget()

        self.plot_box.add(self.canvas_price_widget, text="Price + Keltner")
        self.plot_box.add(self.canvas_equity_widget, text="Equity")
        self.plot_box.add(self.canvas_dd_widget, text="Drawdown")

    def _slider(self, parent, row, col, label, default, lo, hi, res):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=4)
        scale = tk.Scale(parent, from_=lo, to=hi, resolution=res, orient="horizontal", length=200)
        scale.set(default)
        scale.grid(row=row, column=col+1, sticky="w", padx=4)
        setattr(self, f"s_{label.replace(' ','_')}", scale)

    def _toggle_tp(self):
        if self.tp_enable.get():
            self.tp_frame.tkraise()
            self.tp_frame.grid()
        else:
            self.tp_frame.grid_remove()

    def choose_outdir(self):
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self.outdir.set(path)

    def _init_plots(self):
        self.ax_price.set_title("Price and Keltner Channel")
        self.ax_price.set_xlabel("Date")
        self.ax_price.set_ylabel("Price")
        self.canvas_price.draw()

        self.ax_equity.set_title("Equity Curve")
        self.ax_equity.set_xlabel("Date")
        self.ax_equity.set_ylabel("Equity")
        self.canvas_equity.draw()

        self.ax_dd.set_title("Drawdown")
        self.canvas_dd.draw()

    def _clear_plots(self):
        self.ax_price.cla()
        self.ax_equity.cla()
        self.ax_dd.cla()

    def run(self):
        ticker = self.e_ticker.get().strip()
        if not ticker:
            messagebox.showerror("Error", "Ticker is required")
            return

        period = self.period.get().strip() or None
        start = self.e_start.get().strip() or None
        end = self.e_end.get().strip() or None
        if start and not self._valid_date(start):
            messagebox.showerror("Error", "Start date must be YYYY-MM-DD")
            return
        if end and not self._valid_date(end):
            messagebox.showerror("Error", "End date must be YYYY-MM-DD")
            return
        if start and period:
            if not messagebox.askyesno("Confirm", "Both period and start are set. Use period and ignore dates?"):
                return
            start, end = None, None

        outdir = self.outdir.get().strip()
        if not outdir:
            messagebox.showerror("Error", "Choose an output folder")
            return
        os.makedirs(outdir, exist_ok=True)

        try:
            df = fetch_ohlc(ticker, start=start, end=end, period=period)
        except Exception as e:
            messagebox.showerror("Ticker error", f"Failed to fetch data for {ticker}\n{e}")
            return

        ema_len = int(self.s_EMA.get())
        atr_len = int(self.s_ATR.get())
        mult = float(self.s_Multiplier.get())
        risk = float(self.s_Risk.get())
        stop_mult = float(self.s_Stop_x_ATR.get())
        tp = float(self.tp_scale.get()) if self.tp_enable.get() else None

        side = self.side.get()
        execution = self.execution.get()
        fee_bps = float(self.e_fee.get())
        slip_bps = float(self.e_slip.get())
        warm = int(self.e_warm.get())
        warmup = warm if warm > 0 else max(ema_len, atr_len)

        kc = keltner_channel(df, ema_len=ema_len, atr_len=atr_len, mult=mult)
        sig = breakout_signals(kc)

        bt = BTParams(
            execution=execution,
            initial_capital=100000.0,
            side=side,
            fee_bps=fee_bps,
            slip_bps=slip_bps,
            risk_per_trade=risk,
            atr_stop_mult=stop_mult,
            take_profit_mult=tp,
            warmup_bars=warmup,
            max_leverage=1.0,
        )
        res = run_backtest(kc, sig, bt)

        base = ticker
        kc_out = kc.copy()
        kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
        kc_csv = os.path.join(outdir, f"{base}_kc.csv")
        trades_csv = os.path.join(outdir, f"trades_{base}.csv")
        kc_out.to_csv(kc_csv)
        res["trades"].to_csv(trades_csv, index=False)

        met = res["metrics"]
        txt = (
            f"CAGR {met['CAGR']:.2%}  |  Sharpe {met['Sharpe']:.2f}  |  "
            f"Sortino {met['Sortino']:.2f}  |  MaxDD {met['MaxDrawdown']:.2%}  |  "
            f"Exposure {met['Exposure']:.2%}  |  Trades {met['NumTrades']}\n"
            f"Saved to: {outdir}"
        )
        self.metrics_text.delete("1.0", "end")
        self.metrics_text.insert("end", txt)

        self._clear_plots()

        self.ax_price.plot(kc.index, kc["Close"], label="Close")
        self.ax_price.plot(kc.index, kc["KC_Middle"], label="KC Middle")
        self.ax_price.plot(kc.index, kc["KC_Upper"], label="KC Upper")
        self.ax_price.plot(kc.index, kc["KC_Lower"], label="KC Lower")

        tdf = res["trades"]
        if not tdf.empty:
            longs = tdf[tdf["side"]=="long"]
            shorts = tdf[tdf["side"]=="short"]
            self.ax_price.scatter(longs["entry_time"], longs["entry_px"], marker="^", s=40, label="Long Entry")
            self.ax_price.scatter(longs["exit_time"], longs["exit_px"], marker="v", s=40, label="Long Exit")
            self.ax_price.scatter(shorts["entry_time"], shorts["entry_px"], marker="v", s=40, label="Short Entry")
            self.ax_price.scatter(shorts["exit_time"], shorts["exit_px"], marker="^", s=40, label="Short Exit")
        self.ax_price.legend(loc="best")
        self.ax_price.set_title(f"{ticker} Keltner Channel")
        self.ax_price.set_xlabel("Date")
        self.ax_price.set_ylabel("Price")
        self.canvas_price.draw()

        curve = res["equity"]
        self.ax_equity.plot(curve.index, curve.values, label="Equity")
        self.ax_equity.set_title(f"Equity Curve, {ticker}")
        self.ax_equity.set_xlabel("Date")
        self.ax_equity.set_ylabel("Equity")
        self.ax_equity.legend(loc="best")
        self.canvas_equity.draw()

        dd = curve / curve.cummax() - 1.0
        self.ax_dd.fill_between(dd.index, dd.values, 0, step="pre")
        self.ax_dd.set_title(f"Drawdown, {ticker}")
        self.canvas_dd.draw()

        price_png = os.path.join(outdir, f"{base}_kc.png")
        equity_png = os.path.join(outdir, f"{base}_equity.png")
        dd_png = os.path.join(outdir, f"{base}_drawdown.png")
        self.fig_price.savefig(price_png, dpi=150, bbox_inches="tight")
        self.fig_equity.savefig(equity_png, dpi=150, bbox_inches="tight")
        self.fig_dd.savefig(dd_png, dpi=150, bbox_inches="tight")

        messagebox.showinfo("Done", f"Backtest complete.\nFiles saved in:\n{outdir}")

    @staticmethod
    def _valid_date(s: str) -> bool:
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except Exception:
            return False

if __name__ == "__main__":
    app = KCBacktestApp()
    app.mainloop()
