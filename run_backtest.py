from __future__ import annotations
import argparse, os
from data import fetch_ohlc, interval_limit
from indicators import keltner_channel
from strategy import keltner_signals

__all__ = ["main", "interactive_inputs", "parse_args"]
from backtester import run_backtest, BTParams, run_buy_and_hold
from plotting import plot_price_kc, plot_equity, plot_drawdown

def ask(prompt, default=None, cast=str, valid_range=None, choices=None):
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

    cfg["ticker"] = ask("Ticker symbol", "AAPL", str)

    use_period = ask("Use period instead of start/end? (yes/no)", "yes", str).lower().startswith("y")
    if use_period:
        cfg["period"] = ask("Period (1mo,3mo,6mo,1y,2y,5y,10y,max)", "5y", str)
        cfg["start"], cfg["end"] = None, None
    else:
        cfg["period"] = None
        cfg["start"] = ask("Start date (YYYY-MM-DD)", "2018-01-01", str)
        cfg["end"] = ask("End date (YYYY-MM-DD or blank)", "", str) or None

    cfg["interval"] = ask(
        "Interval (1m,2m,5m,15m,30m,1h,1d,1wk,1mo)",
        "1d",
        str,
        choices=["1m","2m","5m","15m","30m","1h","1d","1wk","1mo"]
    )
    lim = interval_limit(cfg["interval"])
    print(f"Max lookback for {cfg['interval']} is {lim['period_hint']}  {lim['note']}")

    print("\n--- INDICATOR PARAMETERS ---")
    cfg["ema"] = ask("EMA periods", 20, int, valid_range=(5, 200))
    cfg["atr"] = ask("ATR periods", 10, int, valid_range=(5, 100))
    cfg["mult"] = ask("ATR multiplier", 2.0, float, valid_range=(1.0, 5.0))

    print("\n--- STRATEGY ---")
    cfg["strategy"] = ask(
        "Strategy (momentum / mean_reversion / percentb / pullback / regime_switch)",
        "momentum",
        str,
        choices=["momentum","mean_reversion","percentb","pullback","regime_switch"]
    )

    print("\n--- RISK & TRADE SETTINGS ---")
    cfg["risk"] = ask("Risk per trade fraction", 0.01, float, valid_range=(0.001, 0.1))
    cfg["stop"] = ask("Stop loss x ATR", 2.0, float, valid_range=(0.5, 10.0))
    tp_str = ask("Take profit x ATR (blank for None)", "", str)
    cfg["tp"] = float(tp_str) if tp_str else None

    cfg["side"] = ask(
        "Trade side: long_only / short_only / long_short",
        "long_short",
        str,
        choices=["long_only", "short_only", "long_short"]
    )

    cfg["execution"] = ask(
        "Execution: next_open / next_close",
        "next_open",
        str,
        choices=["next_open", "next_close"]
    )

    print("\n--- COST SETTINGS ---")
    cfg["fee_bps"] = ask("Fees per side bps", 1.0, float, valid_range=(0, 100))
    cfg["slip_bps"] = ask("Slippage per side bps", 2.0, float, valid_range=(0, 100))

    print("\n--- MISC SETTINGS ---")
    cfg["warmup"] = ask("Warmup bars (0=auto)", 0, int, valid_range=(0, 300)) or None
    cfg["outdir"] = ask("Output folder name", "out", str)

    print("\n--- CAPITAL & LEVERAGE ---")
    cfg["capital"] = ask("Initial capital ($)", 100000.0, float, valid_range=(1000, 10000000))
    cfg["max_leverage"] = ask("Max leverage", 1.0, float, valid_range=(1.0, 5.0))

    print("\n--- ADVANCED STRATEGY ---")
    cfg["trend_ema"] = ask("Trend EMA length", 200, int, valid_range=(20, 500))
    if cfg["strategy"] == "percentb":
        cfg["pb_low"] = ask("PercentB low threshold", 0.20, float, valid_range=(0.00, 0.50))
        cfg["pb_high"] = ask("PercentB high threshold", 0.80, float, valid_range=(0.50, 1.00))
    else:
        cfg["pb_low"] = 0.20
        cfg["pb_high"] = 0.80

    print("\n--- EXITS ---")
    ts_str = ask("Enable trailing stop? (yes/no)", "no", str).lower().startswith("y")
    cfg["trailing_stop"] = ts_str
    if ts_str:
        cfg["trailing_atr_mult"] = ask("Trailing stop x ATR", 2.5, float, valid_range=(0.5, 10.0))
    else:
        cfg["trailing_atr_mult"] = 2.5

    print("\n--- BENCHMARK ---")
    cfg["bh"] = ask("Run Buy & Hold benchmark? (yes/no)", "no", str).lower().startswith("y")

    print()
    return cfg

