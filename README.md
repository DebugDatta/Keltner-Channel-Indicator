# KELTNER CHANNEL INDICATOR PROJECT (GUI + WEB EDITION)

---

A complete and production level **Python project** that unites a **Tkinter Desktop GUI** and a **Streamlit Web App** to analyze, visualize, and backtest the **Keltner Channel** indicator, a dynamic trading tool based on volatility and trend strength.

---

## STRATEGY MECHANICS AND FORMULAS

---

This project uses rule based systems with explicit math. Signals, sizing, and exits are deterministic.

**Bands and core terms**

* Middle: `KC_mid = EMA(Close, n)`
* True Range: `TR_t = max[(High_t - Low_t), |High_t - Close_{t−1}|, |Low_t - Close_{t−1}|]`
* Average True Range: `ATR = EMA(TR, n_atr)`
* Upper Band: `KC_up = KC_mid + (k_atr × ATR)`
* Lower Band: `KC_dn = KC_mid - (k_atr × ATR)`
* Band position: `PercentB = (Close - KC_dn) / (KC_up - KC_dn)` clipped to `[0, 1]`
* Midline slope: `Slope_mid = KC_mid_t - KC_mid_{t−1}` or regression slope over `L` bars
* Volatility stop distance: `StopPts = s_atr × ATR`
* Take profit distance: `TPPts = tp_atr × ATR`
* Risk based position size: `Qty = floor((Equity × risk_pct) / StopPts)`
* Transaction fee: `Fee = (bps × Price × Qty) / 10000`
* Slippage: `Slip = (slip_pct × Price)` or `Slip = (ticks × tick_value)`

**Stops and targets**

* Long stop: `Stop = Entry - StopPts`
* Long take profit: `TP = Entry + TPPts`
* Short stop: `Stop = Entry + StopPts`
* Short take profit: `TP = Entry - TPPts`

**Returns and risk**

* Per trade PnL: `PnL = (side × (Exit - Entry) × Qty) - Fees - Slippage`
* Equity update: `Equity_t = Equity_{t−1} + PnL_t`
* Drawdown: `DD_t = 1 - (Equity_t / peak(Equity))`
* Exposure: `Exposure = (time_in_position / total_time)`

---

## WHAT IS THE KELTNER CHANNEL?

---

The **Keltner Channel (KC)** is a volatility based indicator with three dynamic lines from **EMA** and **ATR**. It adapts to price volatility and helps identify **breakouts**, **trend strength**, and **reversals**.

**Formulas**

* **Middle Line (Base):** `EMA(Close, n)`
* **Upper Band:** `EMA(Close, n) + (ATR × Multiplier)`
* **Lower Band:** `EMA(Close, n) - (ATR × Multiplier)`

**Interpretation**

* **Price > Upper Band:** Uptrend or bullish breakout
* **Price < Lower Band:** Downtrend or bearish breakdown
* **Price inside bands:** Range bound or consolidation

The Keltner Channel widens or contracts with volatility, useful for **trend continuation** and **mean reversion**.

---

## PROJECT OVERVIEW

---

This system automatically performs

1. **Data Fetching** – Downloads historical OHLC data from Yahoo Finance
2. **Indicator Computation** – Calculates EMA, ATR, and Keltner Channel
3. **Signal Generation** – Creates long or short entries and exits
4. **Backtesting** – Simulates trades with capital, stop loss, and take profit logic
5. **Performance Metrics** – Computes advanced return and risk indicators
6. **Visualization** – Displays charts (Price, Equity, Drawdown)
7. **Export** – Saves CSV, JSON, PNG, and report files automatically

---

## FEATURES SUMMARY

---

### DESKTOP GUI (Tkinter)

* Slider based controls for all indicator and strategy parameters
* Capital, leverage, trend EMA, and PercentB threshold inputs
* Dynamic charts using Matplotlib (Price, Equity, Drawdown)
* File chooser for output directory
* Instant metric summaries
* Auto run logging (`runs_log.csv` per ticker)
* PDF export with parameters, metrics, and visuals

### WEB APP (Streamlit)

* Modern web dashboard interface
* Real time Plotly visualizations (interactive and zoomable)
* Capital, leverage, trend EMA, trailing stop, and PercentB threshold controls
* Buy & Hold benchmark comparison
* Interval based period restriction per Yahoo data limits
* Multi tab design: Backtest, KC CSV, Trades Explorer, Run History, Report Builder, GBM Simulation
* GBM Monte Carlo simulation with distribution histograms and percentile tables
* Downloadable CSVs, charts, and reports
* Auto folder organization by ticker

