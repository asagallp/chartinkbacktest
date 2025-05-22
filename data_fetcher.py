import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys

def fetch_stock_data(symbol: str, start_date_str: str) -> tuple[pd.DataFrame | None, str | None]:
    """
    Fetches historical stock data for a given symbol and start date.
    Tries .NS and .BO suffixes if no suffix is provided and the symbol is not found.

    Args:
        symbol: The stock symbol (e.g., "RELIANCE", "RELIANCE.NS").
        start_date_str: The start date string (e.g., "2023-01-01").

    Returns:
        A tuple containing:
        - A pandas DataFrame with historical stock data, or None if an error occurs.
        - The symbol string that was successfully used to fetch data, or None if fetching failed.
    """
    original_symbol = symbol
    upper_symbol = symbol.upper()
    
    symbols_to_attempt = []

    if upper_symbol.endswith(".NS") or upper_symbol.endswith(".BO"):
        symbols_to_attempt = [upper_symbol]
    else:
        symbols_to_attempt = [upper_symbol + ".NS", upper_symbol + ".BO"]

    try:
        start_datetime = datetime.strptime(start_date_str, "%Y-%m-%d")
        # Calculate end_date approximately 4 months after start_date
        end_datetime = start_datetime + timedelta(days=4 * 30)
    except ValueError as e:
        print(f"Error: Invalid date format for start_date_str '{start_date_str}'. Expected YYYY-MM-DD. Details: {e}", file=sys.stderr)
        return None, None

    for attempt_symbol in symbols_to_attempt:
        print(f"Trying to fetch data for symbol: {attempt_symbol}", file=sys.stderr)
        try:
            ticker = yf.Ticker(attempt_symbol)
            # The yfinance library can sometimes raise exceptions for various reasons,
            # including network issues or invalid symbols that aren't caught by .history() returning empty.
            # A common pattern for yfinance is that .history() might return an empty DataFrame
            # for symbols that exist but have no data in the range, or for invalid symbols.
            data = ticker.history(start=start_datetime.strftime("%Y-%m-%d"), end=end_datetime.strftime("%Y-%m-%d"))

            if not data.empty:
                print(f"Successfully fetched data for {attempt_symbol}", file=sys.stderr)
                return data, attempt_symbol
            else:
                # This handles cases where the symbol is valid but no data for the period,
                # or yfinance returns empty for some types of invalid symbols.
                print(f"Failed to fetch data for {attempt_symbol}: No data returned.", file=sys.stderr)
        
        except Exception as e:
            # This catches other errors during yf.Ticker() or ticker.history() call
            # For example, network errors, or sometimes yfinance raises specific errors for truly bad symbols.
            print(f"Failed to fetch data for {attempt_symbol}: An error occurred: {e}", file=sys.stderr)
            # We continue to the next symbol in the list.

    # If loop completes, all attempts failed
    print(f"All attempts to fetch data for original symbol '{original_symbol}' (tried: {', '.join(symbols_to_attempt)}) failed.", file=sys.stderr)
    return None, None

# The __main__ block has been removed as per the subtask instructions.
# Unit tests are now in test_data_fetcher.py
