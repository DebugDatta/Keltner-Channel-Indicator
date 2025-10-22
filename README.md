KELTNER CHANNEL INDICATOR PROJECT

This project calculates the Keltner Channel indicator and tests how a basic trading idea using it would perform.

WHAT IT DOES
- Downloads stock data automatically using yfinance
- Calculates the Keltner Channel which consists of three lines:
  - A middle line that is an Exponential Moving Average (EMA)
  - An upper and a lower line that are based on Average True Range (ATR)
- Generates buy and sell points based on price crossing these lines
- Simulates trades and shows results with profits, losses, and charts

FOLDER STRUCTURE
src/
│
├─ data.py          → downloads and cleans stock data
├─ indicators.py    → calculates EMA, ATR, and Keltner Channel
├─ strategy.py      → defines buy and sell logic
├─ backtester.py    → simulates trades over historical data
├─ plotting.py      → makes graphs for visualization
├─ run_backtest.py  → main file that connects everything
├─ out/             → saves all outputs like csv and charts
└─ requirements.txt → contains list of required python libraries

INSTALLATION
1. open command prompt or terminal in project folder  
2. type and run: pip install -r requirements.txt  

USAGE
To run for Apple stock example:
python -m src.run_backtest --ticker AAPL --start 2018-01-01 --end 2025-01-01

For Indian stocks example:
python -m src.run_backtest --ticker RELIANCE.NS --period 5y

You can adjust settings:
--ema       number of periods for EMA (default 20)
--atr       number of periods for ATR (default 10)
--mult      multiplier for ATR (default 2)
--risk      capital risk per trade (default 1%)
--stop      stop loss multiple of ATR
--tp        take profit multiple of ATR
--side      choose long_only, short_only or long_short
--fee_bps   transaction fee in basis points (1 bps = 0.01%)
--slip_bps  slippage in basis points

OUTPUT FILES (saved in src/out/)
<ticker>_kc.csv → data with indicator values and signals  
trades_<ticker>.csv → all trades with entry, exit, and pnl  
<ticker>_kc.png → price chart with keltner bands and trades  
<ticker>_equity.png → total portfolio growth line  
<ticker>_drawdown.png → shows biggest losses from peaks  

HOW IT WORKS STEP BY STEP
1. Data is downloaded using yfinance (daily open, high, low, close, volume)
2. Typical Price = (High + Low + Close) / 3
3. EMA is calculated on this typical price for smoothing
4. True Range is calculated for each day as the largest of:
   (High - Low), (High - previous Close), (Low - previous Close)
5. ATR = EMA of True Range over chosen period
6. Channel lines are built as:
   Upper Band = EMA + ATR * multiplier
   Lower Band = EMA - ATR * multiplier
7. Buy signal when price crosses above upper band
8. Sell signal when price crosses below middle line
9. Backtester simulates entering and exiting trades with given fees and slippage
10. Final charts show results of trading over time

MEANINGS OF TECHNICAL TERMS
EMA (Exponential Moving Average) → smooths price data and reacts faster to new prices  
ATR (Average True Range) → measures how much price moves daily, shows volatility  
PnL (Profit and Loss) → money gained or lost from each trade  
Slippage → small difference between expected and actual trade price due to market movement  
Basis Points → one basis point = 0.01 percent, used to describe small costs  
Drawdown → drop from portfolio high to next low, shows worst loss from top  
Sharpe Ratio → return divided by volatility, shows reward per unit of risk  
CAGR → average yearly growth rate of the portfolio  

LIMITATIONS
- Uses daily data only, no intraday or real-time use  
- Only one stock tested at a time  
- Strategy is simple breakout logic, not optimized for all markets  
- Does not include dividends or corporate events  

POSSIBLE IMPROVEMENTS
- Add long-only and trend filters like EMA200  
- Add trailing stops and partial exits  
- Allow multiple stocks and portfolio testing  
- Add optimization to test different parameter combinations  

AUTHOR
Made by Pramit  
Language used: Python  
Goal: learn financial data analysis, indicators, and backtesting from scratch
