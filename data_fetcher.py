import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys

def fetch_stock_data(symbol: str, start_date_str: str) -> pd.DataFrame | None:
    """
    Fetches historical stock data for a given symbol and start date.

    Args:
        symbol: The stock symbol (e.g., "RELIANCE.NS").
        start_date_str: The start date string (e.g., "2023-01-01").

    Returns:
        A pandas DataFrame containing the historical stock data, or None if an error occurs.
    """
    try:
        start_datetime = datetime.strptime(start_date_str, "%Y-%m-%d")
        # Calculate end_date approximately 4 months after start_date
        end_datetime = start_datetime + timedelta(days=4 * 30)

        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start_datetime.strftime("%Y-%m-%d"), end=end_datetime.strftime("%Y-%m-%d"))

        if data.empty:
            print(f"Error: No data found for symbol {symbol} from {start_date_str} to {end_datetime.strftime('%Y-%m-%d')}", file=sys.stderr)
            return None

        return data
    except Exception as e:
        print(f"Error fetching stock data for {symbol}: {e}", file=sys.stderr)
        return None

if __name__ == '__main__':
    # This is a simple test case, more comprehensive tests should be in a separate test file.
    # Example usage: python data_fetcher.py RELIANCE.NS 2023-01-01
    if len(sys.argv) == 3:
        test_symbol = sys.argv[1]
        test_start_date = sys.argv[2]
        print(f"Fetching data for {test_symbol} from {test_start_date}...")
        df = fetch_stock_data(test_symbol, test_start_date)
        if df is not None:
            print("Data fetched successfully. Head of DataFrame:")
            print(df.head())
        else:
            print("Failed to fetch data.")
    else:
        # Default test if no command line arguments are provided
        print("Running default test case for RELIANCE.NS and 2023-01-01")
        test_symbol = "RELIANCE.NS"
        test_start_date = "2023-01-01"
        df = fetch_stock_data(test_symbol, test_start_date)
        if df is not None:
            print("Data fetched successfully. Head of DataFrame:")
            print(df.head())
        else:
            print("Failed to fetch data.")
