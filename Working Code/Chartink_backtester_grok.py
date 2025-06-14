import os
import time
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup as bs
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

# Constants
CACHE_FILE = 'chartink_backtest_results.csv'
LOGIN_URL = 'https://chartink.com/login'
BACKTEST_URL = 'https://chartink.com/backtest/process'
SCANNER_FETCH_URL = "https://chartink.com/screener/process"

def get_next_business_day(date):
    """
    Returns the next business day if the given date falls on a weekend or holiday.
    """
    while True:
        date += timedelta(days=1)
        if date.weekday() < 5:  # Monday to Friday
            return date

def get_chartink_clause(scanner_input, session):
    """Fetches the scanner clause by making an AJAX request."""
    print(f"[DEBUG] User Input: {scanner_input}")  # Debugging: Print user input
    if "chartink.com/screener/" in scanner_input:
        print("[INFO] Fetching scanner clause from URL...")
        try:
            # Extract scanner name from URL
            scanner_name = scanner_input.split("/")[-1]
            print(f"[DEBUG] Scanner Name: {scanner_name}")  # Debugging: Print scanner name
            # Fetch CSRF token
            login_page = session.get(LOGIN_URL)
            soup = bs(login_page.text, 'html.parser')
            csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
            if not csrf_token:
                print("[ERROR] CSRF token not found. Exiting...")
                return None
            # Make the AJAX request with CSRF token
            headers = {
                "x-csrf-token": csrf_token,
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }
            payload = {"scan_clause": "", "screener_name": scanner_name}
            response = session.post(SCANNER_FETCH_URL, headers=headers, data=payload)
            if response.status_code != 200:
                print(f"[ERROR] Failed to fetch scanner data. Status: {response.status_code}")
                print(f"[DEBUG] Response Text: {response.text}")  # Debugging: Print response text
                return None
            # Extract the scan_clause from response JSON
            data = response.json()
            print(f"[DEBUG] Response JSON: {data}")  # Debugging: Print the entire response JSON
            if "scan_clause" in data:
                clause = data["scan_clause"].strip()
                print("[INFO] Scanner clause extracted successfully.")
                return clause
            elif "scan_error" in data:
                print(f"[ERROR] Server returned an error: {data['scan_error']}")
                return None
            else:
                print("[ERROR] Scanner clause not found in response.")
                return None
        except requests.RequestException as e:
            print(f"[ERROR] Request failed: {e}")
            return None
    else:
        print("[INFO] Using provided scan clause.")
        return scanner_input  # Return as-is if it's not a URL

def fetch_csrf_token_and_login():
    """Fetches CSRF token and logs into Chartink."""
    print("[INFO] Fetching CSRF token and logging in...")
    session = requests.Session()
    login_page = session.get(LOGIN_URL)
    if login_page.status_code != 200:
        print(f"[ERROR] Failed to fetch login page. Status: {login_page.status_code}")
        return None
    soup = bs(login_page.text, 'html.parser')
    csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
    if not csrf_token:
        print("[ERROR] CSRF token not found. Exiting...")
        return None
    # Prompt user for login credentials
    email = input("Enter your Chartink email: ").strip()
    password = input("Enter your Chartink password: ").strip()
    login_payload = {
        "email": email,
        "password": password,
        "_token": csrf_token
    }
    login_response = session.post(LOGIN_URL, data=login_payload)
    if login_response.status_code != 200:
        print(f"[ERROR] Failed to log in. Status: {login_response.status_code}")
        return None
    print("[INFO] Logged in successfully.")
    return session, csrf_token

