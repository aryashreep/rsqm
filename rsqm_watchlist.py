import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_fixed
import numpy as np

# -------------------------------
# 1. Load tickers from local or fallback
# -------------------------------
def load_tickers(local_filepath="ind_nifty100list.csv"):
    if os.path.exists(local_filepath):
        print("📂 Using local copy of Nifty100 list...")
        try:
            df = pd.read_csv(local_filepath)
            tickers = [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
            return tickers
        except Exception as e:
            print(f"⚠️ Error reading local file: {e}. Falling back to Nifty50 online.")

    url = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
    try:
        df = pd.read_csv(url)
        tickers = [f"{symbol}.NS" for symbol in df['Symbol'].tolist()]
        print("🌐 Using online Nifty50 list...")
        return tickers
    except Exception as e:
        print(f"❌ Failed to fetch tickers online: {e}")
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
        auto_adjust=False
    )
    if data.empty:
        raise ValueError(f"No data for {ticker}")
    return data["Adj Close"] if "Adj Close" in data.columns else data["Close"]


# -------------------------------
# 3. Main fetch (batch → fallback)
# -------------------------------
def fetch_data(tickers, benchmark="^NSEI", lookback_days=400):
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

        if isinstance(batch_data.columns, pd.MultiIndex):
            if "Adj Close" in batch_data.columns.levels[1]:
                batch_data = batch_data.xs("Adj Close", axis=1, level=1, drop_level=True)
            elif "Close" in batch_data.columns.levels[1]:
                batch_data = batch_data.xs("Close", axis=1, level=1, drop_level=True)

        if benchmark in batch_data.columns and not batch_data[benchmark].dropna().empty:
            print("✅ Batch download successful.")
            return batch_data
        else:
            print(f"⚠️ Benchmark {benchmark} missing in batch. Falling back to individual downloads...")

    except Exception as e:
        print(f"⚠️ Batch download failed due to: {e}")
        print("➡️ Switching to individual downloads with retries...")

    # ---- Fallback: individual ----
    price_data = {}
    for i, ticker in enumerate(all_tickers):
        print(f"  Fetching {ticker} ({i+1}/{len(all_tickers)})...", end="\r")
        try:
            series = fetch_single_ticker(ticker, start, end)
            price_data[ticker] = series
        except Exception as e:
            print(f"❌ {ticker} failed: {e}")

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
    lookbacks = {"30D": 30, "90D": 90, "180D": 180}
    rsqm = pd.DataFrame(index=tickers)

    if benchmark not in data.columns:
        print(f"⚠️ Benchmark {benchmark} missing, computing only absolute returns.")
        for label, days in lookbacks.items():
            rsqm[f"AbsRet_{label}"] = data.pct_change(days).iloc[-1, :].mul(100)
        rsqm["RS Score"] = rsqm.mean(axis=1)
        rsqm["Rank"] = rsqm["RS Score"].rank(ascending=False)
        return rsqm.sort_values("RS Score", ascending=False).head(15)

    # Compute returns
    abs_returns = {}
    rel_strengths = {}
    for label, days in lookbacks.items():
        # absolute returns
        returns = data.pct_change(days).iloc[-1, :].mul(100)
        abs_returns[label] = returns

        # relative strength
        bench_ret = returns.get(benchmark, np.nan)
        if not np.isnan(bench_ret) and bench_ret != 0:
            rel_strengths[label] = returns / bench_ret
        else:
            rel_strengths[label] = returns

    # Build DataFrame
    for label in lookbacks.keys():
        rsqm[f"AbsRet_{label}"] = abs_returns[label]
        rsqm[f"RelStr_{label}"] = rel_strengths[label]

    # RS Score = average of relative strengths
    rsqm["RS Score"] = rsqm[[f"RelStr_{lb}" for lb in lookbacks]].mean(axis=1)
    rsqm["Rank"] = rsqm["RS Score"].rank(ascending=False)

    leaders = rsqm.sort_values("RS Score", ascending=False).head(15)
    return leaders


# -------------------------------
# 5. Main workflow
# -------------------------------
if __name__ == "__main__":
    tickers = load_tickers()
    if not tickers:
        print("No tickers available. Exiting.")
        exit()

    data = fetch_data(tickers, benchmark="^NSEI")

    if not data.empty:
        leaders = compute_rsqm(data, tickers, benchmark="^NSEI")

        print("\n🔥 RSQM Watchlist (Top 15 NSE Stocks):")
        print(leaders.round(2))

        # Export results
        leaders.round(2).to_csv("RSQM_watchlist.csv")
        leaders.round(2).to_excel("RSQM_watchlist.xlsx")

        print("\n📁 Exported: RSQM_watchlist.csv and RSQM_watchlist.xlsx")
