RSQM WATCHLIST GENERATOR
========================

This project generates a **Relative Strength Quant Model (RSQM) watchlist** 
for NSE stocks. It fetches price data, calculates absolute and relative returns, 
and produces a ranked list of the strongest momentum stocks.

-------------------------------------------------
FILES
-------------------------------------------------
1. rsqm_watchlist.py        → Main Python script
2. ind_nifty100list.csv     → Local ticker universe (Nifty100 list)
3. RSQM_watchlist.csv       → Output: Top 15 leaders (CSV)
4. RSQM_watchlist.xlsx      → Output: Top 15 leaders (Excel)
5. README.txt               → This help file

-------------------------------------------------
PREREQUISITES
-------------------------------------------------
Python version:
    Python 3.10 or higher is recommended.

Required Python packages:
    pandas
    yfinance
    tenacity
    openpyxl

To install all dependencies, run:
    pip install pandas yfinance tenacity openpyxl

-------------------------------------------------
HOW TO RUN
-------------------------------------------------
1. Download or clone this project folder.

2. Place the stock universe file (`ind_nifty100list.csv`) 
   in the same directory as the script.
   - If the file is missing, the script will try to fetch
     the official list from NSE’s website.

3. Open a terminal (Command Prompt / PowerShell / Linux shell) 
   in the project folder.

4. Run the script:
       python rsqm_watchlist.py

5. On successful completion, outputs will be generated:
   - RSQM_watchlist.csv
   - RSQM_watchlist.xlsx

-------------------------------------------------
CALCULATIONS
-------------------------------------------------
The model computes:

- **Absolute Returns**:
      AbsRet_30D   → 30-day return (%)
      AbsRet_90D   → 90-day return (%)
      AbsRet_180D  → 180-day return (%)

- **Relative Strength (RS)** vs Benchmark (^NSEI):
      RelStr_30D   → Stock return ÷ NIFTY return (30 days)
      RelStr_90D   → Stock return ÷ NIFTY return (90 days)
      RelStr_180D  → Stock return ÷ NIFTY return (180 days)

- **RS Score**:
      Average of relative strengths across all periods.

- **Rank**:
      Ranking by RS Score (descending). Top 15 are exported.

-------------------------------------------------
ABOUT RSQM
-------------------------------------------------
The **Relative Strength Quant Model (RSQM)** is a systematic way to find 
stocks that are outperforming the market (NIFTY benchmark). Instead of 
looking only at raw price gains, RSQM measures performance **relative to 
the index**.

Why this matters:
- In a bull market, leaders outperform the index strongly.
- In a sideways market, strong RS stocks resist falling and hold up better.
- In a bear market, RSQM can highlight **anti-fragile stocks** (falling 
  less than the index or still rising).

-------------------------------------------------
WHY RSQM HELPS SWING TRADING
-------------------------------------------------
Swing traders aim to capture medium-term (days to weeks) price moves.  
The RSQM approach helps by:

1. **Focus on Leaders**  
   Highlights the **top 15–20 strongest stocks**, more likely to trend 
   and give clean swing setups.

2. **Avoid Weak Stocks**  
   Filters out low-RS underperformers, keeping capital focused on leaders.

3. **Momentum Confirmation**  
   High RS scores indicate sustained momentum, improving swing entry odds.

4. **Multi-Timeframe Strength**  
   Combines 30D, 90D, and 180D performance, ensuring short-term moves are 
   backed by medium-term momentum.

5. **Benchmark Awareness**  
   RSQM compares to NIFTY, so you always know if a stock is a true leader 
   or just moving with the market.

-------------------------------------------------
NOTES
-------------------------------------------------
- Benchmark used: ^NSEI (Nifty 50 Index).
- Script fetches ~400 days of data for calculation.
- CSV/Excel outputs include **absolute returns, relative strength, RS Score, Rank**.
- Stable internet connection is required to fetch stock data.

-------------------------------------------------
AUTHOR
-------------------------------------------------
Created by: Aryashree Pritikrishna  
Principal Architect | Full Stack, DevOps, Security  
LinkedIn: https://www.linkedin.com/in/aryashreep  
GitHub:   https://github.com/aryashreep
