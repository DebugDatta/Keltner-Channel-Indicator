# KELTNER CHANNEL INDICATOR PROJECT (GUI + WEB EDITION)

---

A complete and production-level **Python project** that unites a **Tkinter Desktop GUI** and a **Streamlit Web App** to analyze, visualize, and backtest the **Keltner Channel** indicator, a dynamic trading tool based on volatility and trend strength.

---

## WHAT IS THE KELTNER CHANNEL?

---

The **Keltner Channel (KC)** is a volatility-based indicator consisting of three dynamic lines derived from **EMA** and **ATR**. It adapts to price volatility and helps identify **breakouts**, **trend strength**, and **reversals**.

**Formulas:**

* **Middle Line (Base):** EMA(Close, n)
* **Upper Band:** EMA + (ATR × Multiplier)
* **Lower Band:** EMA − (ATR × Multiplier)

**Interpretation:**

* **Price > Upper Band:** Uptrend or bullish breakout
* **Price < Lower Band:** Downtrend or bearish breakdown
* **Price inside bands:** Range-bound or consolidation

The Keltner Channel dynamically widens or contracts based on market volatility, making it ideal for **trend continuation** or **mean-reversion strategies**.

---

## PROJECT OVERVIEW

---

This system automatically performs:

1. **Data Fetching** – Downloads historical OHLC data from Yahoo Finance
2. **Indicator Computation** – Calculates EMA, ATR, and Keltner Channel
3. **Signal Generation** – Generates long/short entries and exits
4. **Backtesting** – Simulates trades with capital, stop-loss, and take-profit logic
5. **Performance Metrics** – Calculates advanced return and risk indicators
6. **Visualization** – Displays charts (Price, Equity, Drawdown)
7. **Export** – Saves CSV, JSON, PNG, and PDF reports automatically

---

## FEATURES SUMMARY

---

### DESKTOP GUI (Tkinter)

* Slider-based controls for indicator and strategy parameters
* Dynamic charts using Matplotlib (Price, Equity, Drawdown)
* File chooser for output directory
* Instant metric summaries
* Auto run-logging (`runs_log.csv` per ticker)
* PDF export with parameters, metrics, and visuals

### WEB APP (Streamlit)

* Modern web dashboard interface
* Real-time Plotly visualizations (interactive, zoomable)
* Interval-based period restriction per Yahoo data limits
* Multi-tab design for Backtest, Trades, History, and Reports
* Downloadable CSVs, charts, and PDF reports
* Auto folder organization by ticker

---

## STRATEGIES SUPPORTED

---

1. **Momentum Breakout:** Buys break above upper KC, sells below lower KC.
2. **Mean Reversion:** Buys near lower KC, sells near upper KC.
3. **PercentB Strategy:** Enters based on normalized band position (0–1).
4. **Pullback Strategy:** Enters on retracement within a strong trend.
5. **Regime Switch:** Switches between long/short modes based on KC slope.

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

The app automatically filters available **periods** based on selected **intervals**, ensuring compatibility with Yahoo Finance limits.

---

## FULL TECHNICAL TERM EXPLANATION

---

Below is a detailed glossary of every key technical term used in this system.

### 1. **OHLC (Open, High, Low, Close)**

Standard price data structure.

* **Open:** First traded price of the time interval
* **High:** Highest price reached
* **Low:** Lowest price reached
* **Close:** Final traded price of the interval

### 2. **EMA (Exponential Moving Average)**

A weighted average of closing prices giving more importance to recent data.
Faster to react than a simple moving average (SMA), making it ideal for trend detection.

**Formula:**
`EMA = (Close_today × α) + EMA_yesterday × (1 - α)`
where `α = 2 / (N + 1)`

### 3. **ATR (Average True Range)**

Measures volatility.
It computes the average range (High - Low) over N periods, accounting for gaps.

**Formula:**
`TR = max(High - Low, abs(High - PrevClose), abs(Low - PrevClose))`
`ATR = EMA(TR, N)`

### 4. **Keltner Channel (KC)**

A volatility envelope based on EMA and ATR.
Expands and contracts dynamically to reflect volatility changes.

* **Upper Band:** EMA + ATR × Multiplier
* **Lower Band:** EMA − ATR × Multiplier

