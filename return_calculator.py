import pandas as pd
import numpy as np
from pandas.tseries.offsets import DateOffset

def get_price_on_or_after(date: pd.Timestamp, data: pd.DataFrame) -> float | None:
    """
    Helper function to get the closing price on or after a given date.
    """
    if data.empty:
        return None
    # Filter data from the given date onwards
    future_data = data[data.index >= date]
    if future_data.empty:
        return None
    return future_data.iloc[0]['Close']

def calculate_returns(historical_data: pd.DataFrame, identification_date_str: str) -> dict:
    """
    Calculates stock returns for 1-week, 1-month, and 3-month periods
    from an identification date.

    Args:
        historical_data: Pandas DataFrame with DateTimeIndex and 'Close' prices.
        identification_date_str: The date string (e.g., "2023-01-01")
                                   when the stock was identified.

    Returns:
        A dictionary containing the calculated returns:
        {'1W': <return_1_week_percentage>,
         '1M': <return_1_month_percentage>,
         '3M': <return_3_months_percentage>}
        Uses numpy.nan for any returns that could not be calculated.
    """
    returns = {'1W': np.nan, '1M': np.nan, '3M': np.nan}

    if historical_data is None or historical_data.empty:
        return returns

    try:
        t_0 = pd.Timestamp(identification_date_str)
    except ValueError:
        # Handle invalid date string format if necessary, though Timestamp is quite robust
        print(f"Error: Invalid identification_date_str format: {identification_date_str}")
        return returns
        
    # Ensure the index is timezone-naive if t_0 is timezone-naive, or localize t_0
    if historical_data.index.tz is not None and t_0.tz is None:
        t_0 = t_0.tz_localize(historical_data.index.tz)
    elif historical_data.index.tz is None and t_0.tz is not None:
        t_0 = t_0.tz_localize(None)


    price_t_0 = get_price_on_or_after(t_0, historical_data)

    if price_t_0 is None:
        return returns # All NaN as per requirement

    # Target dates
    t_1W = t_0 + pd.Timedelta(days=7)
    t_1M = t_0 + DateOffset(months=1)
    t_3M = t_0 + DateOffset(months=3)

    # Prices at target dates
    price_t_1W = get_price_on_or_after(t_1W, historical_data)
    price_t_1M = get_price_on_or_after(t_1M, historical_data)
    price_t_3M = get_price_on_or_after(t_3M, historical_data)

    # Calculate returns
    if price_t_1W is not None:
        returns['1W'] = ((price_t_1W / price_t_0) - 1) * 100
    
    if price_t_1M is not None:
        returns['1M'] = ((price_t_1M / price_t_0) - 1) * 100

    if price_t_3M is not None:
        returns['3M'] = ((price_t_3M / price_t_0) - 1) * 100

    return returns

# End of calculate_returns function
# The test code previously under if __name__ == "__main__": has been moved to test_return_calculator.py
```