---

## STRATEGIES SUPPORTED

---

### 1. **Momentum Breakout**

* Entry long when price closes above the upper Keltner Channel (`Close > KC_up`)
* Entry short when price closes below the lower Keltner Channel (`Close < KC_dn`)
* Optional trend confirmation using midline slope (`Slope_mid`)
* Exit on midline cross, stop loss, or take profit trigger

---

### 2. **Mean Reversion**

* Entry long when price touches or closes near lower band (`Close ≤ KC_dn + α × ATR`)
* Entry short when price touches or closes near upper band (`Close ≥ KC_up - α × ATR`)
* Exit at midline or opposite band
* Protective stop and target defined using ATR multiples

---

### 3. **PercentB Strategy**

* Compute `PercentB = (Close - KC_dn) / (KC_up - KC_dn)`
* Long entry when `PercentB` crosses above upper threshold (e.g., 0.8)
* Short entry when `PercentB` crosses below lower threshold (e.g., 0.2)
* Exit on reverse cross or ATR based exit

---

### 4. **Pullback Strategy**

* Detect primary trend using `Slope_mid`
* In an uptrend (`Slope_mid > 0`), enter long on pullback to mid or lower band after bullish confirmation
* In a downtrend (`Slope_mid < 0`), enter short on pullback to mid or upper band after bearish confirmation
* Stops and targets sized with ATR multiples

---

### 5. **Regime Switch**

* Identify market regime using slope or regression of midline
* **Positive slope:** Use momentum long strategies
* **Negative slope:** Use momentum short strategies
* **Flat slope:** Switch to mean reversion mode

---

## INTERVAL AND PERIOD COMPATIBILITY

| Interval | Max Lookback | Typical Periods                      |
| -------- | ------------ | ------------------------------------ |
| 1m       | ~7 days      | 1d, 2d, 3d, 5d, 7d                   |
| 2m–30m   | ~60 days     | 5d, 10d, 15d, 30d, 60d               |
| 1h       | ~2 years     | 1mo, 3mo, 6mo, 1y, 2y                |
| 1d       | ~50 years    | 1mo, 3mo, 6mo, 1y, 5y, 10y, ytd, max |
| 1wk      | ~50 years    | 3mo, 6mo, 1y, 5y, 10y, ytd, max      |
| 1mo      | ~50 years    | 1y, 2y, 3y, 5y, 10y, max             |

The app filters available **periods** based on selected **intervals** to match Yahoo Finance limits.

---

## PARAMETER REFERENCE

All user-adjustable parameters and their valid ranges:

| Parameter | GUI Control | CLI Argument | Min | Max | Default |
|-----------|-------------|--------------|-----|-----|---------|
| Initial Capital | Entry ($) | `--capital` | 1,000 | 10,000,000 | 100,000 |
| Max Leverage | Entry | `--max-leverage` | 1.0 | 5.0 | 1.0 |
| EMA Length | Slider | `--ema` | 5 | 200 | 20 |
| ATR Length | Slider | `--atr` | 5 | 100 | 10 |
| Band Multiplier | Slider | `--mult` | 1.0 | 5.0 | 2.0 |
| Risk per Trade | Slider | `--risk` | 0.001 | 0.100 | 0.010 |
| Stop × ATR | Slider | `--stop` | 0.5 | 10.0 | 2.0 |
| Take Profit × ATR | Checkbox + Slider | `--tp` | 0.5 | 10.0 | 4.0 |
| Trailing Stop | Checkbox | `--trailing-stop` | — | boolean | False |
| Trailing × ATR | Entry | `--trailing-atr-mult` | 0.5 | 10.0 | 2.5 |
| Trend EMA | Slider | `--trend-ema` | 20 | 500 | 200 |
| PercentB Low | Entry | `--pb-low` | 0.00 | 0.50 | 0.20 |
| PercentB High | Entry | `--pb-high` | 0.50 | 1.00 | 0.80 |
| Fee (bps) | Entry | `--fee_bps` | 0 | 50 | 1.0 |
| Slippage (bps) | Entry | `--slip_bps` | 0 | 100 | 2.0 |
| Warmup Bars | Entry | `--warmup` | 0 | 500 | auto |
| Side | Combobox | `--side` | — | long_only/short_only/long_short | long_short |
| Execution | Combobox | `--execution` | — | next_open/next_close | next_open |
| Buy & Hold | Checkbox | `--bh` | — | boolean | False |

