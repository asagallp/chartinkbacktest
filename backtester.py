import pandas as pd
import argparse
import numpy as np
import sys

from data_fetcher import fetch_stock_data
from return_calculator import calculate_returns

def process_input_csv(input_csv_path: str, output_csv_path: str):
    """
    Reads an input CSV with stock symbols and identification dates,
    fetches historical data, calculates returns, and saves results to an output CSV.

    Args:
        input_csv_path: Path to the input CSV file.
                        Expected columns: 'Symbol', 'Date' (YYYY-MM-DD).
        output_csv_path: Path to save the output CSV file.
    """
    try:
        input_df = pd.read_csv(input_csv_path)
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_csv_path}", file=sys.stderr)
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print(f"Error: Input file {input_csv_path} is empty.", file=sys.stderr)
        sys.exit(1)
    except pd.errors.ParserError:
        print(f"Error: Could not parse input file {input_csv_path}. Check CSV formatting.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input CSV {input_csv_path}: {e}", file=sys.stderr)
        sys.exit(1)

    if not {'Symbol', 'Date'}.issubset(input_df.columns):
        print(f"Error: Input CSV {input_csv_path} must contain 'Symbol' and 'Date' columns.", file=sys.stderr)
        sys.exit(1)

    results_list = []

    for index, row in input_df.iterrows():
        original_symbol_from_csv = str(row['Symbol'])
        identification_date = str(row['Date']) # Ensure it's a string for the functions

        # Call fetch_stock_data and unpack both return values
        historical_data, resolved_symbol = fetch_stock_data(original_symbol_from_csv, identification_date)

        returns_dict = {'1W': np.nan, '1M': np.nan, '3M': np.nan} # Default to NaN

        if historical_data is not None and not historical_data.empty and resolved_symbol is not None:
            # Data fetched successfully
            print(f"Processing {resolved_symbol} (identified as '{original_symbol_from_csv}' on {identification_date})...")
            
            # Ensure the date format passed to calculate_returns is YYYY-MM-DD
            # The 'identification_date' from CSV is already in this format.
            calculated_returns = calculate_returns(historical_data, identification_date)
            returns_dict.update(calculated_returns) # Update with actual returns if calculated
        else:
            # Data fetching failed or returned empty/None
            print(f"Failed to fetch data for {original_symbol_from_csv} identified on {identification_date} after trying relevant suffixes. Using NaN for returns.", file=sys.stderr)
            # returns_dict remains as all NaNs

        result_row = {
            'Symbol': original_symbol_from_csv, # Store the original symbol from CSV
            'Date': identification_date,
            '1W_Return': returns_dict.get('1W', np.nan),
            '1M_Return': returns_dict.get('1M', np.nan),
            '3M_Return': returns_dict.get('3M', np.nan)
        }
        results_list.append(result_row)

    if not results_list:
        print("No data processed. Output file will be empty or not created.")
        # Depending on desired behavior, one might still want to create an empty CSV with headers
        # For now, if results_list is empty, an empty DataFrame will be created and saved.

    output_df = pd.DataFrame(results_list)
    
    try:
        output_df.to_csv(output_csv_path, index=False)
        print(f"Backtest complete. Results saved to {output_csv_path}")
    except Exception as e:
        print(f"Error saving output CSV to {output_csv_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stock Backtester")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to the input CSV file. Expected columns: 'Symbol', 'Date'."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="Path to the output CSV file for saving results."
    )

    args = parser.parse_args()

    process_input_csv(args.input, args.output)

    # Example to create a dummy input CSV for testing:
    # if not os.path.exists("dummy_input.csv"):
    #     dummy_data = {
    #         'Symbol': ["RELIANCE.NS", "TCS.NS", "INFY.NS", "NONEXISTENT.NS"],
    #         'Date': ["2023-01-01", "2023-02-01", "2022-11-15", "2023-01-01"]
    #     }
    #     dummy_df = pd.DataFrame(dummy_data)
    #     dummy_df.to_csv("dummy_input.csv", index=False)
    #     print("Created dummy_input.csv for testing. Run again with: python backtester.py -i dummy_input.csv -o output_results.csv")
