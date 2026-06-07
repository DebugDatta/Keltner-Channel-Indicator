from __future__ import annotations
import numpy as np
import pandas as pd

__all__ = ["gbm_price_paths", "run_gbm_simulation"]

def gbm_price_paths(
    S0: float,
    mu: float,
    sigma: float,
    n_days: int,
    n_paths: int,
    seed: int = 42,
    dt: float = 1 / 252
) -> np.ndarray:
    np.random.seed(seed)
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * np.random.standard_normal((n_days, n_paths))
    paths = np.zeros((n_days + 1, n_paths))
    paths[0] = S0
    paths[1:] = S0 * np.exp(np.cumsum(log_returns, axis=0))
    return paths


def run_gbm_simulation(
    kc_params: dict,
    bt_params,
    sig_params: dict,
    mu: float = 0.0,
    sigma: float = 0.20,
    n_days: int = 2520,
    n_paths: int = 500,
    S0: float = 100.0,
    seed: int = 42,
    progress_callback=None,
) -> dict:
    from backtester import run_backtest
    from indicators import keltner_channel
    from strategy import keltner_signals

    paths = gbm_price_paths(S0, mu, sigma, n_days, n_paths, seed)
    all_results = []
    failed_paths = []

    for i in range(n_paths):
        try:
            close_prices = paths[:n_days, i]
            if np.any(np.isnan(close_prices)) or np.any(close_prices <= 0):
                failed_paths.append((i, "NaN or non-positive price in path"))
                continue

            sim_df = pd.DataFrame(
                {"Open": close_prices, "High": close_prices, "Low": close_prices, "Close": close_prices},
                index=pd.bdate_range(start="2015-01-01", periods=n_days)
            )

            kc = keltner_channel(sim_df, **kc_params)
            sig = keltner_signals(kc, **sig_params)
            res = run_backtest(kc, sig, bt_params)

            m = res["metrics"].copy()
            m["Path"] = i
            all_results.append(m)

        except Exception as e:
            failed_paths.append((i, str(e)))

        if progress_callback is not None:
            progress_callback(i + 1, n_paths)

    if failed_paths:
        print(f"[GBM Sim] {len(failed_paths)} paths failed: {failed_paths[:5]}")

    if not all_results:
        return {"summary": {}, "all_results": pd.DataFrame(), "paths": paths, "failed": len(failed_paths)}

    results_df = pd.DataFrame(all_results)
    percentiles = [5, 25, 50, 75, 95]

    summary = {}
    for metric in ["CAGR", "Sharpe", "Sortino", "MaxDrawdown", "NumTrades", "Expectancy"]:
        if metric in results_df.columns:
            summary[metric] = {f"p{p}": float(results_df[metric].quantile(p / 100)) for p in percentiles}
            summary[metric]["mean"] = float(results_df[metric].mean())
            summary[metric]["std"] = float(results_df[metric].std())

    return {"summary": summary, "all_results": results_df, "paths": paths, "failed": len(failed_paths)}