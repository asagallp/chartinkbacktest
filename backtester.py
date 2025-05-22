import pandas as pd
import argparse
import numpy as np
import sys
import os

from data_fetcher import fetch_stock_data
from return_calculator import calculate_returns

def process_input_csv(input_csv_path: str, output_csv_path: str, html_output_path_arg: str | None = None):
    """
    Reads an input CSV with stock symbols and identification dates,
    fetches historical data, calculates returns, and saves results to an output CSV and optionally HTML.

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
        print(f"Backtest complete. CSV results saved to {output_csv_path}")

        # Generate HTML report
        if html_output_path_arg:
            html_output_filename = html_output_path_arg
        else:
            html_output_filename = os.path.splitext(output_csv_path)[0] + ".html"
        
        html_style = """
        <style>
            body { font-family: sans-serif; }
            table { border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #dddddd; text-align: left; padding: 8px; }
            th { background-color: #f2f2f2; font-weight: bold; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            caption { caption-side: top; font-size: 1.2em; margin-bottom: 10px; font-weight: bold; }
        </style>
        """
        html_title = "<h1>Backtest Report</h1>"
        
        # Ensure column names in DataFrame are suitable for HTML display if needed
        # For now, using existing column names.
        # Convert float columns to string with fixed precision for better display
        # Create a copy for formatting to avoid changing original output_df for other uses
        formatted_df = output_df.copy()
        for col in ['1W_Return', '1M_Return', '3M_Return']:
            if col in formatted_df.columns:
                # Format to 2 decimal places, N/A for NaNs
                formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else 'N/A')
            
        html_table = formatted_df.to_html(index=False, na_rep='N/A', border=0, escape=False)
        
        full_html = f"<!DOCTYPE html><html><head><title>Backtest Report</title>{html_style}</head><body>{html_title}{html_table}</body></html>"
        
        with open(html_output_filename, 'w') as f:
            f.write(full_html)
        print(f"HTML report saved to {html_output_filename}")

    except Exception as e:
        print(f"Error saving output CSV or HTML to {output_csv_path}: {e}", file=sys.stderr)


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
    parser.add_argument(
        "--html",
        "--html_output_path",
        type=str,
        default=None, # Default to None, so we know if it was provided
        help="Optional path to save the HTML report. "
             "If not provided, it defaults to the CSV output path with an .html extension."
    )

    args = parser.parse_args()

    process_input_csv(args.input, args.output, args.html)

    # Example to create a dummy input CSV for testing:
    # if not os.path.exists("dummy_input.csv"):
    #     dummy_data = {
    #         'Symbol': ["RELIANCE.NS", "TCS.NS", "INFY.NS", "NONEXISTENT.NS"],
    #         'Date': ["2023-01-01", "2023-02-01", "2022-11-15", "2023-01-01"]
    #     }
    #     dummy_df = pd.DataFrame(dummy_data)
    #     dummy_df.to_csv("dummy_input.csv", index=False)
    #     print("Created dummy_input.csv for testing. Run again with: python backtester.py -i dummy_input.csv -o output_results.csv")
