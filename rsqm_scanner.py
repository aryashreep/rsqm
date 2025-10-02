import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_fixed
import numpy as np
import sys # <-- Added for command-line arguments

# -------------------------------
# 1. Load tickers from local or fallback
# -------------------------------
def load_tickers(scope):
    """
    Loads NSE tickers based on the specified Nifty index scope (50, 100, 200, 500).
    It first tries a local copy, then falls back to downloading the list online.
    
    Args:
        scope (int): The Nifty index scope (e.g., 100 for Nifty100).
    """
    scope_str = str(scope)
    local_filepath = f"ind_nifty{scope_str}list.csv"
    
    def process_df(df):
        # Filter out NaN or non-string symbols, then append the .NS suffix
        valid_symbols = [symbol for symbol in df['Symbol'].tolist() if isinstance(symbol, str) and pd.notna(symbol)]
        return [f"{symbol}.NS" for symbol in valid_symbols]
        
    # Attempt 1: Load from local file
    if os.path.exists(local_filepath):
        print(f"📂 Using local copy of Nifty{scope_str} list ({local_filepath})...")
        try:
            df = pd.read_csv(local_filepath)
            return process_df(df)
        except Exception as e:
            print(f"⚠️ Error reading local file: {e}.")

    # Attempt 2: Download from NSE archives
    url = f"https://nsearchives.nseindia.com/content/indices/ind_nifty{scope_str}list.csv"
    try:
        df = pd.read_csv(url)
        print(f"🌐 Using online Nifty{scope_str} list from {url}...")
        return process_df(df)
    except Exception as e:
        print(f"❌ Failed to fetch Nifty{scope_str} tickers online: {e}")
        return []


# -------------------------------
# 2. Retryable single ticker fetch
# -------------------------------
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def fetch_single_ticker(ticker, start, end):
    """Fetch single ticker with retries."""
    data = yf.download(
        ticker,
        start=start,
        end=end,
        progress=False,
        auto_adjust=False,
        timeout=10
    )
    if data.empty:
        raise ValueError(f"No data for {ticker}")
    return data["Adj Close"] if "Adj Close" in data.columns else data["Close"]


# -------------------------------
# 3. Main fetch (batch → fallback)
# -------------------------------
def fetch_data(tickers, benchmark="^NSEI", lookback_days=400):
    """
    Attempts a batch download for all tickers, falling back to individual
    downloads with retries if the batch fails or is incomplete.
    """
    end = datetime.today()
    start = end - timedelta(days=lookback_days)
    all_tickers = tickers + [benchmark]

    print(f"\n⚡ Attempting fast batch download for {len(all_tickers)} symbols...")
    try:
        batch_data = yf.download(
            all_tickers,
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,
            group_by="ticker"
        )

        # Handle MultiIndex structure from yfinance batch download
        if isinstance(batch_data.columns, pd.MultiIndex):
            if "Adj Close" in batch_data.columns.levels[1]:
                batch_data = batch_data.xs("Adj Close", axis=1, level=1, drop_level=True)
            elif "Close" in batch_data.columns.levels[1]:
                batch_data = batch_data.xs("Close", axis=1, level=1, drop_level=True)

        # Check if benchmark is present and not empty
        if benchmark in batch_data.columns and not batch_data[benchmark].dropna().empty:
            print("✅ Batch download successful.")
            return batch_data
        else:
            print(f"⚠️ Benchmark {benchmark} missing in batch. Falling back to individual downloads...")

    except Exception as e:
        print(f"⚠️ Batch download failed due to: {e}")
        print("➡️ Switching to individual downloads with retries...")

    # ---- Fallback: individual downloads ----
    price_data = {}
    for i, ticker in enumerate(all_tickers):
        print(f"  Fetching {ticker} ({i+1}/{len(all_tickers)})...", end="\r")
        try:
            series = fetch_single_ticker(ticker, start, end)
            price_data[ticker] = series
        except Exception:
            # Error message already handled by retry mechanism/ValueError
            print(f"❌ {ticker} failed after retries.")

    # Remove the progress line from console
    print(" " * 60, end="\r") 

    if not price_data:
        print("🛑 All downloads failed.")
        return pd.DataFrame()

    data_df = pd.concat(price_data.values(), axis=1, keys=price_data.keys())

    if benchmark in data_df.columns and not data_df[benchmark].dropna().empty:
        print("✅ Individual downloads successful with benchmark.")
    else:
        print(f"⚠️ Benchmark {benchmark} still missing. Proceeding without it.")
    return data_df


