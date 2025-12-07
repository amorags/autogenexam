import json
import pandas as pd
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except Exception:
    YFINANCE_AVAILABLE = False

def fetch_stock(ticker: str, start: str = None, end: str = None) -> str:
    """
    Download historical stock data using yfinance and return JSON.
    start/end are 'YYYY-MM-DD' strings (optional).
    """
    if not YFINANCE_AVAILABLE:
        return json.dumps({"error": "yfinance not installed or failed to import."})
    try:
        # yfinance .download returns a DataFrame with DatetimeIndex
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
        if df.empty:
            return json.dumps({"error": f"No data returned for ticker {ticker}."})
        if isinstance(df.columns, pd.MultiIndex):
                # We take the last level, which usually contains the column name (Open, Close, etc.)
                df.columns = df.columns.get_level_values(-1)
            # 2. Rename columns to ensure they are clean strings for the chart agent
        df.columns = [col.replace(' ', '_') for col in df.columns]# Keep the index as a 'date' column
        df = df.reset_index()
        # Convert Timestamp to string for JSON serialization
        df['Date'] = df['Date'].dt.strftime("%Y-%m-%d")
        return json.dumps({
            "source": "yfinance",
            "ticker": ticker,
            "columns": list(df.columns),
            "data": df.to_dict(orient="list")
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
