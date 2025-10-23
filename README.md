# KELTNER CHANNEL INDICATOR PROJECT (GUI EDITION)

---

A complete Python project with a **Tkinter-based GUI** that calculates, visualizes, and backtests the **Keltner Channel** — a volatility-based technical indicator used by traders to identify trends, breakouts, and reversals.

This project lets you interact with sliders, dropdowns, and file choosers directly in a graphical interface — no terminal needed.
It uses live data from Yahoo Finance, runs a backtest, displays metrics and plots in the same window, and saves all results (charts and CSVs) automatically.

---

## WHAT IS THE KELTNER CHANNEL?

---

The **Keltner Channel** is a volatility envelope consisting of three lines around price:

1. **Middle Line (EMA)** – Exponential Moving Average of the closing price
2. **Upper Band** – EMA + (Average True Range × Multiplier)
3. **Lower Band** – EMA - (Average True Range × Multiplier)

**Interpretation:**

* Price above the upper band → bullish breakout or strong momentum
* Price below the lower band → bearish breakdown
* Price within the bands → consolidation or low volatility phase

Traders use the Keltner Channel to identify trend direction, catch breakouts early, and set stop-loss/take-profit levels that adapt to volatility.

---

## PROJECT OVERVIEW

---

The GUI app automates:

1. **Data Fetching** – Pulls OHLC data from Yahoo Finance
2. **Indicator Computation** – Calculates EMA, ATR, and Keltner Channel
3. **Signal Generation** – Detects entry and exit points from breakouts
4. **Backtesting** – Simulates realistic trades with risk management, slippage, and fees
5. **Performance Metrics** – Computes CAGR, Sharpe, Sortino, Max Drawdown, Exposure, etc.
6. **Visualization** – Shows all charts (price, equity, drawdown) inside the GUI
7. **Export** – Saves CSVs and PNGs to a user-selected folder

---

## KEY FEATURES

---

- User-friendly **GUI built with Tkinter**
- **Ticker input** box with real-time validation (errors shown instantly)
- **Sliders** for EMA, ATR, multiplier, risk, stop × ATR, and take-profit × ATR
- **Dropdowns** for side (`long_only`, `short_only`, `long_short`) and execution mode (`next_open`, `next_close`)
- **Automatic folder chooser** to pick where to save results
- **Live metrics panel** with CAGR, Sharpe, Sortino, Max Drawdown, Exposure, Trades count
- **Embedded Matplotlib charts** for:
   * Price with Keltner Bands and trade markers
   * Equity curve
   * Drawdown curve
- **CSV and PNG export** for all results

---

## HOW TO SET UP

---

1. Clone the repository:

   ```bash
   git clone https://github.com/DebugDatta/Keltner-Channel-Indicator.git
   ```

2. Enter the folder:

   ```bash
   cd Keltner-Channel-Indicator
   ```

3. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   venv\Scripts\activate     # Windows
   source venv/bin/activate  # macOS/Linux
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   *(If tkinter isn’t installed, install it)*

---

## HOW TO RUN (GUI MODE)

---

Simply execute:

   ```bash
   python gui_app.py
   ```

A graphical window will open.

Inside the GUI:

1. Enter a ticker (e.g., `AAPL`, `RELIANCE.NS`, `BTC-USD`)
2. Choose period or date range
3. Adjust sliders for EMA, ATR, Multiplier, Risk %, Stop × ATR, and optionally Take-Profit × ATR
4. Pick Side (`long_only`, `short_only`, `long_short`) and Execution (`next_open`, `next_close`)
5. Click **Choose Folder** to set where results will be saved
6. Click **Run Backtest**

The app will:
- Validate the ticker
- Download data
- Run the strategy
- Display metrics and charts
- Save:
  ```
  <ticker>_kc.csv
  trades_<ticker>.csv
  <ticker>_kc.png
  <ticker>_equity.png
  <ticker>_drawdown.png
  ```
  in your selected folder.


---

## TECHNICAL TERMS SIMPLIFIED

---

- **EMA (Exponential Moving Average):** Fast-reacting average used for trend detection
- **ATR (Average True Range):** Volatility measure showing average range of movement
- **Multiplier:** Determines channel width; larger = fewer signals
- **Risk (%):** Fraction of capital risked per trade
- **Stop/TP multiples:** Dynamic exits based on ATR volatility
- **Fee_bps / Slip_bps:** Trading cost modeling in basis points (1bps = 0.01%)
- **CAGR:** Average annual portfolio growth
- **Sharpe / Sortino:** Risk-adjusted returns
- **Max Drawdown:** Largest peak-to-trough equity decline

---

## LIMITATIONS

---

- Works only on daily OHLC data
- Handles one instrument per test
- Ignores dividends and corporate events
- Meant for learning and research, not live trading

---

## FUTURE IMPROVEMENTS

---

- Add portfolio-level testing
- Automated parameter optimization
- Multi-asset comparison mode
- Trend filters like SMA200 confirmation
- Advanced GUI themes and dashboards

---

## AUTHOR

---

Developed by **Pramit Datta**
