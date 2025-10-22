from __future__ import annotations
import argparse, os
from data import fetch_ohlc
from indicators import keltner_channel
from strategy import breakout_signals
from backtester import run_backtest, BTParams
from plotting import plot_price_kc, plot_equity, plot_drawdown

def ask(prompt, default=None, cast=str, valid_range=None, choices=None):
    """Safe user input with validation"""
    while True:
        s = input(f"{prompt} [{default}]: ").strip()
        if s == "" and default is not None:
            return default
        try:
            val = cast(s)
            if choices and val not in choices:
                print(f"Choose one of: {choices}")
                continue
            if valid_range:
                lo, hi = valid_range
                if val < lo or val > hi:
                    print(f"Enter a value between {lo} and {hi}")
                    continue
            return val
        except Exception:
            print("Invalid input, try again.")

def interactive_inputs():
    print("\nINTERACTIVE MODE — PRESS ENTER TO ACCEPT DEFAULTS\n")
    cfg = {}

    cfg["ticker"] = ask("Ticker symbol (e.g. AAPL, BTC-USD, RELIANCE.NS)", "AAPL", str)

    use_period = ask("Use period instead of start/end? (yes/no)", "yes", str).lower().startswith("y")
    if use_period:
        cfg["period"] = ask("Period (valid: 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max)", "5y", str)
        cfg["start"], cfg["end"] = None, None
    else:
        cfg["period"] = None
        cfg["start"] = ask("Start date (YYYY-MM-DD)", "2018-01-01", str)
        cfg["end"] = ask("End date (YYYY-MM-DD or leave blank)", "", str) or None

    print("\n--- INDICATOR PARAMETERS ---")
    cfg["ema"] = ask("EMA periods (typical 10–50)", 20, int, valid_range=(5, 200))
    cfg["atr"] = ask("ATR periods (typical 5–30)", 10, int, valid_range=(5, 100))
    cfg["mult"] = ask("ATR multiplier (1.5–4.0 typical)", 2.0, float, valid_range=(1.0, 5.0))

    print("\n--- RISK & TRADE SETTINGS ---")
    cfg["risk"] = ask("Risk per trade as fraction of capital (0.005–0.05 typical)", 0.01, float, valid_range=(0.001, 0.1))
    cfg["stop"] = ask("Stop loss multiple of ATR (1.0–5.0 typical)", 2.0, float, valid_range=(0.5, 10.0))
    tp_str = ask("Take profit multiple of ATR (blank for None)", "", str)
    cfg["tp"] = float(tp_str) if tp_str else None

    cfg["side"] = ask("Trade side (choose): long_only / short_only / long_short", "long_short", str,
                      choices=["long_only", "short_only", "long_short"])

    cfg["execution"] = ask("Execution mode (choose): next_open / next_close", "next_open", str,
                           choices=["next_open", "next_close"])

    print("\n--- COST SETTINGS ---")
    cfg["fee_bps"] = ask("Transaction cost per side in bps (0–50 typical, 1bps=0.01%)", 1.0, float, valid_range=(0, 100))
    cfg["slip_bps"] = ask("Slippage per side in bps (0–50 typical)", 2.0, float, valid_range=(0, 100))

    print("\n--- MISC SETTINGS ---")
    cfg["warmup"] = ask("Warmup bars (0=auto, typical 20–100)", 0, int, valid_range=(0, 300)) or None
    cfg["outdir"] = ask("Output folder name", "out", str)
    print()
    return cfg

def parse_args():
    ap = argparse.ArgumentParser(description="Keltner Channel Backtest Tool")
    ap.add_argument("--ticker")
    ap.add_argument("--period", default=None)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--ema", type=int, default=20)
    ap.add_argument("--atr", type=int, default=10)
    ap.add_argument("--mult", type=float, default=2.0)
    ap.add_argument("--risk", type=float, default=0.01)
    ap.add_argument("--stop", type=float, default=2.0)
    ap.add_argument("--tp", type=float, default=None)
    ap.add_argument("--side", choices=["long_only","short_only","long_short"], default="long_short")
    ap.add_argument("--execution", choices=["next_open","next_close"], default="next_open")
    ap.add_argument("--fee_bps", type=float, default=1.0)
    ap.add_argument("--slip_bps", type=float, default=2.0)
    ap.add_argument("--warmup", type=int, default=None)
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--interactive", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()
    if args.interactive or not args.ticker:
        cfg = interactive_inputs()
    else:
        cfg = vars(args)
        if not cfg["warmup"]:
            cfg["warmup"] = max(cfg["ema"], cfg["atr"])

    os.makedirs(cfg["outdir"], exist_ok=True)

    df = fetch_ohlc(cfg["ticker"], start=cfg["start"], end=cfg["end"], period=cfg["period"])
    kc = keltner_channel(df, ema_len=cfg["ema"], atr_len=cfg["atr"], mult=cfg["mult"])
    sig = breakout_signals(kc)

    bt = BTParams(
        execution=cfg["execution"],
        initial_capital=100000.0,
        side=cfg["side"],
        fee_bps=cfg["fee_bps"],
        slip_bps=cfg["slip_bps"],
        risk_per_trade=cfg["risk"],
        atr_stop_mult=cfg["stop"],
        take_profit_mult=cfg["tp"],
        warmup_bars=cfg["warmup"] if cfg["warmup"] else max(cfg["ema"], cfg["atr"]),
        max_leverage=1.0,
    )

    res = run_backtest(kc, sig, bt)

    base, outdir = cfg["ticker"], cfg["outdir"]
    kc_out = kc.copy()
    kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
    kc_out.to_csv(os.path.join(outdir, f"{base}_kc.csv"))
    res["trades"].to_csv(os.path.join(outdir, f"trades_{base}.csv"), index=False)

    plot_equity(res["equity"], base, os.path.join(outdir, f"{base}_equity.png"))
    plot_drawdown(res["equity"], base, os.path.join(outdir, f"{base}_drawdown.png"))
    plot_price_kc(kc, base, os.path.join(outdir, f"{base}_kc.png"), trades=res["trades"])

    print("Metrics:", res["metrics"])
    print("Saved outputs in:", outdir)

if __name__ == "__main__":
    main()