# -------------------------------
# 4. RSQM computation (returns + relative)
# -------------------------------
def compute_rsqm(data, tickers, benchmark="^NSEI"):
    """
    Calculates Absolute Returns and Relative Strength for multiple lookback periods,
    then computes the final RS Score.
    """
    lookbacks = {"30D": 30, "90D": 90, "180D": 180}
    
    # Filter data columns to only include the requested tickers and benchmark
    cols_to_use = [t for t in tickers if t in data.columns]
    if benchmark in data.columns:
        cols_to_use.append(benchmark)
        
    data = data[cols_to_use].copy()
    rsqm = pd.DataFrame(index=tickers)

    if benchmark not in data.columns:
        print(f"⚠️ Benchmark {benchmark} missing, computing only absolute returns.")
        for label, days in lookbacks.items():
            # Calculate absolute return for each ticker
            rsqm[f"AbsRet_{label}"] = data[tickers].pct_change(days).iloc[-1, :].mul(100)
            
        rsqm["RS Score"] = rsqm[[col for col in rsqm.columns if "AbsRet" in col]].mean(axis=1)
        rsqm["Rank"] = rsqm["RS Score"].rank(ascending=False)
        # Filter for top 15 and remove any non-Nifty stocks that might have snuck in (though unlikely here)
        return rsqm.dropna(subset=["RS Score"]).sort_values("RS Score", ascending=False).head(15)

    # --- Standard RSQM Calculation (with Benchmark) ---
    abs_returns = {}
    rel_strengths = {}
    
    # 1. Get benchmark returns for all lookbacks
    bench_returns = {
        label: data[benchmark].pct_change(days).iloc[-1].item() * 100
        for label, days in lookbacks.items()
    }
    
    for label, days in lookbacks.items():
        # Absolute returns (for all stocks)
        returns = data.pct_change(days).iloc[-1, :].mul(100)
        abs_returns[label] = returns.drop(benchmark, errors='ignore') # Don't include benchmark in output

        # Relative strength (Stock Return / Benchmark Return)
        bench_ret = bench_returns[label]
        if abs(bench_ret) > 0.0001: # Avoid division by near-zero
            # Use Numpy broadcasting for efficiency
            rel_strengths[label] = returns / bench_ret
        else:
            # If benchmark return is zero/near-zero, just use absolute return as relative strength
            rel_strengths[label] = returns

    # 2. Build Final DataFrame
    rsqm = pd.DataFrame(index=tickers)
    for label in lookbacks.keys():
        rsqm[f"AbsRet_{label}"] = abs_returns[label]
        # Only keep the relative strength for the target tickers, not the benchmark
        rsqm[f"RelStr_{label}"] = rel_strengths[label].drop(benchmark, errors='ignore')

    # 3. RS Score = average of relative strengths (RelStr_30D, RelStr_90D, RelStr_180D)
    rsqm["RS Score"] = rsqm[[f"RelStr_{lb}" for lb in lookbacks]].mean(axis=1)
    
    # 4. Rank and Filter
    rsqm["Rank"] = rsqm["RS Score"].rank(ascending=False)
    
    leaders = rsqm.dropna(subset=["RS Score"]).sort_values("RS Score", ascending=False).head(15)
    return leaders


