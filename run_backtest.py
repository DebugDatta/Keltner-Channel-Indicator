from __future__ import annotations
import argparse
import os
import pandas as pd

from data import fetch_ohlc
from indicators import keltner_channel
from strategy import breakout_signals
from backtester import run_backtest, BTParams
from plotting import plot_price_kc, plot_equity, plot_drawdown

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True, help="Symbol, e.g., AAPL or RELIANCE.NS")
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--period", default=None, help="Alternative to start/end, e.g., 5y or max")
    ap.add_argument("--ema", type=int, default=20)
    ap.add_argument("--atr", type=int, default=10)
    ap.add_argument("--mult", type=float, default=2.0)
    ap.add_argument("--execution", choices=["next_open","next_close"], default="next_open")
    ap.add_argument("--side", choices=["long_only","short_only","long_short"], default="long_short")
    ap.add_argument("--fee_bps", type=float, default=1.0)
    ap.add_argument("--slip_bps", type=float, default=2.0)
    ap.add_argument("--risk", type=float, default=0.01, help="risk per trade fraction, 0 for full notional")
    ap.add_argument("--stop", type=float, default=2.0, help="ATR stop multiple")
    ap.add_argument("--tp", type=float, default=None, help="take profit multiple of ATR stop")
    ap.add_argument("--warmup", type=int, default=None)
    ap.add_argument("--outdir", default="out")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # data
    df = fetch_ohlc(args.ticker, start=args.start, end=args.end, period=args.period)

    # indicator
    kc = keltner_channel(df, ema_len=args.ema, atr_len=args.atr, mult=args.mult)

    # signals
    sig = breakout_signals(kc)

    # backtest
    bt = BTParams(
        execution=args.execution,
        initial_capital=100000.0,
        side=args.side,
        fee_bps=args.fee_bps,
        slip_bps=args.slip_bps,
        risk_per_trade=args.risk,
        atr_stop_mult=args.stop,
        take_profit_mult=args.tp,
        warmup_bars=args.warmup or max(args.ema, args.atr),
        max_leverage=1.0,
    )
    res = run_backtest(kc, sig, bt)

    # save outputs
    out_csv = os.path.join(args.outdir, f"{args.ticker}_kc.csv")
    kc_out = kc.copy()
    kc_out[["long_entry","short_entry","long_exit","short_exit"]] = sig
    kc_out.to_csv(out_csv)

    trades_csv = os.path.join(args.outdir, f"trades_{args.ticker}.csv")
    res["trades"].to_csv(trades_csv, index=False)

    eq_png = os.path.join(args.outdir, f"{args.ticker}_equity.png")
    dd_png = os.path.join(args.outdir, f"{args.ticker}_drawdown.png")
    kc_png = os.path.join(args.outdir, f"{args.ticker}_kc.png")

    plot_equity(res["equity"], args.ticker, eq_png)
    plot_drawdown(res["equity"], args.ticker, dd_png)
    plot_price_kc(kc, args.ticker, kc_png, trades=res["trades"])

    print("Saved:", out_csv)
    print("Saved:", trades_csv)
    print("Saved:", eq_png)
    print("Saved:", dd_png)
    print("Saved:", kc_png)
    print("Metrics:", res["metrics"])

if __name__ == "__main__":
    main()
