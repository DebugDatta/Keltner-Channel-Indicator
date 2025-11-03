from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class Costs:
    fee_bps: float = 1.0
    slip_bps: float = 2.0

@dataclass
class BTParams:
    execution: str = "next_open"      # next_open or next_close
    initial_capital: float = 100000.0
    side: str = "long_short"          # long_only, short_only, long_short
    fee_bps: float = 1.0
    slip_bps: float = 2.0
    risk_per_trade: float = 0.01      # 0 means full notional
    atr_stop_mult: float = 2.0
    take_profit_mult: float | None = None
    warmup_bars: int | None = None
    max_leverage: float = 1.0

def _bps_mult(bps: float) -> float:
    return 1.0 - bps / 10000.0

def run_backtest(df: pd.DataFrame, sig: pd.DataFrame, p: BTParams) -> dict:
    data = pd.concat([df, sig], axis=1).copy()
    warm = p.warmup_bars or max(20, 10)
    mask = (pd.Series(range(len(data)), index=data.index) >= warm)

    exec_px = data["Open"].shift(-1) if p.execution == "next_open" else data["Close"].shift(-1)
    cost_in = _bps_mult(p.fee_bps + p.slip_bps)
    cost_out = _bps_mult(p.fee_bps + p.slip_bps)

    equity = p.initial_capital
    cash = p.initial_capital
    pos = 0.0
    side = 0                 # 1 long, -1 short, 0 flat
    entry_px = np.nan
    entry_t = None
    stop_px = np.nan
    tp_px = np.nan
    trades = []

    def size_from_risk(px: float, atr_now: float) -> float:
        if p.risk_per_trade <= 0 or atr_now <= 0:
            shares = (equity * p.max_leverage) / max(px, 1e-12)
        else:
            risk_per_share = p.atr_stop_mult * atr_now
            capital_at_risk = equity * p.risk_per_trade
            shares = capital_at_risk / max(risk_per_share, 1e-12)
        return float(np.floor(max(shares, 0)))

    for i in range(len(data) - 1):
        if not mask.iat[i]:
            continue
        nxt_px = exec_px.iat[i]
        if np.isnan(nxt_px):
            continue

        # manage exits
        if side != 0:
            exit_flag = (side == 1 and data["long_exit"].iat[i]) or (side == -1 and data["short_exit"].iat[i])
            st_hit = False
            if not np.isnan(stop_px):
                if side == 1 and data["Low"].iat[i] <= stop_px:
                    st_hit = True
                if side == -1 and data["High"].iat[i] >= stop_px:
                    st_hit = True
            tp_hit = False
            if p.take_profit_mult is not None and not np.isnan(tp_px):
                if side == 1 and data["High"].iat[i] >= tp_px:
                    tp_hit = True
                if side == -1 and data["Low"].iat[i] <= tp_px:
                    tp_hit = True

            if exit_flag or st_hit or tp_hit:
                px = nxt_px * cost_out
                pnl = pos * (px - entry_px)
                cash += pnl
                equity = cash
                trades.append(dict(
                    entry_time=entry_t, exit_time=data.index[i+1],
                    side="long" if side == 1 else "short",
                    entry_px=float(entry_px), exit_px=float(px),
                    shares=float(pos), pnl=float(pnl)
                ))
                pos = 0.0; side = 0; entry_px = np.nan; stop_px = np.nan; tp_px = np.nan; entry_t = None

        # entries
        if side == 0 and mask.iat[i]:
            go_long = data["long_entry"].iat[i]
            go_short = data["short_entry"].iat[i]
            if p.side == "long_only":
                go_short = False
            if p.side == "short_only":
                go_long = False

            atr_now = data["KC_ATR"].iat[i]

            if go_long and not np.isnan(atr_now):
                ep = nxt_px * cost_in
                qty = size_from_risk(ep, atr_now)
                if qty >= 1:
                    side = 1; pos = qty; entry_px = ep; entry_t = data.index[i+1]
                    stop_px = entry_px - p.atr_stop_mult * atr_now
                    tp_px = entry_px + (p.take_profit_mult * p.atr_stop_mult * atr_now) if p.take_profit_mult else np.nan

            elif go_short and not np.isnan(atr_now):
                ep = nxt_px * cost_in
                qty = size_from_risk(ep, atr_now)
                if qty >= 1:
                    side = -1; pos = -qty; entry_px = ep; entry_t = data.index[i+1]
                    stop_px = entry_px + p.atr_stop_mult * atr_now
                    tp_px = entry_px - (p.take_profit_mult * p.atr_stop_mult * atr_now) if p.take_profit_mult else np.nan

        equity = cash if side == 0 else cash + pos * data["Close"].iat[i]

    # force close on last bar
    if side != 0:
        last_px = data["Close"].iat[-1] * cost_out
        pnl = pos * (last_px - entry_px)
        cash += pnl
        equity = cash
        trades.append(dict(
            entry_time=entry_t, exit_time=data.index[-1],
            side="long" if side == 1 else "short",
            entry_px=float(entry_px), exit_px=float(last_px),
            shares=float(pos), pnl=float(pnl)
        ))

    tdf = pd.DataFrame(trades)

    # equity curve from exits
    curve = pd.Series(p.initial_capital, index=data.index, name="equity")
    eq = p.initial_capital
    if not tdf.empty:
        exits = tdf.set_index("exit_time")["pnl"]
        for dt in curve.index:
            if dt in exits.index:
                val = exits.loc[dt]
                eq += float(val) if isinstance(val, float) else float(val.values[0])
            curve.at[dt] = eq

    ret = curve.pct_change().fillna(0.0)
    years = ((curve.index[-1] - curve.index[0]).days / 365.25) if hasattr(curve.index, "freq") or isinstance(curve.index, pd.DatetimeIndex) else len(curve) / 252
    years = max(years, 1e-9)
    cagr = (curve.iloc[-1] / curve.iloc[0]) ** (1 / years) - 1
    vol = ret.std() * (252 ** 0.5)
    sharpe = 0.0 if vol == 0 else (ret.mean() * 252) / vol
    downside = ret[ret < 0].std() * (252 ** 0.5)
    sortino = 0.0 if downside == 0 else (ret.mean() * 252) / downside
    dd = (curve / curve.cummax() - 1.0)
    maxdd = float(dd.min())

    # exposure
    exposure = 0.0
    if not tdf.empty:
        mask_pos = pd.Series(0.0, index=data.index)
        for _, tr in tdf.iterrows():
            mask_pos.loc[tr["entry_time"]:tr["exit_time"]] = 1.0
        exposure = float(mask_pos.mean())

    metrics = dict(
        CAGR=float(cagr),
        Sharpe=float(sharpe),
        Sortino=float(sortino),
        MaxDrawdown=float(maxdd),
        Exposure=float(exposure),
        NumTrades=int(len(tdf))
    )

    return dict(trades=tdf, equity=curve, returns=ret, metrics=metrics)