---

## FULL TECHNICAL TERM EXPLANATION

---

### 1. **OHLC (Open, High, Low, Close)**

Core market data format representing each candle’s four price points.

### 2. **EMA (Exponential Moving Average)**

`EMA_t = (α × Close_t) + ((1 - α) × EMA_{t−1})`, where `α = 2 / (N + 1)`

### 3. **ATR (Average True Range)**

`TR_t = max[(High_t - Low_t), |High_t - Close_{t−1}|, |Low_t - Close_{t−1}|]`
`ATR = EMA(TR, N)`

### 4. **Keltner Channel (KC)**

`KC_mid = EMA(Close, N)`
`KC_up = KC_mid + (ATR × Multiplier)`
`KC_dn = KC_mid - (ATR × Multiplier)`

### 5. **PercentB**

`PercentB = (Close - KC_dn) / (KC_up - KC_dn)`
Normalizes price location between KC bands, range 0–1.

### 6. **Breakout**

Price crossing above or below KC bands signals strong directional move.

### 7. **Mean Reversion**

Price tends to revert to KC midline after extremes.

### 8. **Pullback**

Temporary retracement within ongoing trend used for entries.

### 9. **Regime Detection**

Market mode identified by slope of KC midline or regression coefficient.

### 10. **Volatility Stop / ATR Stop**

Dynamic stop distance scaled by volatility: `StopPts = s_atr × ATR`.

### 11. **Risk per Trade (%)**

Defines position sizing based on acceptable percentage of total capital risk.

### 12. **Take Profit × ATR**

Defines target distance based on volatility measure: `TPPts = tp_atr × ATR`.

### 13. **Fee (bps)**

Transaction cost per trade, 1 bps = 0.01%.

### 14. **Slippage**

Execution difference between theoretical and actual trade price.

### 15. **Equity Curve**

`Equity_t = Equity_{t−1} + PnL_t`
Cumulative change in total account value through time.

### 16. **Drawdown**

`MaxDD = max[1 - (Equity_t / peak_to_date(Equity))]`
Largest observed decline in portfolio value from its peak.

### 17. **Exposure**

`Exposure = (time_in_trades / total_backtest_time)`
Time fraction when capital is actively deployed.

### 18. **CAGR (Compound Annual Growth Rate)**

`CAGR = ((FinalEquity / InitialEquity)^(1 / Years)) - 1`

### 19. **Sharpe Ratio**

`Sharpe = (mean(r) - rf) / std(r)`
Risk adjusted return per unit of total volatility.

### 20. **Sortino Ratio**

`Sortino = (mean(r) - rf) / downside_std(r)`
Risk adjusted return penalizing only downside volatility.

### 21. **R-Multiple**

`R = (Profit_per_trade) / (Initial_risk)`
Profit normalized by initial risk per trade.

### 22. **Trade Log**

Detailed record of all trades with entry, exit, PnL, side, duration, and risk metrics.

### 23. **Backtest**

Simulation of historical trades using defined rules and parameters.

### 24. **Volatility Expansion / Contraction**

KC bands widen as ATR increases (high volatility) and narrow as ATR decreases (low volatility).

### 25. **Run Log**

Aggregated record of all backtest runs storing symbol, parameters, and metrics.

### 26. **Equity Metrics**

Set of calculated statistics such as CAGR, Sharpe, Sortino, Max Drawdown, and Exposure derived from equity series.

---

## HOW TO RUN

**Clone and setup**

```bash
git clone https://github.com/DebugDatta/Keltner-Channel-Indicator.git
cd Keltner-Channel-Indicator

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS or Linux
source .venv/bin/activate

pip install -r requirements.txt
```

**GUI**

```bash
python gui_app.py
```

**Web**

```bash
streamlit run app.py
```

**CLI (command line)**

```bash
python run_backtest.py --ticker AAPL --period 5y --strategy momentum --capital 100000 --max-leverage 2.0 --trend-ema 200
```

**CLI (interactive mode)**

```bash
python run_backtest.py --interactive
```

Both modes support all intervals and automatically adjust period limits to Yahoo retention boundaries.

### CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--ticker` | Ticker symbol | *(required unless --interactive)* |
| `--period` | Yahoo period (1mo,3mo,6mo,1y,2y,5y,10y,max) | 5y |
| `--start` | Start date YYYY-MM-DD | None |
| `--end` | End date YYYY-MM-DD | None |
| `--interval` | Data interval (1m,2m,5m,15m,30m,1h,1d,1wk,1mo) | 1d |
| `--ema` | EMA length for KC middle | 20 |
| `--atr` | ATR length | 10 |
| `--mult` | ATR multiplier for bands | 2.0 |
| `--strategy` | Strategy mode | momentum |
| `--risk` | Risk per trade fraction | 0.01 |
| `--stop` | Stop loss × ATR | 2.0 |
| `--tp` | Take profit × ATR | None |
| `--side` | long_only / short_only / long_short | long_short |
| `--execution` | next_open / next_close | next_open |
| `--fee_bps` | Fee per side in bps | 1.0 |
| `--slip_bps` | Slippage per side in bps | 2.0 |
| `--warmup` | Warmup bars override | auto |
| `--capital` | Initial capital ($) | 100000 |
| `--max-leverage` | Maximum leverage | 1.0 |
| `--pb-low` | PercentB low threshold | 0.20 |
| `--pb-high` | PercentB high threshold | 0.80 |
| `--trend-ema` | Trend EMA length for momentum/regime strategies | 200 |
| `--trailing-stop` | Enable trailing stop exit | False |
| `--trailing-atr-mult` | Trailing stop ATR multiplier | 2.5 |
| `--bh` | Run Buy & Hold benchmark alongside backtest | False |
| `--outdir` | Output directory | out |
| `--interactive` | Run interactive prompt mode | False |

---

## OUTPUTS GENERATED

Each run creates a structured folder

```
runs/
└── AAPL/
    ├── runs_log.csv
    ├── AAPL_20251103_141200_kc.csv
    ├── AAPL_20251103_141200_trades.csv
    ├── AAPL_20251103_141200_metrics.json
    ├── AAPL_20251103_141200_metrics.csv
    ├── AAPL_20251103_141200_params.json
    ├── AAPL_20251103_141200_equity.png
    ├── AAPL_20251103_141200_drawdown.png
    ├── AAPL_20251103_141200_kc.png
    └── AAPL_20251103_141200_summary.txt
```

`runs_log.csv` in the parent `runs/` folder aggregates all historical runs for all tickers, useful for the **Run History** tab in the web app.

---

## LIMITATIONS

* Single symbol backtest per run
* Dependent on Yahoo Finance data limits
* No live trade execution
* Educational and research use only

---

## CHANGELOG

### v3.0 — Advanced Analytics & Simulation
- Added **R-Multiple** per trade: `initial_risk` and `r_multiple` columns in trades CSV
- Added **Expectancy** metric: `Expectancy = WinRate × AvgWinR − LossRate × AvgLossR`
- Added **signal frequency stats**: TradesPerYear, AvgDaysInTrade, MaxConsecutiveWins, MaxConsecutiveLosses
- Added **Trailing Stop** mechanism: `--trailing-stop` + `--trailing-atr-mult`; exits when price retraces by ATR multiple after new highs/lows
- Added **Buy & Hold benchmark**: `--bh` flag; runs B&H alongside backtest and prints comparison metrics
- Added **GBM Monte Carlo Simulation**: `simulation.py` module; runs strategy across 100–5,000 synthetic GBM price paths; shows percentile distributions (p5/p25/p50/p75/p95) for CAGR, Sharpe, MaxDD, Expectancy; includes distribution histograms and sample path visualization
- New **GBM Simulation tab** in Streamlit web app

### v2.0 — User Input Expansions
- Added `initial_capital` and `max_leverage` as user-configurable parameters across all interfaces
- Added `trend_ema_len` parameter (configurable Trend EMA) for momentum and regime_switch strategies
- Added `pb_low` / `pb_high` PercentB threshold parameters for the percentb strategy
- Added `--interactive` CLI mode with guided prompts
- Fixed equity curve to update mark-to-market every bar instead of only at trade exits
- Fixed short entry/exit marker swap in plotting
- Fixed Keltner Channel middle line to use Close price instead of Typical Price
- Removed invalid `90m` interval from interval limits
- Added `__all__` exports to all modules for clean public API
- Added comprehensive CLI argument reference to README

---

## FUTURE UPGRADES

* Multi symbol batch testing
* Parameter optimization engine (grid search over EMA/ATR/mult combinations)
* Machine learning regime filters
* Multi timeframe aggregation
* Cloud based dashboard
* Automated PDF report emailed on completion
* Combined equity curve (strategy vs B&H) on single chart

---

## AUTHOR

Developed by **Pramit Datta**
