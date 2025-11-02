# KELTNER CHANNEL INDICATOR PROJECT (GUI EDITION)

---

A complete Python project with a **Tkinter-based GUI** and a **Streamlit web app** that calculates, visualizes, and backtests the **Keltner Channel** — a volatility-based technical indicator used by traders to identify trends, breakouts, and reversals.

This project lets you interact with sliders, dropdowns, and file choosers directly in a graphical interface — no terminal needed.
You can also use the web app in your browser with interactive dashboards, CSV views, and a PDF report builder.

It uses live data from Yahoo Finance, runs a backtest, displays metrics and plots in the same window or browser, and saves all results automatically.

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

Traders use the Keltner Channel to identify trend direction, catch breakouts early, and set stop-loss or take-profit levels that adapt to volatility.

---

## PROJECT OVERVIEW

---

The app automates:

1. **Data Fetching** – Pulls OHLC data from Yahoo Finance
2. **Indicator Computation** – Calculates EMA, ATR, and Keltner Channel
3. **Signal Generation** – Detects entry and exit points from breakouts
4. **Backtesting** – Simulates trades with risk, slippage, and fees
5. **Performance Metrics** – Computes CAGR, Sharpe, Sortino, Max Drawdown, Exposure, etc
6. **Visualization** – Shows price, equity, and drawdown charts
7. **Export** – Saves metrics, CSVs, PNGs, and a PDF report with inputs, metrics, and charts

---

## KEY FEATURES

---

* **Tkinter GUI**

  * Ticker input, period or dates, side, execution
  * Sliders for EMA, ATR, multiplier, risk, stop × ATR, optional take-profit × ATR
  * Folder chooser to save results
  * Embedded Matplotlib charts and live metrics
  * Per ticker subfolder creation and run registry

* **Streamlit Web App**

  * Same inputs and strategy as GUI
  * Sliders with a single compact value box under each slider
  * Tabs:

    * **Backtest** – interactive OHLC with Keltner, equity, drawdown
    * **KC CSV** – full Keltner Channel dataset table
    * **Trades Explorer** – filters, table from saved trades CSV, R histogram
    * **Run History** – aggregates all `runs_log.csv` from each ticker subfolder
    * **Report Builder** – one click PDF with inputs, metrics, and selected charts
  * Per ticker subfolder creation under the chosen root
  * **`runs_log.csv` saved inside each ticker subfolder**
  * Download buttons for CSVs, optional ZIP of a run

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

1. Enter a ticker, for example `AAPL`, `RELIANCE.NS`, `BTC-USD`
2. Choose period or date range
3. Adjust EMA, ATR, Multiplier, Risk %, Stop × ATR, optional Take-Profit × ATR
4. Pick Side `long_only`, `short_only`, or `long_short` and Execution `next_open` or `next_close`
5. Click **Choose Folder**
6. Click **Run Backtest**

The app will download data, run the strategy, show metrics and charts, and save:

```
<output_root>/
│
└── <ticker>/
    ├── runs_log.csv
    │
    ├── <ticker>_<timestamp>_kc.csv
    ├── <ticker>_<timestamp>_trades.csv
    ├── <ticker>_<timestamp>_kc.png
    ├── <ticker>_<timestamp>_equity.png
    ├── <ticker>_<timestamp>_drawdown.png
    ├── <ticker>_<timestamp>_params.json
    ├── <ticker>_<timestamp>_metrics.json
    ├── <ticker>_<timestamp>_metrics.csv
    └── <ticker>_<timestamp>_summary.txt
```

---

## HOW TO RUN (WEB APP MODE)

---

1. Start the Streamlit app:

   ```bash
   streamlit run app.py
   ```

2. Open in your browser:

   ```
   http://localhost:8501
   ```

3. For LAN access:

   ```bash
   streamlit run app.py --server.address 0.0.0.0 --server.port 8501
   ```

Use the sidebar to set inputs and the root save folder.
The app will create a **per ticker subfolder** and save all outputs there, including `runs_log.csv` inside that subfolder.

---

## OUTPUTS SAVED

---

* **CSV**

  * Keltner Channel data `*_kc.csv`
  * Trades `*_trades.csv`
  * Metrics `*_metrics.csv`
  * Run registry `runs_log.csv` inside each ticker subfolder

* **JSON**

  * Parameters `*_params.json`
  * Metrics `*_metrics.json`

* **Images**

  * `*_kc.png`, `*_equity.png`, `*_drawdown.png`

* **PDF**

  * Report with inputs, metrics, and selected charts

* **TXT**

  * `*_summary.txt` with inputs and metrics

All filenames include the timestamp.

---

## TECHNICAL TERMS SIMPLIFIED

---

* **EMA:** Fast trend average
* **ATR:** Volatility gauge
* **Multiplier:** Channel width factor
* **Risk (%):** Fraction of capital risked per trade
* **Stop/TP multiples:** ATR based exits
* **Fee_bps / Slip_bps:** Costs in basis points
* **CAGR:** Annualized growth
* **Sharpe / Sortino:** Risk adjusted returns
* **Max Drawdown:** Peak to trough fall

---

## LIMITATIONS

---

* Daily OHLC data only
* Single instrument per run
* No dividends or corporate actions
* Research use, not live trading

---

## FUTURE IMPROVEMENTS

---

* Portfolio backtests
* Parameter sweeps and optimization
* Multi asset comparisons
* Trend filters like SMA200
* More report layouts

---

## AUTHOR

---

Developed by **Pramit Datta**
