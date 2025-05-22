import sys
from data_fetcher import fetch_stock_data

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python main.py <stock_symbol> <start_date_YYYY-MM-DD>")
        sys.exit(1)

    symbol = sys.argv[1]
    start_date = sys.argv[2]

    print(f"Fetching stock data for {symbol} from {start_date}...")
    stock_data_df = fetch_stock_data(symbol, start_date)

    if stock_data_df is not None:
        print("Data fetched successfully:")
        print(stock_data_df.head())
    else:
        print(f"Failed to fetch stock data for {symbol}.")