# -------------------------------
# 5. Main workflow
# -------------------------------
if __name__ == "__main__":
    
    # --- Command-Line Argument Parsing ---
    VALID_SCOPES = [50, 100, 200, 500]
    
    if len(sys.argv) < 2:
        print("Usage: python rsqm_scanner.py <Nifty_Scope>")
        print(f"Nifty_Scope must be one of: {', '.join(map(str, VALID_SCOPES))}.")
        sys.exit(1)
        
    try:
        requested_scope = int(sys.argv[1])
    except ValueError:
        print(f"Error: Scope '{sys.argv[1]}' is not a valid number.")
        print(f"Nifty_Scope must be one of: {', '.join(map(str, VALID_SCOPES))}.")
        sys.exit(1)

    if requested_scope not in VALID_SCOPES:
        print(f"Error: Nifty Scope {requested_scope} is not supported.")
        print(f"Please choose one of: {', '.join(map(str, VALID_SCOPES))}.")
        sys.exit(1)
        
    INDEX_SCOPE = requested_scope
    # -------------------------------------
    
    tickers = load_tickers(scope=INDEX_SCOPE)
    if not tickers:
        print("No tickers available. Exiting.")
        sys.exit(1)

    # Use a longer lookback to ensure sufficient history for 180-day returns calculation
    data = fetch_data(tickers, benchmark="^NSEI", lookback_days=400) 

    if not data.empty:
        leaders = compute_rsqm(data, tickers, benchmark="^NSEI")

        if not leaders.empty:
            print(f"\n🔥 RSQM Watchlist (Top 15 Nifty {INDEX_SCOPE} Stocks):")
            # Display results, rounded to 2 decimal places
            print(leaders.round(2))

            # Export results
            csv_filename = f"RSQM_watchlist_Nifty{INDEX_SCOPE}.csv"
            excel_filename = f"RSQM_watchlist_Nifty{INDEX_SCOPE}.xlsx"
            
            leaders.round(2).to_csv(csv_filename)
            leaders.round(2).to_excel(excel_filename)

            # --- HTML Generation ---
            
            # Define column descriptions for tooltips (title attribute)
            COLUMN_DESCRIPTIONS = {
                'Ticker': 'Stock symbol (NSE code)',
                'Rank': 'Position in RS Score ranking (1 = strongest)',
                'RS Score': 'Average of all relative strength values (overall outperformance)',
                'AbsRet_30D': 'Absolute return over last 30 days (%)',
                'RelStr_30D': 'Relative strength vs Nifty 50 over 30 days',
                'AbsRet_90D': 'Absolute return over last 90 days (%)',
                'RelStr_90D': 'Relative strength vs Nifty 50 over 90 days',
                'AbsRet_180D': 'Absolute return over last 180 days (%)',
                'RelStr_180D': 'Relative strength vs Nifty 50 over 180 days',
            }

            # Prepare DataFrame for HTML
            df_html = leaders.reset_index().rename(columns={'index': 'Ticker'})
            
            # Format numeric columns with data-order attribute for JS sorting
            numeric_cols = [col for col in df_html.columns if col not in ['Ticker']]
            
            # Define fmt_num locally to capture 'col' correctly
            def fmt_num(val, col_name):
                # Check for NaN and return empty string if NaN
                if pd.isna(val):
                    return ""
                # Format as percentage if it's a return column
                if 'Ret_' in col_name:
                    return f'<span data-order="{val:.2f}">{val:.2f}%</span>'
                # Format as general number (Rank, RS Score, Relative Strength)
                return f'<span data-order="{val:.2f}">{val:.2f}</span>'

            # Apply formatting with the column name context
            for col in numeric_cols:
                # Use a lambda function to pass the column name to fmt_num
                df_html[col] = df_html[col].apply(lambda x: fmt_num(x, col)) 
                
            # Ticker column needs its suffix removed for display
            df_html['Ticker'] = df_html['Ticker'].str.replace(".NS", "", regex=False)
            
            header_names = df_html.columns.tolist()
            numeric_columns = header_names[1:] # All columns except Ticker are numeric metrics

            header_row = ""
            for i, name in enumerate(header_names):
                # Add data-type attribute for JS sorting
                data_type = "numeric" if name in numeric_columns else "string"
                
                # Get the description and add it as the title attribute for the tooltip
                description = COLUMN_DESCRIPTIONS.get(name, f"Data for {name}") 
                
                # Ticker is index 0
                header_row += f'<th onclick="sortTable({i})" data-type="{data_type}" title="{description}">{name}<span class="sort-indicator"></span></th>'

            table_rows = ""
            for index, row in df_html.iterrows():
                # Highlight the top row (Rank 1)
                rank_value_check = row['Rank'].split('>')[1].split('<')[0] # Extract the numeric value from the span
                row_style = 'style="background-color:#fffceb;"' if rank_value_check == '1.00' else ''
                
                table_rows += f'<tr {row_style}>'
                for key in df_html.columns:
                    cell_content = row[key]
                    if key == "Ticker":
                        # Ticker display name is already clean
                        display_ticker = cell_content 
                        
                        # Constructing the Finology Ticker URL
                        finology_link = f'https://ticker.finology.in/company/{display_ticker}'
                        
                        cell_content = f'<a href="{finology_link}" target="_blank" rel="noopener noreferrer" class="ticker-link">{display_ticker}</a>'
                    
                    table_rows += f'<td>{cell_content}</td>'
                table_rows += '</tr>'
            
            html_table_content = f"""
<table id="stockTable" class="styled-table">
    <thead>
        <tr>{header_row}</tr>
    </thead>
    <tbody>
        {table_rows}
    </tbody>
</table>
"""

            html_filename = f"RSQM_watchlist_Nifty{INDEX_SCOPE}.html"
            with open(html_filename,"w",encoding="utf-8") as f:
                f.write(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RSQM Watchlist - Nifty {INDEX_SCOPE}</title>
<style>
/* Pure CSS Styling (Ensuring Borders, Stickiness, and Fluidity) */
html, body {{ 
    margin: 0; 
    padding: 0; 
    overflow-x: hidden; /* FIX: Prevents page-level horizontal scrollbar */
}}
body {{ 
    font-family: 'Arial', sans-serif; 
    background-color: #f4f4f9; 
    padding: 20px; 
}}
.container {{ 
    max-width: 98%; /* Fluid width */
    margin: 0 auto; 
    background-color: white; 
    padding: 15px 20px; 
    border-radius: 8px; 
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); 
}}
h2 {{ color: #2c3e50; border-bottom: 3px solid #f39c12; padding-bottom: 10px; margin-bottom: 20px; font-size: 28px; font-weight: bold; }}
p {{ color: #7f8c8d; margin-bottom: 25px; font-size: 16px; }}

/* Table Styling - Ensuring Borders and Interactivity */
.styled-table {{
    width: 100%;
    min-width: 900px; /* Ensures the wide table is visible in the wrapper scroll area */
    border-collapse: collapse; 
    font-size: 14px;
    text-align: center;
    margin: 0; 
}}
.styled-table thead th {{ /* FIX: Make header sticky and prominent */
    position: sticky !important; /* Force sticky */
    top: 0 !important; /* Stick to the top of the scrollable container/viewport */
    z-index: 10; 
    background-color: #f39c12; /* Accent color for RSQM */
    color: white;
    box-shadow: 0 2px 2px -1px rgba(0, 0, 0, 0.2); 
    cursor: pointer; 
    font-weight: bold;
    text-transform: uppercase;
    border: 1px solid #e67e22 !important; /* Strong border */
    padding: 12px 15px;
    white-space: nowrap;
}}
.styled-table td {{
    padding: 10px 12px;
    border: 1px solid #dcdcdc !important; /* Clear cell border */
    white-space: nowrap;
    vertical-align: middle;
}}

.styled-table tr:nth-child(even) {{
    background-color: #f7f7fa; 
}}
.styled-table tr:hover {{
    background-color: #fcf3cf; /* Light yellow hover for RSQM theme */
}}

/* Ticker link styling */
.ticker-link {{
    font-weight: bold;
    color: #2980b9;
    text-decoration: none; 
}}
.ticker-link:hover {{
    text-decoration: underline;
}}


/* Sort Indicators */
.sort-indicator {{
    margin-left: 5px;
    display: inline-block;
    width: 0;
    height: 0;
    vertical-align: middle;
}}
.asc .sort-indicator::after {{ content: ' ▲'; }}
.desc .sort-indicator::after {{ content: ' ▼'; }}
.styled-table th.active {{ background-color: #e67e22; }} /* Darker active header */


/* Wrapper for table responsiveness and scroll */
.table-wrapper {{
    overflow-x: auto; /* Allows wide table horizontal scroll */
    max-height: 80vh; /* Constrain height for better sticky effect */
    border: 1px solid #c7d5e8;
    border-radius: 6px;
}}
</style>
</head>
<body>
<div class="container">
<h2 class="header-title">RSQM Watchlist - Nifty {INDEX_SCOPE}</h2>
<p>This report ranks the top 15 stocks in the Nifty {INDEX_SCOPE} index by their **RS Score** (Relative Strength & Quantitative Momentum). The score is an average of the stock's performance relative to the Nifty benchmark over 30, 90, and 180 days. Click on column headers to sort the table. Tickers link to Finology Ticker.</p>

<div class="table-wrapper">
{html_table_content}
</div>

</div>

<script>
let currentSortColumn = -1;
let sortDirection = "asc";

/**
 * Retrieves the value used for sorting from a table cell.
 * Prioritizes the 'data-order' attribute for accurate numeric/percent sorting.
 * @param {{Element}} tr - The table row element.
 * @param {{number}} idx - The index of the column/cell.
 * @returns {{number|string}} The sortable value.
 */
function getCellValue(tr, idx) {{
    const cell = tr.children[idx];
    
    // Check for <a> tag for Ticker column (index 0)
    if (idx === 0) {{
        const link = cell.querySelector('a');
        return link ? link.textContent.trim() : (cell.textContent || cell.innerText).trim();
    }}
    
    const span = cell.querySelector('span[data-order]');
    
    // 1. Numeric/Percent check (uses data-order)
    if (span) {{
        const value = parseFloat(span.getAttribute('data-order'));
        // Use -Infinity for NaN to push missing values to the bottom in ascending order
        return isNaN(value) ? -Infinity : value;
    }}
    
    // 2. Default to text content
    return (cell.textContent || cell.innerText).trim();
}}

/**
 * Sorts the HTML table rows based on the clicked column (n).
 * @param {{number}} n - The index of the column to sort.
 */
function sortTable(n) {{
    const table = document.getElementById("stockTable");
    const tbody = table.querySelector("tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));
    const header = table.querySelector("thead tr").children[n];
    const dataType = header.getAttribute('data-type');
    
    // Determine the sorting direction
    if (currentSortColumn === n) {{
        sortDirection = sortDirection === "asc" ? "desc" : "asc";
    }} else {{
        // Reset direction and active class for new column
        // Default to descending for numbers, ascending for strings (Ticker)
        sortDirection = (dataType === 'numeric') ? 'desc' : 'asc'; 
        
        // Remove active class and indicator from old column
        if (currentSortColumn !== -1) {{
            const oldHeader = table.querySelector("thead tr").children[currentSortColumn];
            oldHeader.classList.remove("asc", "desc", "active");
        }}
        currentSortColumn = n;
    }}

    // Add active class and indicator to the current column
    header.classList.remove("asc", "desc");
    header.classList.add(sortDirection, "active");


    const sortedRows = rows.sort((rowA, rowB) => {{
        let valA = getCellValue(rowA, n);
        let valB = getCellValue(rowB, n);
        let comparison = 0;

        // Perform comparison based on data type
        if (dataType === 'numeric') {{
            // Direct numeric comparison
            if (valA < valB) comparison = -1;
            if (valA > valB) comparison = 1;
        }} 
        else {{
            // Standard string comparison (case-insensitive for 'Ticker')
            const strA = String(valA).toLowerCase();
            const strB = String(valB).toLowerCase();
            if (strA < strB) comparison = -1;
            if (strA > strB) comparison = 1;
        }}
        
        // Apply direction multiplier
        return sortDirection === "asc" ? comparison : comparison * -1;
    }});

    // Reappend the sorted rows to the tbody
    tbody.innerHTML = ''; // Clear existing content
    sortedRows.forEach(row => tbody.appendChild(row));
    
}}

// Initial sort on 'RS Score' column (Index 2) descending.
// Ticker(0), Rank(1), RS Score(2)
document.addEventListener('DOMContentLoaded', () => {{
    // Automatically trigger initial sort on 'RS Score' (index 2) descending
    sortTable(2); 
}});
</script>

</body>
</html>
""")
            
            print(f"📁 Exported: {csv_filename}, {excel_filename}, and {html_filename}")
        else:
            print("\n⚠️ No stocks met the criteria or data was insufficient to compute RSQM scores.")
    else:
        print("\n🛑 Failed to retrieve any valid price data. Cannot proceed with RSQM calculation.")
