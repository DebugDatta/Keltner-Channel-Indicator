KELTNER CHANNEL INDICATOR PROJECT
---------------------------------

A complete Python project that calculates, visualizes, and backtests the **Keltner Channel** — a volatility-based technical indicator used by traders to identify price trends, breakouts, and potential reversals.

This project uses real market data (via yfinance) to simulate trades, apply risk management, and measure performance metrics like CAGR, Sharpe Ratio, and Drawdown.  
It is built to help students, traders, and data enthusiasts understand how volatility bands work and how to test a simple yet powerful trading system.

---------------------------------
WHAT IS THE KELTNER CHANNEL?
---------------------------------
The **Keltner Channel** is a type of trading envelope that adjusts itself based on market volatility.  
It consists of three lines plotted around the price:

1. **Middle Line (EMA)** – The Exponential Moving Average (EMA) of the closing price over a specific period.  
2. **Upper Band** – EMA + (Average True Range × Multiplier)  
3. **Lower Band** – EMA - (Average True Range × Multiplier)

The **Average True Range (ATR)** measures how volatile the market is, while the **Multiplier** controls how wide the channel spreads from the EMA.

Interpretation:
- When prices move **above the upper band**, it suggests strong upward momentum or a potential breakout.
- When prices move **below the lower band**, it signals strong downward momentum or a breakdown.
- Prices oscillating inside the channel indicate a consolidating or range-bound market.

Traders use this indicator to:
• Identify trend directions  
• Spot breakouts and reversals  
• Set dynamic stop losses and profit targets based on volatility  

---------------------------------
PROJECT OVERVIEW
---------------------------------
This project automates:
1. **Data Collection** – Fetches price data from Yahoo Finance.  
2. **Indicator Calculation** – Computes EMA, ATR, and the Keltner Channel bands.  
3. **Signal Generation** – Generates buy/sell signals when prices break out of the channel.  
4. **Backtesting** – Simulates trades using realistic assumptions like fees, slippage, and position sizing.  
5. **Performance Analysis** – Calculates CAGR, Sharpe, Sortino, Drawdown, and other metrics.  
6. **Visualization** – Plots the price chart, Keltner Channel, equity curve, and drawdown graph.

---------------------------------
KEY FEATURES
---------------------------------
• Supports both **stocks** and **cryptocurrencies** (e.g., AAPL, NVDA, RELIANCE.NS, BTC-USD)  
• Interactive mode for easy parameter input  
• Command-line mode for automation  
• Customizable risk, stop-loss, and take-profit levels  
• Realistic transaction fees and slippage modeling  
• Automatically generates performance charts and CSV trade logs  

---------------------------------
HOW TO SET UP
---------------------------------
1. Clone this repository: 
   ```bash
   git clone https://github.com/DebugDatta/Keltner-Channel-Indicator.git 
   ```

3. Enter the folder: 
   ```bash
   cd Keltner-Channel-Indicator 
   ```

4. Create a virtual environment: 
   ```bash
   python -m venv venv 
   ```

5. Activate it:
    
   • Windows →
   ```bash
   venv\Scripts\activate
   ```
   • macOS/Linux →
   ```bash
   source venv/bin/activate
   ```

7. Install dependencies: 
   ```bash
   pip install -r requirements.txt
   ```

---------------------------------
HOW TO RUN
---------------------------------
Option 1: Interactive Mode  
python run_backtest.py --interactive  
The program will ask for: 
```bash
- Ticker (AAPL, BTC-USD, RELIANCE.NS, etc.)
- Date range or period
- EMA, ATR, Multiplier
- Risk, Stop loss, Take profit
- Trade side (long_only, short_only, long_short)
- Execution mode (next_open, next_close)
- Fees, slippage, output folder 
```

Option 2: Command-Line Mode  
```bash
   python run_backtest.py --ticker RELIANCE.NS --start 2015-01-01 --end 2025-01-01 --ema 25 --atr 14 --mult 2.5 --risk 0.01 --stop 2.5 --tp 4.0 --side long_only --execution next_open --fee_bps 3 --slip_bps 5 --warmup 50 --outdir out_reliance

  ```


---------------------------------
OUTPUT FILES
---------------------------------
All results are automatically saved in your output folder:
```bash
• <ticker>_kc.csv → Data with indicators and signals  
• trades_<ticker>.csv → Detailed trade logs (entries, exits, PnL)  
• <ticker>_kc.png → Price chart with Keltner Channel  
• <ticker>_equity.png → Portfolio growth chart  
• <ticker>_drawdown.png → Drawdown curve  
```

---------------------------------
TECHNICAL TERMS SIMPLIFIED
---------------------------------
• **EMA (Exponential Moving Average):** Smoothed average that reacts faster to recent prices.  
• **ATR (Average True Range):** Measures daily volatility.  
• **Multiplier:** Controls the channel width; higher = fewer signals.  
• **Risk (%):** Fraction of capital risked per trade.  
• **Stop Loss / Take Profit:** Exit conditions based on multiples of ATR.  
• **Fee_bps / Slip_bps:** Trading costs in basis points (1bps = 0.01%).  
• **CAGR:** Compound Annual Growth Rate, average yearly return.  
• **Sharpe / Sortino:** Risk-adjusted performance ratios.  
• **Max Drawdown:** Largest loss from portfolio peak to trough.  

---------------------------------
LIMITATIONS
---------------------------------
• Works on daily data only (not intraday).  
• Tests one instrument at a time.  
• Does not include dividends or corporate actions.  
• Strategy is basic — best used for learning, not real-money trading.  

---------------------------------
FUTURE IMPROVEMENTS
---------------------------------
• Add portfolio-level backtesting  
• Optimize parameters automatically  
• Support multiple data sources  
• Integrate trend filters (e.g., SMA200 confirmation)  

---------------------------------
LICENSE
---------------------------------
MIT License © 2025 Pramit  
Free to use, modify, and share for research and educational purposes.

---------------------------------
AUTHOR
---------------------------------
Developed by Pramit Datta