### 5. **Breakout**

Price crossing above or below the KC bands.
Indicates potential start of new trend or strong momentum burst.

### 6. **Mean Reversion**

The concept that prices revert back to their average value after deviation.
KC helps spot overbought or oversold zones.

### 7. **Pullback**

Temporary counter-trend move inside a larger trend, often an ideal entry point.

### 8. **Regime Detection**

Identifies whether the market is trending or ranging based on slope of KC midline.

### 9. **Risk per Trade (%)**

The fraction of total capital risked in a single trade.
E.g., 1% risk means a stop-loss is sized so the loss equals 1% of total equity.

### 10. **Stop × ATR**

A volatility-adjusted stop-loss distance.
E.g., ATR=2.5, Multiplier=2 → Stop = 5 points below/above entry.

### 11. **Take-Profit × ATR**

Target level based on multiples of ATR for consistent reward-to-risk ratios.

### 12. **Fee (bps)**

Cost per transaction, in basis points.
1 basis point (bps) = 0.01% = 0.0001 in decimal form.

### 13. **Slippage**

Difference between intended trade price and actual execution price due to market movement or low liquidity.

### 14. **Equity Curve**

Graph showing total account value across time during the backtest.

### 15. **Drawdown**

The decline from a peak to a trough in portfolio value.
Expressed as a percentage of the peak.

**Max Drawdown** = Largest historical drawdown observed.

### 16. **Exposure**

The percentage of time your strategy holds active positions.

**Formula:**
`Exposure = (Total time in trades) / (Total backtest duration)`

### 17. **CAGR (Compound Annual Growth Rate)**

The mean annual growth rate of portfolio over the test period.

**Formula:**
`CAGR = (Final Equity / Initial Equity)^(1 / Years) - 1`

### 18. **Sharpe Ratio**

Measures risk-adjusted return using volatility.

**Formula:**
`Sharpe = (Mean(Returns) - RiskFreeRate) / StdDev(Returns)`

Higher = better risk efficiency.

### 19. **Sortino Ratio**

Similar to Sharpe but penalizes only **downside volatility** (bad risk).

**Formula:**
`Sortino = (Mean(Returns) - RiskFreeRate) / DownsideDeviation(Returns)`

### 20. **R-Multiple**

Profit or loss normalized by the initial risk per trade.

**Formula:**
`R = (Profit per trade) / (Initial risk)`

### 21. **Trade Log**

CSV file recording each trade’s entry, exit, side, PnL, duration, and R multiple.

### 22. **Backtest**

Simulation of strategy performance using historical data to validate profitability and robustness.

### 23. **PDF Report**

Automatically generated document summarizing parameters, metrics, and charts for documentation.

### 24. **Exposure Time**

Fraction of time portfolio capital is at risk or in open trades.

### 25. **Volatility Expansion / Contraction**

KC bands widen in high volatility (ATR up) and narrow in calm markets (ATR down), signaling breakout readiness.

---

## HOW TO RUN

**GUI:**

```bash
python gui_app.py
```

**Web:**

```bash
streamlit run app.py
```

Each mode supports all intervals and automatically adjusts period limits to Yahoo’s retention boundaries.

---

## OUTPUTS GENERATED

Each run creates a structured folder:

```
runs/
└── AAPL/
    ├── runs_log.csv
    ├── AAPL_20251103_141200_kc.csv
    ├── AAPL_20251103_141200_trades.csv
    ├── AAPL_20251103_141200_metrics.json
    ├── AAPL_20251103_141200_metrics.csv
    ├── AAPL_20251103_141200_report.pdf
    ├── AAPL_20251103_141200_equity.png
    ├── AAPL_20251103_141200_drawdown.png
    ├── AAPL_20251103_141200_kc.png
    └── AAPL_20251103_141200_summary.txt
```

---

## LIMITATIONS

* Single-symbol backtest per run
* Dependent on Yahoo Finance data limits
* No live-trade execution
* Educational and research use only

---

## FUTURE UPGRADES

* Multi-symbol batch testing
* Parameter optimization engine
* Machine learning regime filters
* Multi-timeframe aggregation
* Cloud-based dashboard

---

## AUTHOR

Developed by **Pramit Datta**
