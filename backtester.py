from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass

__all__ = ["BTParams", "Costs", "run_backtest", "run_buy_and_hold"]

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
    trailing_stop: bool = False
    trailing_atr_mult: float = 2.5

def run_backtest(df: pd.DataFrame, sig: pd.DataFrame, p: BTParams) -> dict:
    data = pd.concat([df, sig], axis=1).copy()
    warm = p.warmup_bars or max(20, 10)
    mask = (pd.Series(range(len(data)), index=data.index) >= warm)

    exec_px = data["Open"].shift(-1) if p.execution == "next_open" else data["Close"].shift(-1)
    cost_in = 1.0 - (p.fee_bps + p.slip_bps) / 10000.0
    cost_out = 1.0 - (p.fee_bps + p.slip_bps) / 10000.0

    equity = p.initial_capital
    cash = p.initial_capital
    pos = 0.0
    side = 0
    entry_px = np.nan
    entry_t = None
    stop_px = np.nan
    tp_px = np.nan
    atr_at_entry = np.nan
    trailing_high = np.nan
    trailing_low = np.nan
    trades = []
    equity_curve = pd.Series(p.initial_capital, index=data.index, name="equity")

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

            ts_hit = False
            if p.trailing_stop:
                if side == 1:
                    trailing_high = max(data["High"].iat[i], trailing_high)
                    ts_level = trailing_high - p.trailing_atr_mult * atr_at_entry
                    if data["Low"].iat[i] <= ts_level:
                        ts_hit = True
                elif side == -1:
                    trailing_low = min(data["Low"].iat[i], trailing_low)
                    ts_level = trailing_low + p.trailing_atr_mult * atr_at_entry
                    if data["High"].iat[i] >= ts_level:
                        ts_hit = True

            if exit_flag or st_hit or tp_hit or ts_hit:
                px = nxt_px * cost_out
                pnl = pos * (px - entry_px)
                initial_risk = p.atr_stop_mult * atr_at_entry * abs(pos)
                r_mult = float(pnl / initial_risk) if initial_risk > 0 else 0.0
                cash += pnl
                equity = cash
                trades.append(dict(
                    entry_time=entry_t, exit_time=data.index[i+1],
                    side="long" if side == 1 else "short",
                    entry_px=float(entry_px), exit_px=float(px),
                    shares=float(abs(pos)), pnl=float(pnl),
                    initial_risk=float(initial_risk), r_multiple=r_mult
                ))
                pos = 0.0; side = 0; entry_px = np.nan; stop_px = np.nan; tp_px = np.nan
                atr_at_entry = np.nan; trailing_high = np.nan; trailing_low = np.nan; entry_t = None

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
                    atr_at_entry = atr_now
                    trailing_high = data["High"].iat[i]

            elif go_short and not np.isnan(atr_now):
                ep = nxt_px * cost_in
                qty = size_from_risk(ep, atr_now)
                if qty >= 1:
                    side = -1; pos = -qty; entry_px = ep; entry_t = data.index[i+1]
                    stop_px = entry_px + p.atr_stop_mult * atr_now
                    tp_px = entry_px - (p.take_profit_mult * p.atr_stop_mult * atr_now) if p.take_profit_mult else np.nan
                    atr_at_entry = atr_now
                    trailing_low = data["Low"].iat[i]

        equity = cash if side == 0 else cash + pos * data["Close"].iat[i]
        equity_curve.iat[i] = equity

    if side != 0:
        last_px = data["Close"].iat[-1] * cost_out
        pnl = pos * (last_px - entry_px)
        initial_risk = p.atr_stop_mult * atr_at_entry * abs(pos)
        r_mult = float(pnl / initial_risk) if initial_risk > 0 else 0.0
        cash += pnl
        equity = cash
        equity_curve.iat[-1] = equity
        trades.append(dict(
            entry_time=entry_t, exit_time=data.index[-1],
            side="long" if side == 1 else "short",
            entry_px=float(entry_px), exit_px=float(last_px),
            shares=float(abs(pos)), pnl=float(pnl),
            initial_risk=float(initial_risk), r_multiple=r_mult
        ))

    tdf = pd.DataFrame(trades)
    curve = equity_curve

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

    if not tdf.empty:
        metrics.update(_compute_expectancy(tdf))
        metrics.update(_compute_signal_stats(tdf, data))

    return dict(trades=tdf, equity=curve, returns=ret, metrics=metrics)


def _max_consecutive(series: pd.Series) -> int:
    if series.empty or not series.any():
        return 0
    return int(series.groupby((~series).cumsum()).sum().max())


def _compute_expectancy(tdf: pd.DataFrame) -> dict:
    if tdf.empty or "r_multiple" not in tdf.columns:
        return {"Expectancy": 0.0, "AvgWinR": 0.0, "AvgLossR": 0.0, "WinRate": 0.0}
    wins = tdf[tdf["pnl"] > 0]["r_multiple"]
    losses = tdf[tdf["pnl"] <= 0]["r_multiple"]
    win_rate = len(wins) / len(tdf)
    avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
    avg_loss = float(abs(losses.mean())) if len(losses) > 0 else 0.0
    expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    return {
        "Expectancy": float(expectancy),
        "AvgWinR": avg_win,
        "AvgLossR": avg_loss,
        "WinRate": float(win_rate)
    }


def _compute_signal_stats(tdf: pd.DataFrame, data: pd.DataFrame) -> dict:
    if tdf.empty:
        return {"TradesPerYear": 0.0, "AvgDaysInTrade": 0.0, "MaxConsecutiveWins": 0, "MaxConsecutiveLosses": 0}
    if "duration_bars" not in tdf.columns:
        tdf = tdf.copy()
        tdf["duration_bars"] = (pd.to_datetime(tdf["exit_time"]) - pd.to_datetime(tdf["entry_time"])).dt.days
    years = max((data.index[-1] - data.index[0]).days / 365.25, 1e-9)
    return {
        "TradesPerYear": float(len(tdf) / years),
        "AvgDaysInTrade": float(tdf["duration_bars"].mean()),
        "MaxConsecutiveWins": _max_consecutive(tdf["pnl"] > 0),
        "MaxConsecutiveLosses": _max_consecutive(tdf["pnl"] < 0),
    }


def run_buy_and_hold(df: pd.DataFrame, initial_capital: float = 100000.0) -> dict:
    price = df["Close"].copy()
    shares = initial_capital / price.iloc[0]
    equity = price * shares
    returns = equity.pct_change().fillna(0.0)

    years = max((price.index[-1] - price.index[0]).days / 365.25, 1e-9)
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    vol = returns.std() * (252 ** 0.5)
    sharpe = (returns.mean() * 252) / vol if vol != 0 else 0.0
    downside = returns[returns < 0].std() * (252 ** 0.5)
    sortino = (returns.mean() * 252) / downside if downside != 0 else 0.0
    dd = equity / equity.cummax() - 1.0
    maxdd = float(dd.min())

    return {
        "equity": equity,
        "returns": returns,
        "metrics": {
            "CAGR": float(cagr),
            "Sharpe": float(sharpe),
            "Sortino": float(sortino),
            "MaxDrawdown": maxdd,
            "Exposure": 1.0,
            "FinalValue": float(equity.iloc[-1]),
            "NumTrades": 1,
            "Expectancy": 0.0,
            "AvgWinR": 0.0,
            "AvgLossR": 0.0,
            "WinRate": 0.0,
            "TradesPerYear": 0.0,
            "AvgDaysInTrade": 0.0,
            "MaxConsecutiveWins": 0,
            "MaxConsecutiveLosses": 0,
        }
    }