def parse_args():
    ap = argparse.ArgumentParser(description="Keltner Channel Backtest Tool")
    ap.add_argument("--ticker")
    ap.add_argument("--period", default=None)
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--interval", default="1d",
                    choices=["1m","2m","5m","15m","30m","1h","1d","1wk","1mo"])
    ap.add_argument("--ema", type=int, default=20)
    ap.add_argument("--atr", type=int, default=10)
    ap.add_argument("--mult", type=float, default=2.0)
    ap.add_argument("--strategy", choices=["momentum","mean_reversion","percentb","pullback","regime_switch"], default="momentum")
    ap.add_argument("--risk", type=float, default=0.01)
    ap.add_argument("--stop", type=float, default=2.0)
    ap.add_argument("--tp", type=float, default=None)
    ap.add_argument("--side", choices=["long_only","short_only","long_short"], default="long_short")
    ap.add_argument("--execution", choices=["next_open","next_close"], default="next_open")
    ap.add_argument("--fee_bps", type=float, default=1.0)
    ap.add_argument("--slip_bps", type=float, default=2.0)
    ap.add_argument("--warmup", type=int, default=None)
    ap.add_argument("--capital", type=float, default=100000.0)
    ap.add_argument("--max-leverage", type=float, default=1.0)
    ap.add_argument("--pb-low", type=float, default=0.20)
    ap.add_argument("--pb-high", type=float, default=0.80)
    ap.add_argument("--trend-ema", type=int, default=200)
    ap.add_argument("--trailing-stop", action="store_true")
    ap.add_argument("--trailing-atr-mult", type=float, default=2.5)
    ap.add_argument("--bh", action="store_true", help="Also run Buy & Hold benchmark")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--interactive", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()
    if args.interactive or not args.ticker:
        cfg = interactive_inputs()
    else:
        cfg = vars(args)
        lim = interval_limit(cfg["interval"])
        print(f"[info] Interval {cfg['interval']} max lookback {lim['period_hint']}  {lim['note']}")
        if not cfg["warmup"]:
            cfg["warmup"] = max(cfg["ema"], cfg["atr"])

    os.makedirs(cfg["outdir"], exist_ok=True)

    df = fetch_ohlc(
        cfg["ticker"],
        start=cfg["start"],
        end=cfg["end"],
        period=cfg["period"],
        interval=cfg["interval"]
    )
    kc = keltner_channel(df, ema_len=cfg["ema"], atr_len=cfg["atr"], mult=cfg["mult"])

    sig_kwargs = {}
    if cfg["strategy"] == "percentb":
        sig_kwargs = {"low": cfg["pb_low"], "high": cfg["pb_high"]}
    if cfg["strategy"] == "pullback":
        sig_kwargs = {"slope_len": 20}
    if cfg["strategy"] == "regime_switch":
        sig_kwargs = {"slope_len": 20, "strong_mult": 1.0, "trend_ema_len": cfg["trend_ema"]}
    if cfg["strategy"] in ("momentum", "breakout", "trend"):
        sig_kwargs = {"trend_ema_len": cfg["trend_ema"]}

    sig = keltner_signals(kc, mode=cfg["strategy"], **sig_kwargs)

    bt = BTParams(
        execution=cfg["execution"],
        initial_capital=cfg["capital"],
        side=cfg["side"],
        fee_bps=cfg["fee_bps"],
        slip_bps=cfg["slip_bps"],
        risk_per_trade=cfg["risk"],
        atr_stop_mult=cfg["stop"],
        take_profit_mult=cfg["tp"],
        warmup_bars=cfg["warmup"] if cfg["warmup"] else max(cfg["ema"], cfg["atr"]),
        max_leverage=cfg["max_leverage"],
        trailing_stop=cfg.get("trailing_stop", False),
        trailing_atr_mult=cfg.get("trailing_atr_mult", 2.5),
    )

    res = run_backtest(kc, sig, bt)

    bh_res = None
    if cfg.get("bh"):
        bh_res = run_buy_and_hold(df, initial_capital=cfg["capital"])

    base, outdir = cfg["ticker"], cfg["outdir"]
    kc_out = kc.copy()
    kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
    kc_out.to_csv(os.path.join(outdir, f"{base}_kc.csv"))
    res["trades"].to_csv(os.path.join(outdir, f"trades_{base}.csv"), index=False)

    plot_equity(res["equity"], base, os.path.join(outdir, f"{base}_equity.png"))
    plot_drawdown(res["equity"], base, os.path.join(outdir, f"{base}_drawdown.png"))
    plot_price_kc(kc, base, os.path.join(outdir, f"{base}_kc.png"), trades=res["trades"])

    print("=== Strategy Metrics ===")
    print("Metrics:", res["metrics"])
    if bh_res:
        print("\n=== Buy & Hold Metrics ===")
        print("Metrics:", bh_res["metrics"])
    print("Saved outputs in:", outdir)

if __name__ == "__main__":
    main()