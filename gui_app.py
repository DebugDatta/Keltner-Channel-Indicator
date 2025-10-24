from __future__ import annotations
import os
import json
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import webbrowser
import requests
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

try:
    import ttkbootstrap as tb
    ThemedTk = tb.Window
    use_bootstrap = True
except Exception:
    ThemedTk = tk.Tk
    use_bootstrap = False

from data import fetch_ohlc
from indicators import keltner_channel
from strategy import breakout_signals
from backtester import run_backtest, BTParams


class TickerSearchFrame(ttk.Frame):
    def __init__(self, parent, add_callback):
        super().__init__(parent)
        self.add_callback = add_callback
        self.query = tk.StringVar()
        self.cache = {}
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=6)
        ttk.Label(top, text="Search").pack(side="left")
        self.entry = ttk.Entry(top, textvariable=self.query, width=24)
        self.entry.pack(side="left", padx=6)
        self.entry.bind("<KeyRelease>", self.on_search)
        ttk.Button(top, text="Add", command=self.add_selected).pack(side="left", padx=4)
        ttk.Button(top, text="Clear", command=self.clear_list).pack(side="left", padx=4)
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.listbox = tk.Listbox(body, selectmode="extended", height=10)
        self.listbox.pack(fill="both", expand=True)

    def on_search(self, _evt=None):
        q = self.query.get().strip()
        self.listbox.delete(0, "end")
        if not q:
            return
        if q in self.cache:
            syms = self.cache[q]
        else:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={q}"
            try:
                res = requests.get(url, timeout=4).json()
                syms = []
                for it in res.get("quotes", []):
                    s = it.get("symbol")
                    if s:
                        syms.append(s)
                self.cache[q] = syms
            except Exception:
                syms = []
        for s in syms[:50]:
            self.listbox.insert("end", s)

    def add_selected(self):
        items = [self.listbox.get(i) for i in self.listbox.curselection()]
        if items:
            self.add_callback(items)

    def clear_list(self):
        self.listbox.delete(0, "end")


