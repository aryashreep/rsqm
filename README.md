# RSQM WATCHLIST GENERATOR

The **Relative Strength Quant Model (RSQM) Watchlist Generator** is a Python-based tool for identifying the strongest momentum stocks in the NSE universe. It automates data fetching, calculates absolute and relative returns, and ranks stocks by their outperformance versus the Nifty 50 benchmark.

---

## WHAT IS THE RELATIVE STRENGTH QUANT MODEL (RSQM)?

The Relative Strength Quant Model (RSQM) is a systematic approach to stock selection that focuses on identifying equities consistently outperforming a benchmark index (Nifty 50). It leverages quantitative analysis of price momentum across multiple timeframes to rank stocks by their relative strength.

### Key Concepts

- **Relative Strength (RS):**  
   Measures how much a stock has outperformed or underperformed the benchmark index over a specific period. RS > 1 indicates outperformance.

- **Multi-Period Analysis:**  
   RSQM evaluates returns over 30, 90, and 180 days to capture both short-term and medium-term momentum.

- **RS Score:**  
   An aggregate metric combining relative strength values from all periods, providing a holistic view of a stock’s leadership.

- **Ranking & Filtering:**  
   Stocks are ranked by RS Score, and only the top performers are selected for the watchlist.

### Why Use RSQM?

- **Objective Selection:**  
   Removes emotion and bias from stock picking by relying on data-driven metrics.

- **Market Leadership:**  
   Focuses on stocks that are not just rising, but outperforming the broader market.

- **Adaptability:**  
   Can be applied to different universes (Nifty 50, 100, 200, 500) and timeframes.

- **Ease of Use:**  
   Automates data collection, calculation, and output generation for efficient workflow.

RSQM is ideal for traders and investors seeking to identify momentum leaders and build watchlists based on proven quantitative methods.

## FEATURES

- **Automated Data Fetching:** Downloads historical price data for all stocks in the Nifty 100 universe and the Nifty 50 index.
- **Robust Error Handling:** Uses retry logic to handle network issues and missing tickers.
- **Absolute & Relative Returns:** Calculates returns over 30, 90, and 180 days for each stock.
- **Relative Strength Scoring:** Measures each stock’s performance relative to the Nifty 50 index.
- **Ranking & Filtering:** Ranks stocks by RS Score and exports the top 15 leaders.
- **Multi-format Output:** Generates both CSV and Excel files for easy analysis.
- **Automatic Universe Update:** If the local universe file is missing, fetches the latest list from NSE’s official website.

---

## OUTPUT COLUMNS EXPLAINED

| Column        | Description                                                      |
| ------------- | ---------------------------------------------------------------- |
| `Ticker`      | Stock symbol (NSE code)                                          |
| `AbsRet_30D`  | Absolute return over last 30 days (%)                            |
| `RelStr_30D`  | Relative strength vs Nifty 50 over 30 days                       |
| `AbsRet_90D`  | Absolute return over last 90 days (%)                            |
| `RelStr_90D`  | Relative strength vs Nifty 50 over 90 days                       |
| `AbsRet_180D` | Absolute return over last 180 days (%)                           |
| `RelStr_180D` | Relative strength vs Nifty 50 over 180 days                      |
| `RS Score`    | Average of all relative strength values (overall outperformance) |
| `Rank`        | Position in RS Score ranking (1 = strongest)                     |

---

## FILES

- `rsqm_watchlist.py` – Main script for generating the watchlist.
- `ind_nifty100list.csv` – Local universe file (Nifty 100 tickers).
- `RSQM_watchlist.csv` – Output: Top 15 leaders (CSV).
- `RSQM_watchlist.xlsx` – Output: Top 15 leaders (Excel).
- `requirements.txt` – List of required Python packages.
- `README.md` – This help file.

---

## INSTALLATION

1. **Clone or Download the Repository:**

   - Place all files in a single folder.

2. **Install Python Packages:**
   - Open a terminal in the project folder.
   - Run:
     ```
     pip install -r requirements.txt
     ```

---

## USAGE

1. **Prepare Universe File:**

   - Ensure `ind_nifty100list.csv` is present in the folder.
   - If missing, the script will auto-download the latest list from NSE.

2. **Run the Script:**

   - In the terminal, execute:
     ```
      python rsqm_scanner.py 100
      # Usage: python rsqm_scanner.py <Nifty_Scope>
      # Nifty_Scope must be one of: 50, 100, 200, or 500.
     ```

3. **Review Outputs:**
   - On completion, check:
     - `RSQM_watchlist.csv`
     - `RSQM_watchlist.xlsx`

---

## CALCULATION LOGIC

- **Absolute Returns:**

  - `AbsRet_30D`, `AbsRet_90D`, `AbsRet_180D` – Percentage returns over 30, 90, and 180 days.

- **Relative Strength (RS):**

  - `RelStr_30D`, `RelStr_90D`, `RelStr_180D` – Stock return divided by Nifty 50 return for each period.

- **RS Score:**

  - Average of all relative strength values.

- **Ranking:**
  - Stocks are ranked by RS Score (descending). Top 15 are exported.

---

## ADVANTAGES OF RSQM

- **Leader Identification:**  
  Focuses on stocks outperforming the index, ideal for swing and momentum trading.

- **Multi-Timeframe Analysis:**  
  Combines short and medium-term strength for robust selection.

- **Benchmark Awareness:**  
  Ensures selected stocks are true market leaders, not just rising with the tide.

- **Resilience Detection:**  
  Highlights stocks that fall less or rise more than the index in all market conditions.

---

## REQUIREMENTS

- Python 3.10 or higher.
- Internet connection for data fetching.
- Required packages: pandas, yfinance, tenacity, openpyxl, numpy.

---

## TROUBLESHOOTING

- **Missing Universe File:**  
  The script will attempt to download the latest Nifty 100 list if `ind_nifty100list.csv` is absent.

- **Data Fetch Errors:**  
  Network issues are handled with retries. Ensure stable internet.

- **Output Issues:**  
  Check for write permissions in the project folder.

---

## AUTHOR

Created by: Aryashree Pritikrishna  
Principal Architect | Full Stack, DevOps, Security  
[LinkedIn](https://www.linkedin.com/in/aryashreep)  
[GitHub](https://github.com/aryashreep)
