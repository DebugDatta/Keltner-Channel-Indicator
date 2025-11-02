Here’s your updated file, no extra changes beyond light and dark modes, PDF export with inputs metrics and graphs, and per ticker subfolder creation.

```python
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
        self.theme = tk.StringVar(value="light")
        self._build_ui()
        self._init_plots()
        self._init_theme_engine()
        self._apply_theme()
        self._last_run_info = None  # {'run_dir': str, 'base': str}

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

        # Theme control and buttons
        ttk.Label(ctrl, text="Theme").grid(row=r, column=10, sticky="w", padx=4)
        self.dd_theme = ttk.Combobox(ctrl, textvariable=self.theme, values=["light","dark"], width=8, state="readonly")
        self.dd_theme.grid(row=r, column=11, sticky="w", padx=4)
        self.dd_theme.bind("<<ComboboxSelected>>", lambda e: self._apply_theme())

        r += 1
        ttk.Button(ctrl, text="Choose Folder", command=self.choose_outdir).grid(row=r, column=6, sticky="w", padx=4)
        ttk.Button(ctrl, text="Run Backtest", command=self.run).grid(row=r, column=7, sticky="we", padx=4)
        ttk.Button(ctrl, text="Export PDF", command=self.export_pdf).grid(row=r, column=8, sticky="we", padx=4)

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

    def _collect_inputs(self, ticker, start, end, period):
        inputs = {
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
        return inputs

    def _save_params_and_metrics(self, outdir, base, params, metrics):
        params_path = os.path.join(outdir, f"{base}_params.json")
        metrics_path = os.path.join(outdir, f"{base}_metrics.json")
        with open(params_path, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2)
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        met_csv = os.path.join(outdir, f"{base}_metrics.csv")
        pd.DataFrame([metrics]).to_csv(met_csv, index=False)
        # keep registry at root chosen folder for overview of all runs
        registry_csv = os.path.join(os.path.dirname(outdir), "runs_log.csv") if os.path.basename(outdir) else os.path.join(outdir, "runs_log.csv")
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
        root_outdir = self.outdir.get().strip()
        if not root_outdir:
            messagebox.showerror("Error", "Choose an output folder")
            return

        # per ticker subfolder
        run_dir = os.path.join(root_outdir, ticker)
        os.makedirs(run_dir, exist_ok=True)

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
        base = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        kc_out = kc.copy()
        kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
        kc_csv = os.path.join(run_dir, f"{base}_kc.csv")
        trades_csv = os.path.join(run_dir, f"{base}_trades.csv")
        kc_out.to_csv(kc_csv)
        res["trades"].to_csv(trades_csv, index=False)
        met = res["metrics"]
        metrics_clean = {k: (float(v) if hasattr(v, "__float__") else v) for k, v in met.items()}
        txt = (
            f"CAGR {met['CAGR']:.2%}  |  Sharpe {met['Sharpe']:.2f}  |  "
            f"Sortino {met['Sortino']:.2f}  |  MaxDD {met['MaxDrawdown']:.2%}  |  "
            f"Exposure {met['Exposure']:.2%}  |  Trades {met['NumTrades']}\n"
            f"Saved to: {run_dir}"
        )
        self.metrics_text.delete("1.0", "end")
        self.metrics_text.insert("end", txt)
        self._clear_plots()
        self._apply_mpl_colors()  # ensure plots follow current theme

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

        # remember last run
        self._last_run_info = {"run_dir": run_dir, "base": base, "params": params, "metrics": metrics_clean}
        messagebox.showinfo("Done", f"Backtest complete.\nFiles saved in:\n{run_dir}")

    def export_pdf(self):
        if not self._last_run_info:
            messagebox.showerror("Error", "Run a backtest first")
            return
        run_dir = self._last_run_info["run_dir"]
        base = self._last_run_info["base"]
        params = self._last_run_info["params"]
        metrics = self._last_run_info["metrics"]
        pdf_path = os.path.join(run_dir, f"{base}_report.pdf")

        # first page with inputs and metrics as text
        page = Figure(figsize=(8.27, 11.69))  # A4 portrait in inches
        ax = page.add_subplot(111)
        ax.axis("off")

        def fmt_block(title, d):
            lines = [title]
            for k, v in d.items():
                lines.append(f"{k}: {v}")
            return "\n".join(lines)

        txt = f"Run: {base}\nTimestamp: {params['timestamp']}\n\n"
        txt += fmt_block("Parameters", params) + "\n\n"
        txt += fmt_block("Metrics", metrics)

        page.text(0.05, 0.95, "Keltner Channel Backtest Report", fontsize=16, va="top", ha="left", weight="bold")
        page.text(0.05, 0.90, txt, fontsize=9, va="top", ha="left", family="monospace")

        # save multipage pdf
        with PdfPages(pdf_path) as pp:
            # ensure mpl colors match current theme for the text page too
            self._set_fig_facecolors(page)
            pp.savefig(page, bbox_inches="tight")
            self._set_fig_facecolors(self.fig_price)
            pp.savefig(self.fig_price, bbox_inches="tight")
            self._set_fig_facecolors(self.fig_equity)
            pp.savefig(self.fig_equity, bbox_inches="tight")
            self._set_fig_facecolors(self.fig_dd)
            pp.savefig(self.fig_dd, bbox_inches="tight")

        messagebox.showinfo("PDF Exported", f"Report saved to:\n{pdf_path}")

    @staticmethod
    def _valid_date(s: str) -> bool:
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return True
        except Exception:
            return False

    # Theme support
    def _init_theme_engine(self):
        self._colors = {
            "light": {
                "bg": "#F5F5F5",
                "fg": "#000000",
                "input_bg": "#FFFFFF",
                "input_fg": "#000000",
                "frame_bg": "#F5F5F5",
                "accent": "#1a73e8",
                "plot_bg": "#FFFFFF",
                "axes_fg": "#000000",
                "grid": "#E0E0E0",
                "text_bg": "#FFFFFF",
                "text_fg": "#000000",
                "tab_bg": "#EDEDED",
                "tab_fg": "#000000",
            },
            "dark": {
                "bg": "#202124",
                "fg": "#E8EAED",
                "input_bg": "#2B2C2F",
                "input_fg": "#E8EAED",
                "frame_bg": "#202124",
                "accent": "#8AB4F8",
                "plot_bg": "#121212",
                "axes_fg": "#E8EAED",
                "grid": "#3C4043",
                "text_bg": "#2B2C2F",
                "text_fg": "#E8EAED",
                "tab_bg": "#303134",
                "tab_fg": "#E8EAED",
            },
        }
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

    def _apply_theme(self):
        t = self.theme.get()
        c = self._colors[t]

        # root
        self.configure(bg=c["bg"])
        for w in self.winfo_children():
            try:
                w.configure(style="TFrame")
            except Exception:
                pass

        # ttk styles
        self.style.configure("TFrame", background=c["frame_bg"])
        self.style.configure("TLabelframe", background=c["frame_bg"], foreground=c["fg"])
        self.style.configure("TLabelframe.Label", background=c["frame_bg"], foreground=c["fg"])
        self.style.configure("TLabel", background=c["frame_bg"], foreground=c["fg"])
        self.style.configure("TButton", foreground=c["fg"])
        self.style.configure("TCombobox", fieldbackground=c["input_bg"], foreground=c["input_fg"], background=c["input_bg"])
        self.style.map("TButton", foreground=[("active", c["fg"])])
        self.style.configure("TNotebook", background=c["tab_bg"])
        self.style.configure("TNotebook.Tab", background=c["tab_bg"], foreground=c["tab_fg"])

        # tk widgets
        self.metrics_text.configure(bg=c["text_bg"], fg=c["text_fg"], insertbackground=c["text_fg"])

        # entries that are tk.Entry within ttk.Entry are fine, no extra set

        # matplotlib figures
        self._apply_mpl_colors()

        # redraw canvases
        self.canvas_price.draw()
        self.canvas_equity.draw()
        self.canvas_dd.draw()

    def _set_fig_facecolors(self, fig: Figure):
        c = self._colors[self.theme.get()]
        fig.set_facecolor(c["frame_bg"])
        for ax in fig.axes:
            ax.set_facecolor(c["plot_bg"])
            ax.tick_params(colors=c["axes_fg"])
            for spine in ax.spines.values():
                spine.set_color(c["axes_fg"])
            grid_color = c["grid"]
            ax.grid(True, color=grid_color, alpha=0.4)

            # update text colors
            if ax.title:
                ax.title.set_color(c["axes_fg"])
            ax.xaxis.label.set_color(c["axes_fg"])
            ax.yaxis.label.set_color(c["axes_fg"])
            leg = ax.get_legend()
            if leg:
                for text in leg.get_texts():
                    text.set_color(c["axes_fg"])

    def _apply_mpl_colors(self):
        # apply to existing figs
        self._set_fig_facecolors(self.fig_price)
        self._set_fig_facecolors(self.fig_equity)
        self._set_fig_facecolors(self.fig_dd)

if __name__ == "__main__":
    app = KCBacktestApp()
    app.mainloop()
```
