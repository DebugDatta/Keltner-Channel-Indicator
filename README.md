# KELTNER CHANNEL INDICATOR PROJECT (GUI + WEB EDITION)

---

A complete Python project with a **Tkinter-based GUI** and a **Streamlit-based Web App** that calculates, visualizes, and backtests the **Keltner Channel** — a volatility-based technical indicator used by traders to identify trends, breakouts, and reversals.

You can interact through sliders, dropdowns, and inputs in both desktop and web versions.
It fetches live data from Yahoo Finance, runs a backtest, computes performance metrics, shows interactive charts, and saves all results automatically — including PDF reports and CSV exports.

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

Traders use the Keltner Channel to identify trend direction, capture breakouts, and set dynamic stop-loss and take-profit levels that scale with volatility.

---

## PROJECT OVERVIEW

---

The application automates:

1. **Data Fetching** – Downloads OHLC data from Yahoo Finance
2. **Indicator Computation** – Calculates EMA, ATR, and Keltner Channel
3. **Signal Generation** – Detects entry and exit breakouts
4. **Backtesting** – Simulates trades with risk control, slippage, and fees
5. **Performance Metrics** – Calculates CAGR, Sharpe, Sortino, Max Drawdown, Exposure, etc.
6. **Visualization** – Displays price, equity, and drawdown charts
7. **Export** – Saves metrics, CSVs, PNGs, and PDFs (inputs, metrics, and charts)

---

## KEY FEATURES

---

### GUI (Tkinter)

* User-friendly **desktop GUI**
* **Ticker input** box with validation
* **Sliders** for EMA, ATR, multiplier, risk, stop × ATR, and optional take-profit × ATR
* **Dropdowns** for side (`long_only`, `short_only`, `long_short`) and execution (`next_open`, `next_close`)
* **Folder chooser** for saving outputs
* Embedded **Matplotlib** charts (Price, Equity, Drawdown)
* **Live metrics** panel with CAGR, Sharpe, Sortino, MaxDD, Exposure, Trades count
* Automatic **per-ticker subfolders** and run logging

---

### WEB APP (Streamlit)

* **Fully synced sliders and numeric inputs**
* **Interactive dashboards** using Plotly:

  * OHLC with Keltner Channels and trade markers
  * Equity and drawdown charts
* **Tabs:**

  * *Backtest* – Metrics and live charts
  * *KC CSV* – View full Keltner Channel data table
  * *Trades Explorer* – Filterable trade history, R histogram
  * *Run History* – Aggregates `runs_log.csv` from each ticker folder
  * *Report Builder* – Download PDF with parameters, metrics, and charts
* **Auto folder creation per ticker** under the root directory
* Each ticker has its own `runs_log.csv`
* Downloadable **CSV**, **PDF**, and **summary files**

---

## HOW TO SET UP

---

1. **Clone the repository:**

   ```bash
   git clone https://github.com/DebugDatta/Keltner-Channel-Indicator.git
   ```

2. **Enter the folder:**

   ```bash
   cd Keltner-Channel-Indicator
   ```

3. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   venv\Scripts\activate     # Windows
   source venv/bin/activate  # macOS/Linux
   ```

4. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   *(If tkinter isn’t installed, install it manually)*

---

## HOW TO RUN (GUI MODE)

---

```bash
python gui_app.py
```

Steps inside GUI:

1. Enter a ticker (e.g., `AAPL`, `RELIANCE.NS`, `BTC-USD`)
2. Choose a period or date range
3. Adjust EMA, ATR, Multiplier, Risk %, Stop × ATR, and optionally Take-Profit × ATR
4. Pick Side (`long_only`, `short_only`, `long_short`) and Execution (`next_open`, `next_close`)
5. Click **Choose Folder** to select save location
6. Click **Run Backtest**

The app will download data, backtest, display metrics and charts, and save results:

```
<output_root>/
└── <ticker>/
    ├── runs_log.csv
    ├── <ticker>_<timestamp>_kc.csv
    ├── <ticker>_<timestamp>_trades.csv
    ├── <ticker>_<timestamp>_kc.png
    ├── <ticker>_<timestamp>_equity.png
    ├── <ticker>_<timestamp>_drawdown.png
    ├── <ticker>_<timestamp>_params.json
    ├── <ticker>_<timestamp>_metrics.json
    ├── <ticker>_<timestamp>_metrics.csv
    ├── <ticker>_<timestamp>_report.pdf
    └── <ticker>_<timestamp>_summary.txt
```

---

## HOW TO RUN (WEB APP MODE)

---

1. **Start the Streamlit app:**

   ```bash
   streamlit run app.py
   ```

2. **Open in browser:**

   ```
   http://localhost:8501
   ```

3. **Optional LAN sharing:**

   ```bash
   streamlit run app.py --server.address 0.0.0.0 --server.port 8501
   ```

Use the sidebar to configure inputs, run tests, and view all results interactively.
Each run is stored in a **subfolder for that ticker** inside your chosen root folder.

---

## OUTPUT STRUCTURE

---

Each ticker’s run produces:

```
<root>/
└── <TICKER>/
    ├── runs_log.csv
    ├── <TICKER>_<timestamp>_kc.csv
    ├── <TICKER>_<timestamp>_trades.csv
    ├── <TICKER>_<timestamp>_metrics.json
    ├── <TICKER>_<timestamp>_metrics.csv
    ├── <TICKER>_<timestamp>_report.pdf
    └── other PNG and TXT files
```

**Note:**
`runs_log.csv` is now saved **inside each ticker folder** for versioned tracking.

---

## TECHNICAL TERMS SIMPLIFIED

---

* **EMA (Exponential Moving Average):** Smooths prices for trend detection
* **ATR (Average True Range):** Measures volatility
* **Multiplier:** Expands or contracts the channel width
* **Risk (%):** Fraction of capital per trade
* **Stop/TP multiples:** ATR-based exit levels
* **Fee_bps / Slip_bps:** Transaction cost in basis points
* **CAGR:** Annual growth rate
* **Sharpe / Sortino:** Risk-adjusted returns
* **Max Drawdown:** Largest equity drop

---

## LIMITATIONS

---

* Works on daily OHLC data
* Single instrument per run
* No dividend or corporate action adjustments
* For educational and research use only

---

## FUTURE IMPROVEMENTS

---

* Portfolio-level testing
* Parameter optimization
* Multi-asset batch comparison
* Trend filters (e.g. SMA200 confirmation)
* Enhanced dashboards and visual themes

---

## AUTHOR

---

Developed by **Pramit Datta**