def fetch_chartink_results(session, csrf_token, scan_clause):
    """Fetches backtest results from Chartink."""
    print("[INFO] Fetching backtest results from Chartink...")
    headers = {
        "x-csrf-token": csrf_token,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    payload = {"scan_clause": scan_clause}
    response = session.post(BACKTEST_URL, headers=headers, data=payload)
    if response.status_code != 200:
        print(f"[ERROR] Failed to fetch data. Status: {response.status_code}")
        print(f"[DEBUG] Response Text: {response.text}")  # Debugging: Print response text
        return pd.DataFrame()
    try:
        data = response.json()
    except ValueError:
        print("[ERROR] Failed to parse JSON response.")
        print(f"[DEBUG] Response Text: {response.text}")
        return pd.DataFrame()
    if "metaData" not in data or "aggregatedStockList" not in data:
        print("[ERROR] Invalid response format. Exiting...")
        print(f"[DEBUG] Response JSON: {data}")
        return pd.DataFrame()
    dates = data["metaData"][0]["tradeTimes"]
    stocks = data["aggregatedStockList"]
    results = []
    for i, trade_date in enumerate(dates):
        entry_date = datetime.fromtimestamp(trade_date / 1000).strftime("%Y-%m-%d")
        if stocks[i]:
            for j in range(0, len(stocks[i]), 3):
                results.append({"Date": entry_date, "Stock": stocks[i][j]})
    print(f"[INFO] Retrieved {len(results)} stock entries from Chartink.")
    return pd.DataFrame(results)

def cache_data(df):
    df.to_csv(CACHE_FILE, index=False)
    print(f"[INFO] Data cached to {CACHE_FILE}.")

def load_cached_data():
    if os.path.exists(CACHE_FILE):
        print("[INFO] Loading data from cache...")
        return pd.read_csv(CACHE_FILE)
    return None

def validate_date_format(df):
    if df.empty:
        print("[ERROR] DataFrame is empty. Cannot validate date format.")
        return df
    # Check for 'Date' column with case variations
    date_column = None
    for col in df.columns:
        if col.lower() == 'date':
            date_column = col
            break
    if date_column is None:
        print("[ERROR] No 'Date' column (case-insensitive) found in DataFrame. Cannot validate date format.")
        return df
    # Standardize column name to 'Date'
    if date_column != 'Date':
        print(f"[INFO] Renaming column '{date_column}' to 'Date' for consistency.")
        df = df.rename(columns={date_column: 'Date'})
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df.dropna(subset=["Date"], inplace=True)
    return df

def calculate_returns(df):
    """
    Calculate returns for each stock and include full week's closing prices,
    1-month closing price, and 3-month closing price.
    """
    results = []
    for index, row in df.iterrows():
        stock = row["Stock"]
        date = pd.to_datetime(row["Date"])
        # Try NSE (.NS) first, then BSE (.BO) if it fails
        ticker_symbols = [f"{stock}.NS", f"{stock}.BO"]
        identified_price = None
        week_prices = {}
        month_price = None
        three_month_price = None
        successful_ticker = None

        for ticker_symbol in ticker_symbols:
            try:
                print(f"[INFO] Fetching data for {ticker_symbol} from {date}...")
                
                # Fetch data for 1 week
                week_prices = {}
                for i in range(7):
                    day_date = date + timedelta(days=i)
                    day_date = get_next_business_day(day_date) if day_date.weekday() >= 5 else day_date
                    try:
                        hist = yf.Ticker(ticker_symbol).history(start=day_date, end=day_date + timedelta(days=1))
                        if not hist.empty:
                            week_prices[f"Week Day {i+1} Close"] = hist.iloc[0]['Close']
                        else:
                            week_prices[f"Week Day {i+1} Close"] = None
                    except Exception as e:
                        print(f"[WARNING] Error fetching data for {ticker_symbol} on {day_date}: {e}")
                        week_prices[f"Week Day {i+1} Close"] = None

                # Fetch data for 1 month
                month_end_date = date + timedelta(days=30)
                month_end_date = get_next_business_day(month_end_date) if month_end_date.weekday() >= 5 else month_end_date
                try:
                    hist_month = yf.Ticker(ticker_symbol).history(start=date, end=month_end_date)
                    month_price = hist_month.iloc[-1]['Close'] if not hist_month.empty else None
                except Exception as e:
                    print(f"[WARNING] Error fetching 1-month data for {ticker_symbol}: {e}")
                    month_price = None

                # Fetch data for 3 months
                three_month_end_date = date + timedelta(days=90)
                three_month_end_date = get_next_business_day(three_month_end_date) if three_month_end_date.weekday() >= 5 else three_month_end_date
                try:
                    hist_three_month = yf.Ticker(ticker_symbol).history(start=date, end=three_month_end_date)
                    three_month_price = hist_three_month.iloc[-1]['Close'] if not hist_three_month.empty else None
                except Exception as e:
                    print(f"[WARNING] Error fetching 3-month data for {ticker_symbol}: {e}")
                    three_month_price = None

                # Extract identified price
                try:
                    hist = yf.Ticker(ticker_symbol).history(start=date, end=date + timedelta(days=1))
                    identified_price = hist.iloc[0]['Close'] if not hist.empty else None
                except Exception as e:
                    print(f"[WARNING] Error fetching identified price for {ticker_symbol}: {e}")
                    identified_price = None

                # If we got valid data, break the loop
                if identified_price is not None or any(week_prices.values()) or month_price is not None or three_month_price is not None:
                    successful_ticker = ticker_symbol
                    print(f"[INFO] Successfully fetched data for {ticker_symbol}")
                    break
                else:
                    print(f"[INFO] No valid data found for {ticker_symbol}, trying next ticker...")

            except Exception as e:
                print(f"[WARNING] Error processing {ticker_symbol}: {e}")
                continue

        # If no data was retrieved for either .NS or .BO, log and skip
        if successful_ticker is None:
            print(f"[ERROR] No data available for {stock} on either NSE (.NS) or BSE (.BO). Skipping...")
            continue

        # Calculate returns
        week_return = ((week_prices.get("Week Day 7 Close") - identified_price) / identified_price * 100) if week_prices.get("Week Day 7 Close") and identified_price else None
        month_return = ((month_price - identified_price) / identified_price * 100) if month_price and identified_price else None
        three_month_return = ((three_month_price - identified_price) / identified_price * 100) if three_month_price and identified_price else None

        # Store results
        results.append({
            'Stock': stock,
            'Date': date,
            'Identified Price': identified_price,
            **week_prices,  # Full week prices
            '1 Month Close Price': month_price,
            '3 Month Close Price': three_month_price,
            '1 Week Return (%)': week_return,
            '1 Month Return (%)': month_return,
            '3 Month Return (%)': three_month_return
        })

        time.sleep(1)  # Avoid rate limiting

    return pd.DataFrame(results)

def generate_report(df):
    """
    Generates a report, saves it to a CSV file, and converts it to a JSON file.
    """
    if df.empty:
        print("[ERROR] No data to generate a report.")
        return
    print("\n[INFO] Backtest Report:")
    print(df)
    # Save all columns to CSV with a meaningful name
    csv_file = "stock_backtest_analysis.csv"
    df.to_csv(csv_file, index=False)
    print(f"[INFO] Results saved to '{csv_file}'.")
    # Convert CSV to JSON
    json_file = "stock_backtest_analysis.json"
    df.to_json(json_file, orient='records', lines=True)
    print(f"[INFO] Results saved to '{json_file}'.")
    # Plot 1-week, 1-month, and 3-month returns
    plt.figure(figsize=(14, 8))
    # Plot 1-Week Return
    plt.subplot(3, 1, 1)
    sns.barplot(data=df, x='Stock', y='1 Week Return (%)', palette='viridis')
    plt.title('1-Week Returns for Identified Stocks')
    plt.xticks(rotation=90)
    # Plot 1-Month Return
    plt.subplot(3, 1, 2)
    sns.barplot(data=df, x='Stock', y='1 Month Return (%)', palette='viridis')
    plt.title('1-Month Returns for Identified Stocks')
    plt.xticks(rotation=90)
    # Plot 3-Month Return
    plt.subplot(3, 1, 3)
    sns.barplot(data=df, x='Stock', y='3 Month Return (%)', palette='viridis')
    plt.title('3-Month Returns for Identified Stocks')
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.show()

def main():
    # Ask user if they want to login and perform analysis
    login_choice = input("Do you want to login and do the analysis? (yes/no): ").strip().lower()
    # Initialize session and csrf_token
    session = requests.Session()  # Default session if login is skipped or fails
    csrf_token = None
    # Attempt login if user chooses 'yes'
    if login_choice == "yes":
        session_data = fetch_csrf_token_and_login()
        if session_data:
            session, csrf_token = session_data
        else:
            print("[INFO] Login failed, proceeding with default session...")
    else:
        print("[INFO] Skipping login, proceeding with default session...")
    # Proceed with scanner input regardless of login outcome
    scanner_input = input("Enter Chartink scanner URL or clause: ").strip()
    scan_clause = get_chartink_clause(scanner_input, session)
    if not scan_clause:
        print("[ERROR] Failed to fetch scan clause from URL.")
        scan_clause = input("Please manually enter the scan clause: ").strip()
        if not scan_clause:
            print("[ERROR] No scan clause provided. Exiting...")
            return
    use_chartink = input("Fetch fresh data from Chartink? (yes/no): ").strip().lower()
    if use_chartink == "yes":
        df = fetch_chartink_results(session, csrf_token, scan_clause)
        if df.empty:
            print("[INFO] No data retrieved from Chartink. Attempting to load cached data...")
            df = load_cached_data()
            if df is None:
                print("[ERROR] No cached data available. Exiting...")
                return
        df = validate_date_format(df)
        cache_data(df)
    else:
        df = load_cached_data()
        if df is None:
            print("[INFO] No cache found. Fetching fresh data...")
            df = fetch_chartink_results(session, csrf_token, scan_clause)
            if df.empty:
                print("[INFO] No data retrieved from Chartink. Exiting...")
                return
            df = validate_date_format(df)
            cache_data(df)
    # Calculate returns and generate report
    results_df = calculate_returns(df)
    generate_report(results_df)

if __name__ == "__main__":
    main()