class KCBacktestApp(ThemedTk):
    def __init__(self):
        super().__init__(themename="darkly") if use_bootstrap else super().__init__()
        self.title("Keltner Channel Backtester")
        self.geometry("1500x950")
        self.outdir_root = tk.StringVar(value="")
        self.theme_var = tk.StringVar(value="darkly" if use_bootstrap else "default")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.status_var = tk.StringVar(value="Idle")
        self.queue = queue.Queue()
        self.executor_thread = None
        self.stop_flag = threading.Event()
        self.selected_tickers = []
        self._build_ui()
        self._init_plots()
        self.after(120, self._process_queue)

    def _build_ui(self):
        self.paned = tk.PanedWindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        left = ttk.Frame(self.paned)
        right = ttk.Frame(self.paned)
        self.paned.add(left, minsize=460)
        self.paned.add(right)

        ctrl = ttk.LabelFrame(left, text="Inputs")
        ctrl.pack(side="top", fill="x", padx=8, pady=8)

        r = 0
        ttk.Label(ctrl, text="Period").grid(row=r, column=0, sticky="w", padx=4, pady=4)
        self.period = tk.StringVar(value="5y")
        self.dd_period = ttk.Combobox(ctrl, textvariable=self.period, values=["1mo","3mo","6mo","1y","2y","5y","10y","max"], width=10, state="readonly")
        self.dd_period.grid(row=r, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(ctrl, text="Start").grid(row=r, column=2, sticky="w", padx=4)
        self.e_start = ttk.Entry(ctrl, width=12)
        self.e_start.grid(row=r, column=3, sticky="w", padx=4)

        ttk.Label(ctrl, text="End").grid(row=r, column=4, sticky="w", padx=4)
        self.e_end = ttk.Entry(ctrl, width=12)
        self.e_end.grid(row=r, column=5, sticky="w", padx=4)

        ttk.Label(ctrl, text="Side").grid(row=r, column=6, sticky="w", padx=4)
        self.side = tk.StringVar(value="long_short")
        self.dd_side = ttk.Combobox(ctrl, textvariable=self.side, values=["long_only","short_only","long_short"], width=12, state="readonly")
        self.dd_side.grid(row=r, column=7, sticky="w", padx=4, pady=4)

        ttk.Label(ctrl, text="Execution").grid(row=r, column=8, sticky="w", padx=4)
        self.execution = tk.StringVar(value="next_open")
        self.dd_exec = ttk.Combobox(ctrl, textvariable=self.execution, values=["next_open","next_close"], width=10, state="readonly")
        self.dd_exec.grid(row=r, column=9, sticky="w", padx=4, pady=4)

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

        ttk.Label(ctrl, text="Output root").grid(row=r, column=6, sticky="w", padx=4, pady=4)
        self.e_outdir = ttk.Entry(ctrl, textvariable=self.outdir_root, width=30)
        self.e_outdir.grid(row=r, column=7, columnspan=2, sticky="we", padx=4)
        ttk.Button(ctrl, text="Choose", command=self.choose_outdir).grid(row=r, column=9, sticky="w", padx=4)
        ttk.Button(ctrl, text="Run", command=self.run_async).grid(row=r, column=10, sticky="we", padx=4)
        ttk.Button(ctrl, text="Stop", command=self.stop_runs).grid(row=r, column=11, sticky="we", padx=4)

        tickers_frame = ttk.LabelFrame(left, text="Tickers")
        tickers_frame.pack(fill="both", expand=False, padx=8, pady=(0,8))
        self.search_widget = TickerSearchFrame(tickers_frame, add_callback=self._add_to_selected)
        self.search_widget.pack(fill="both", expand=True)

        sel_frame = ttk.Frame(tickers_frame)
        sel_frame.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Label(sel_frame, text="Selected").pack(anchor="w")
        self.lb_selected = tk.Listbox(sel_frame, selectmode="extended", height=8)
        self.lb_selected.pack(fill="both", expand=True)
        btns = ttk.Frame(tickers_frame)
        btns.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(btns, text="Remove", command=self._remove_selected_tickers).pack(side="left", padx=4)
        ttk.Button(btns, text="Clear", command=self._clear_selected_tickers).pack(side="left", padx=4)

        prog = ttk.Frame(left)
        prog.pack(fill="x", padx=8, pady=(0,8))
        self.pb = ttk.Progressbar(prog, variable=self.progress_var, maximum=100)
        self.pb.pack(fill="x", padx=4, pady=4)
        self.status = ttk.Label(prog, textvariable=self.status_var)
        self.status.pack(anchor="w", padx=4)

        theme_frame = ttk.LabelFrame(left, text="Theme")
        theme_frame.pack(fill="x", padx=8, pady=(0,8))
        if use_bootstrap:
            themes = ["darkly","cyborg","vapor","superhero","solar","morph","flatly","journal","lumen","minty","pulse","sandstone","simplex","sketchy","yeti","cosmo","cerulean","litera"]
            self.dd_theme = ttk.Combobox(theme_frame, values=themes, textvariable=self.theme_var, state="readonly", width=16)
            self.dd_theme.pack(side="left", padx=6, pady=6)
            ttk.Button(theme_frame, text="Apply", command=self._apply_theme).pack(side="left", padx=6)
        else:
            ttk.Label(theme_frame, text="Install ttkbootstrap for theming").pack(side="left", padx=6, pady=6)

        hist = ttk.LabelFrame(left, text="Run History")
        hist.pack(fill="both", expand=True, padx=8, pady=(0,8))
        cols = ("timestamp","ticker","CAGR","Sharpe","MaxDD","base","folder")
        self.hist_tree = ttk.Treeview(hist, columns=cols, show="headings", height=10)
        for c in cols:
            self.hist_tree.heading(c, text=c)
            self.hist_tree.column(c, width=90 if c not in ("base","folder") else 180, anchor="w")
        self.hist_tree.pack(fill="both", expand=True)
        self.hist_tree.bind("<Double-1>", self._open_selected_run)
        ttk.Button(hist, text="Refresh", command=self._refresh_history).pack(anchor="e", padx=6, pady=6)

        self.plot_box = ttk.Notebook(right)
        self.plot_box.pack(fill="both", expand=True, padx=8, pady=8)
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

        self.metrics_box = ttk.LabelFrame(right, text="Metrics")
        self.metrics_box.pack(side="bottom", fill="x", padx=8, pady=(0,8))
        self.metrics_text = tk.Text(self.metrics_box, height=4)
        self.metrics_text.pack(fill="x")

    def _apply_theme(self):
        if use_bootstrap:
            self.style.theme_use(self.theme_var.get())

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
        path = filedialog.askdirectory(title="Select Output Root Folder")
        if path:
            self.outdir_root.set(path)
            self._refresh_history()

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

    def _add_to_selected(self, tickers):
        for t in tickers:
            if t not in self.selected_tickers:
                self.selected_tickers.append(t)
                self.lb_selected.insert("end", t)

    def _remove_selected_tickers(self):
        sel_indices = list(self.lb_selected.curselection())
        sel_indices.reverse()
        for i in sel_indices:
            t = self.lb_selected.get(i)
            self.lb_selected.delete(i)
            if t in self.selected_tickers:
                self.selected_tickers.remove(t)

    def _clear_selected_tickers(self):
        self.lb_selected.delete(0, "end")
        self.selected_tickers.clear()

    def _valid_date(self, s: str) -> bool:
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except Exception:
            return False

    def run_async(self):
        if self.executor_thread and self.executor_thread.is_alive():
            messagebox.showwarning("Busy", "A run is already in progress")
            return
        if not self.outdir_root.get().strip():
            messagebox.showerror("Error", "Choose an output root folder")
            return
        tickers = list(self.selected_tickers) if self.selected_tickers else []
        if not tickers:
            messagebox.showerror("Error", "Select at least one ticker")
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
        self.stop_flag.clear()
        args = dict(period=period, start=start, end=end)
        self.executor_thread = threading.Thread(target=self._run_batch, args=(tickers, args), daemon=True)
        self.executor_thread.start()

    def stop_runs(self):
        self.stop_flag.set()
        self.status_var.set("Stopping...")

    def _run_batch(self, tickers, args):
        n = len(tickers)
        for idx, t in enumerate(tickers, 1):
            if self.stop_flag.is_set():
                break
            self.queue.put(("status", f"Running {t} ({idx}/{n})"))
            try:
                self._run_single(t, **args)
            except Exception as e:
                self.queue.put(("status", f"Error {t}: {e}"))
            pct = idx / n * 100.0
            self.queue.put(("progress", pct))
        self.queue.put(("status", "Idle"))
        self.queue.put(("refresh_history", None))

    def _collect_inputs(self, ticker, start, end, period):
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "ticker": ticker,
            "period": period,
            "start": start,
            "end": end,
            "side": self.side.get(),
            "execution": self.execution.get(),
            "ema_len": int(self.s_EMA.get()),
            "atr_len": int(self.s_ATR.get()),
            "multiplier": float(self.s_Multiplier.get()),
            "risk_per_trade": float(self.s_Risk.get()),
            "atr_stop_mult": float(self.s_Stop_x_ATR.get()),
            "take_profit_mult_enabled": self.tp_enable.get(),
            "take_profit_mult": float(self.tp_scale.get()) if self.tp_enable.get() else None,
            "fee_bps": float(self.e_fee.get()),
            "slip_bps": float(self.e_slip.get()),
            "warmup_override": int(self.e_warm.get()),
        }

    def _ensure_ticker_folder(self, ticker):
        root = self.outdir_root.get().strip()
        folder = os.path.join(root, ticker.upper())
        os.makedirs(folder, exist_ok=True)
        return folder

    def _save_params_and_metrics(self, outdir, base, params, metrics):
        with open(os.path.join(outdir, f"{base}_params.json"), "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2)
        with open(os.path.join(outdir, f"{base}_metrics.json"), "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        pd.DataFrame([metrics]).to_csv(os.path.join(outdir, f"{base}_metrics.csv"), index=False)
        registry_csv = os.path.join(outdir, "runs_log.csv")
        row = {**{"base": base, "folder": outdir}, **params, **metrics}
        df_row = pd.DataFrame([row])
        if os.path.exists(registry_csv):
            try:
                old = pd.read_csv(registry_csv)
                pd.concat([old, df_row], ignore_index=True).to_csv(registry_csv, index=False)
            except Exception:
                df_row.to_csv(registry_csv, index=False)
        else:
            df_row.to_csv(registry_csv, index=False)
        with open(os.path.join(outdir, f"{base}_summary.txt"), "w", encoding="utf-8") as f:
            f.write(f"Run: {base}\n")
            f.write(f"Timestamp: {params['timestamp']}\n")
            f.write("Parameters:\n")
            for k, v in params.items():
                f.write(f"  {k}: {v}\n")
            f.write("\nMetrics:\n")
            for k, v in metrics.items():
                f.write(f"  {k}: {v}\n")

    def _export_pdf(self, outdir, base, params, metrics, kc_df, equity_series, dd_series, trades_df):
        pdf_path = os.path.join(outdir, f"{base}_report.pdf")
        with PdfPages(pdf_path) as pdf:
            fig1 = plt.figure(figsize=(10,6))
            ax1 = fig1.add_subplot(111)
            ax1.plot(kc_df.index, kc_df["Close"], label="Close")
            ax1.plot(kc_df.index, kc_df["KC_Middle"], label="KC Mid")
            ax1.plot(kc_df.index, kc_df["KC_Upper"], label="KC Upper")
            ax1.plot(kc_df.index, kc_df["KC_Lower"], label="KC Lower")
            ax1.set_title(f"{params['ticker']} Price and Keltner")
            ax1.legend(loc="best")
            pdf.savefig(fig1, bbox_inches="tight")
            plt.close(fig1)

            fig2 = plt.figure(figsize=(10,6))
            ax2 = fig2.add_subplot(111)
            ax2.plot(equity_series.index, equity_series.values, label="Equity")
            ax2.set_title("Equity Curve")
            ax2.legend(loc="best")
            pdf.savefig(fig2, bbox_inches="tight")
            plt.close(fig2)

            fig3 = plt.figure(figsize=(10,3))
            ax3 = fig3.add_subplot(111)
            ax3.fill_between(dd_series.index, dd_series.values, 0, step="pre")
            ax3.set_title("Drawdown")
            pdf.savefig(fig3, bbox_inches="tight")
            plt.close(fig3)

            fig4 = plt.figure(figsize=(10,6))
            fig4.suptitle("Parameters and Metrics", y=0.98)
            ax4 = fig4.add_subplot(211)
            ax4.axis("off")
            ptext = "\n".join([f"{k}: {v}" for k, v in params.items()])
            ax4.text(0, 1, ptext, va="top", family="monospace")
            ax5 = fig4.add_subplot(212)
            ax5.axis("off")
            mtext = "\n".join([f"{k}: {v}" for k, v in metrics.items()])
            ax5.text(0, 1, mtext, va="top", family="monospace")
            pdf.savefig(fig4, bbox_inches="tight")
            plt.close(fig4)

            if trades_df is not None and not trades_df.empty:
                cols = list(trades_df.columns)
                head = trades_df.head(25).copy()
                fig5 = plt.figure(figsize=(11, min(10, 2 + 0.35*len(head))))
                ax5t = fig5.add_subplot(111)
                ax5t.axis("off")
                tbl = ax5t.table(cellText=head.values, colLabels=cols, loc="center")
                tbl.auto_set_font_size(False)
                tbl.set_fontsize(8)
                tbl.scale(1, 1.2)
                ax5t.set_title("Trades (first 25)")
                pdf.savefig(fig5, bbox_inches="tight")
                plt.close(fig5)
        return pdf_path

    def _run_single(self, ticker, period=None, start=None, end=None):
        folder = self._ensure_ticker_folder(ticker)
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
        df = fetch_ohlc(ticker, start=start, end=end, period=period)
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
        base = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        kc_out = kc.copy()
        kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
        kc_csv = os.path.join(folder, f"{base}_kc.csv")
        trades_csv = os.path.join(folder, f"{base}_trades.csv")
        kc_out.to_csv(kc_csv)
        res["trades"].to_csv(trades_csv, index=False)
        met = res["metrics"]
        metrics_clean = {k: (float(v) if hasattr(v, "__float__") else v) for k, v in met.items()}
        params = self._collect_inputs(ticker, start, end, period)
        self._save_params_and_metrics(folder, base, params, metrics_clean)
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
        self.fig_price.savefig(os.path.join(folder, f"{base}_kc.png"), dpi=150, bbox_inches="tight")
        self.fig_equity.savefig(os.path.join(folder, f"{base}_equity.png"), dpi=150, bbox_inches="tight")
        self.fig_dd.savefig(os.path.join(folder, f"{base}_drawdown.png"), dpi=150, bbox_inches="tight")
        txt = (
            f"CAGR {met['CAGR']:.2%}  |  Sharpe {met['Sharpe']:.2f}  |  "
            f"Sortino {met['Sortino']:.2f}  |  MaxDD {met['MaxDrawdown']:.2%}  |  "
            f"Exposure {met['Exposure']:.2%}  |  Trades {met['NumTrades']}\n"
            f"Saved to: {folder}"
        )
        self.metrics_text.delete("1.0", "end")
        self.metrics_text.insert("end", txt)
        pdf_path = self._export_pdf(folder, base, params, metrics_clean, kc_out, curve, dd, res["trades"])
        self.queue.put(("status", f"Saved {base} | PDF {os.path.basename(pdf_path)}"))

    def _process_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                kind, payload = item
                if kind == "status":
                    self.status_var.set(payload)
                elif kind == "progress":
                    self.progress_var.set(float(payload))
                elif kind == "refresh_history":
                    self._refresh_history()
        except queue.Empty:
            pass
        self.after(120, self._process_queue)

    def _refresh_history(self):
        self.hist_tree.delete(*self.hist_tree.get_children())
        root = self.outdir_root.get().strip()
        if not root or not os.path.isdir(root):
            return
        for ticker in sorted(os.listdir(root)):
            tpath = os.path.join(root, ticker)
            if not os.path.isdir(tpath):
                continue
            log = os.path.join(tpath, "runs_log.csv")
            if not os.path.exists(log):
                continue
            try:
                df = pd.read_csv(log)
            except Exception:
                continue
            cols = ["timestamp","ticker","CAGR","Sharpe","MaxDrawdown","base","folder"]
            for _, row in df.iterrows():
                ts = row.get("timestamp", "")
                tk_ = row.get("ticker", ticker)
                cagr = row.get("CAGR", "")
                shrp = row.get("Sharpe", "")
                mdd = row.get("MaxDrawdown", "")
                base = row.get("base", "")
                folder = row.get("folder", tpath)
                self.hist_tree.insert("", "end", values=(ts, tk_, cagr, shrp, mdd, base, folder))
        for c in ("CAGR","Sharpe","MaxDD"):
            if c in self.hist_tree["columns"]:
                pass

    def _open_selected_run(self, _evt=None):
        sel = self.hist_tree.selection()
        if not sel:
            return
        item = self.hist_tree.item(sel[0])
        vals = item.get("values", [])
        if len(vals) < 7:
            return
        base = vals[5]
        folder = vals[6]
        pdf = os.path.join(folder, f"{base}_report.pdf")
        summ = os.path.join(folder, f"{base}_summary.txt")
        path = pdf if os.path.exists(pdf) else summ if os.path.exists(summ) else folder
        try:
            if os.path.isdir(path):
                webbrowser.open(path)
            else:
                webbrowser.open(f"file://{os.path.abspath(path)}")
        except Exception:
            pass


if __name__ == "__main__":
    app = KCBacktestApp()
    app.mainloop()
