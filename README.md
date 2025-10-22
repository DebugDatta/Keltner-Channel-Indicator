KELTNER CHANNEL INDICATOR PROJECT
---------------------------------

A Python project to calculate and backtest the Keltner Channel — a volatility-based trading indicator.  
It downloads real stock data, generates trading signals, simulates trades with realistic costs,  
and visualizes results with clear charts and performance metrics.

---------------------------------
WHAT THIS PROJECT DOES
---------------------------------
• Downloads stock data using yfinance  
• Calculates the Keltner Channel (EMA as middle line, ATR-based upper and lower bands)  
• Generates buy and sell signals based on price breakouts  
• Runs a backtest that simulates trades with transaction costs and slippage  
• Saves detailed trade results, indicator data, and performance charts  

---------------------------------
PROJECT STRUCTURE
---------------------------------
project/
|
├─ backtester.py      → runs the backtesting engine  
├─ data.py            → fetches and prepares stock data  
├─ indicators.py      → calculates EMA, ATR, and Keltner Channels  
├─ plotting.py        → plots price, equity, and drawdown charts  
├─ run_backtest.py    → main script to execute the full process  
├─ strategy.py        → defines buy and sell conditions  
├─ requirements.txt   → required Python libraries  
├─ README.md          → documentation (this file)  
├─ LICENSE            → MIT license for open usage  
└─ .gitignore         → ignores unnecessary files in version control  

---------------------------------
INSTALLATION
---------------------------------
1. Open your terminal or command prompt in the project folder.  
2. Run the command:
   ```bash 
   pip install -r requirements.txt
   ``` 

---------------------------------
USAGE
---------------------------------
Run for Apple stock:
```bash
python run_backtest.py --ticker AAPL --start 2018-01-01 --end 2025-01-01  
```
Run for Indian stocks:
```bash
python run_backtest.py --ticker RELIANCE.NS --period 5y
```

You can modify parameters:
--ema       number of periods for EMA (default 20)  
--atr       number of periods for ATR (default 10)  
--mult      multiplier for ATR (default 2)  
--risk      risk per trade as a fraction of capital (default 0.01)  
--stop      stop loss multiple of ATR  
--tp        take profit multiple of ATR  
--side      choose long_only, short_only, or long_short  
--fee_bps   transaction cost (basis points, 1 bps = 0.01%)  
--slip_bps  slippage cost (basis points)  

---------------------------------
OUTPUT FILES
---------------------------------
All results are saved automatically in the project folder:  

• <ticker>_kc.csv → data with indicator and signals  
• trades_<ticker>.csv → detailed trade log  
• <ticker>_kc.png → price chart with Keltner Channel  
• <ticker>_equity.png → equity growth chart  
• <ticker>_drawdown.png → drawdown (loss) chart  

---------------------------------
HOW IT WORKS
---------------------------------
1. Downloads daily OHLC data (Open, High, Low, Close)  
2. Calculates the typical price: (High + Low + Close) / 3  
3. Computes EMA (Exponential Moving Average) for smoothing  
4. Calculates True Range (TR) for volatility:  
   TR = max(High - Low, |High - PrevClose|, |Low - PrevClose|)  
5. ATR (Average True Range) = EMA of TR over selected period  
6. Builds the channel:  
   Upper Band = EMA + ATR × multiplier  
   Lower Band = EMA - ATR × multiplier  
7. Entry and exit logic:  
   - Buy when price crosses above upper band  
   - Sell when price crosses below middle line  
8. The backtester simulates trades, applies costs, and records profits/losses  
9. Final output shows performance over time  

---------------------------------
TECHNICAL TERMS (SIMPLE EXPLANATION)
---------------------------------
EMA (Exponential Moving Average) → A smooth average giving more weight to recent prices  
ATR (Average True Range) → Measures daily price volatility or movement range  
PnL (Profit and Loss) → How much money was made or lost in each trade  
Slippage → Difference between expected and actual trade price  
Basis Point (bps) → 0.01%, used to measure small fees  
Drawdown → Largest fall from portfolio high to low  
Sharpe Ratio → Measures return versus risk, higher is better  
CAGR → Compound Annual Growth Rate, average yearly portfolio growth  

---------------------------------
LIMITATIONS
---------------------------------
• Uses daily data only  
• Tests one stock at a time  
• Simple breakout rules (not optimized)  
• Does not include dividends or split adjustments  

---------------------------------
FUTURE IMPROVEMENTS
---------------------------------
• Add long-only and trend filters (like EMA200)  
• Add trailing stops and re-entry rules  
• Support multiple stocks and portfolios  
• Add automatic parameter optimization  

---------------------------------
LICENSE
---------------------------------
MIT License © 2025 Pramit  
Free to use, modify, and distribute for learning and research purposes.  

---------------------------------
AUTHOR
---------------------------------
Developed by Pramit Datta
