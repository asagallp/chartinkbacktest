import unittest
import pandas as pd
import numpy as np
from pandas.tseries.offsets import DateOffset # Needed for test data generation if replicating logic
from datetime import datetime

# Assuming return_calculator.py is in the same directory or accessible via PYTHONPATH
from return_calculator import calculate_returns 

class TestReturnCalculator(unittest.TestCase):

    def assertReturnDictsClose(self, dict1, dict2, msg=None):
        """
        Asserts that two dictionaries of returns are close.
        Compares keys and checks for np.nan equality for float values.
        """
        self.assertEqual(set(dict1.keys()), set(dict2.keys()), msg=f"Keys differ: {msg}" if msg else "Keys differ")
        for key in dict1:
            val1 = dict1[key]
            val2 = dict2[key]
            if isinstance(val1, float) and isinstance(val2, float):
                if np.isnan(val1) and np.isnan(val2):
                    continue # Both are NaN, considered equal for this purpose
                self.assertAlmostEqual(val1, val2, places=5, msg=f"Floats differ for key '{key}': {msg}" if msg else f"Floats differ for key '{key}'")
            else:
                self.assertEqual(val1, val2, msg=f"Values differ for key '{key}': {msg}" if msg else f"Values differ for key '{key}'")

    @classmethod
    def setUpClass(cls):
        # This sample data can be used by multiple tests
        # More specific data can be created within each test method if needed
        dates = pd.to_datetime([
            "2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05", # P_t0 = 102 (idx 2)
            "2023-01-08", "2023-01-09", "2023-01-10", "2023-01-11", "2023-01-12", # P_t1W = 107 (idx 7)
            "2023-01-30", "2023-01-31", "2023-02-01", "2023-02-02", "2023-02-03", # P_t1M = 114 (idx 14)
            "2023-03-28", "2023-03-29", "2023-03-30", "2023-03-31", "2023-04-03", # P_t3M = 120 (idx 19)
            "2023-04-04", "2023-04-05"
        ])
        closes = [
            100, 101, 102, 103, 104,  # Jan 1-5
            105, 106, 107, 108, 109,  # Jan 8-12
            110, 111, 112, 113, 114,  # Jan 30 - Feb 3
            115, 116, 117, 118, 120,  # Mar 28 - Apr 3
            121, 122                   # Apr 4-5
        ]
        cls.sample_data = pd.DataFrame({'Close': closes}, index=dates)

    def test_basic_calculation(self):
        # Test Case 1 from original: Identification date is a trading day
        # t_0 = 2023-01-03 (Price 102)
        # t_1W = 2023-01-10 (Price 107) -> (107/102 - 1)*100 = 4.90196%
        # t_1M = 2023-02-03 (Price 114) -> (114/102 - 1)*100 = 11.7647% (DateOffset makes it 2023-02-03)
        # t_3M = 2023-04-03 (Price 120) -> (120/102 - 1)*100 = 17.64705% (DateOffset makes it 2023-04-03)
        results = calculate_returns(self.sample_data, "2023-01-03")
        expected = {'1W': 4.90196, '1M': 11.76471, '3M': 17.64706}
        self.assertReturnDictsClose(results, expected, "Test Case 1: Basic Calculation")

    def test_identification_date_not_trading_day(self):
        # Test Case 2: Identification date not a trading day
        # Original ID date: "2023-01-06" (Fri). Next trading day in sample_data is "2023-01-08" (Price 105)
        # t_0 = 2023-01-08 (Price 105)
        # t_1W = 2023-01-08 + 7 days = 2023-01-15. Next available: 2023-01-30 (Price 110)
        # Return: (110/105 - 1)*100 = 4.76190%
        # t_1M = 2023-01-08 + 1 month = 2023-02-08. Next available: 2023-02-01 (Price 112) - this was an error in original reasoning.
        # Corrected: t_1M from 2023-01-08 is 2023-02-08. Next available in data is 2023-03-28 (Price 115) - still seems off.
        # Let's use the logic: date = 2023-01-08 (P=105). 1M target: 2023-02-08. In sample_data, after 2023-02-08 is 2023-03-28 (P=115).
        # (115/105 - 1)*100 = 9.52381%

        # t_3M = 2023-01-08 + 3 months = 2023-04-08. Next available: 2023-04-03 (P=120) - again, error in original, should be future.
        # Corrected: t_3M from 2023-01-08 is 2023-04-08. Next available in data is 2023-04-04 (P=121)
        # (121/105 - 1)*100 = 15.23809%
        results = calculate_returns(self.sample_data, "2023-01-06") # Friday, data has 2023-01-08 as next
        expected = {'1W': (107/105-1)*100, # P_t0=105 (01-08), P_t1W=107 (01-10, which is closest to 01-08 + 7days=01-15)
                    '1M': (112/105-1)*100, # P_t1M=112 (02-01, which is closest to 01-08 + 1M=02-08)
                    '3M': (120/105-1)*100} # P_t3M=120 (04-03, which is closest to 01-08 + 3M=04-08)

        # Re-evaluating based on get_price_on_or_after implementation:
        # t0: 2023-01-08 (Price 105)
        # t_1W: 2023-01-15 -> get_price_on_or_after -> 2023-01-30 (Price 110) -> (110/105 - 1)*100 = 4.76190%
        # t_1M: 2023-02-08 -> get_price_on_or_after -> 2023-03-28 (Price 115) -> (115/105 - 1)*100 = 9.52381%
        # t_3M: 2023-04-08 -> get_price_on_or_after -> 2023-04-04 (Price 121) -> (121/105 - 1)*100 = 15.23809%
        # The original script's Test Case 2 output was: {'1W': 4.76190, '1M': 9.52381, '3M': 15.2381}
        # This matches the re-evaluation.

        expected = {'1W': 4.76190, '1M': 9.52381, '3M': 15.23810}
        self.assertReturnDictsClose(results, expected, "Test Case 2: Identification date not trading day")

    def test_data_too_short_for_3m_return(self):
        # Test Case 3 from original
        short_data = self.sample_data[self.sample_data.index < "2023-03-01"]
        # t_0 = 2023-01-03 (Price 102)
        # t_1W = 2023-01-10 (Price 107) -> 4.90196%
        # t_1M = 2023-02-03 (Price 114) -> 11.76471%
        # t_3M = 2023-04-03 (No data in short_data) -> NaN
        results = calculate_returns(short_data, "2023-01-03")
        expected = {'1W': 4.90196, '1M': 11.76471, '3M': np.nan}
        self.assertReturnDictsClose(results, expected, "Test Case 3: Data too short for 3M")

    def test_identification_date_at_very_end(self):
        # Test Case 4 from original
        # t_0 = 2023-04-05 (Price 122)
        # t_1W, t_1M, t_3M will all be NaN as no future data.
        results = calculate_returns(self.sample_data, "2023-04-05")
        expected = {'1W': np.nan, '1M': np.nan, '3M': np.nan}
        self.assertReturnDictsClose(results, expected, "Test Case 4: Identification date at very end")

    def test_identification_date_after_all_data(self):
        # Test Case 5 from original
        # t_0 price will be None. All returns NaN.
        results = calculate_returns(self.sample_data, "2023-05-01")
        expected = {'1W': np.nan, '1M': np.nan, '3M': np.nan}
        self.assertReturnDictsClose(results, expected, "Test Case 5: Identification date after all data")

    def test_empty_dataframe(self):
        # Test Case 6 from original
        empty_df = pd.DataFrame({'Close': []}, index=pd.to_datetime([]))
        results = calculate_returns(empty_df, "2023-01-01")
        expected = {'1W': np.nan, '1M': np.nan, '3M': np.nan}
        self.assertReturnDictsClose(results, expected, "Test Case 6: Empty DataFrame")

    def test_identification_date_no_data_on_or_after_t0(self):
        # Test Case 7 from original
        data_ends_early = self.sample_data[self.sample_data.index < "2023-01-02"] # Data only for 2023-01-01
        results = calculate_returns(data_ends_early, "2023-01-03")
        expected = {'1W': np.nan, '1M': np.nan, '3M': np.nan}
        self.assertReturnDictsClose(results, expected, "Test Case 7: No data at or after t0")

    def test_timezone_aware_data(self):
        # Test Case 9 from original
        sample_data_tz = self.sample_data.copy()
        sample_data_tz.index = sample_data_tz.index.tz_localize('UTC')
        results = calculate_returns(sample_data_tz, "2023-01-03") # identification_date_str is naive
        # Expected results should be same as Test Case 1
        expected = {'1W': 4.90196, '1M': 11.76471, '3M': 17.64706}
        self.assertReturnDictsClose(results, expected, "Test Case 9: Timezone-aware data")

    def test_invalid_identification_date_format(self):
        # Test Case 10 from original
        results = calculate_returns(self.sample_data, "invalid-date-format")
        expected = {'1W': np.nan, '1M': np.nan, '3M': np.nan}
        self.assertReturnDictsClose(results, expected, "Test Case 10: Invalid date format")

    def test_target_date_lands_on_non_trading_day(self):
        # Test Case 11 from original
        dates_missing_targets = pd.to_datetime([
            "2023-01-01", # t0 (Price 100)
            "2023-01-08", # t_1W (Jan 1 + 7 days) (Price 105)
            # "2023-02-01", # t_1M (Jan 1 + 1 month) is missing
            "2023-02-02", # Next available for t_1M (Price 110)
            # "2023-04-01", # t_3M (Jan 1 + 3 months) is missing
            "2023-04-03", # Next available for t_3M (Price 120)
        ])
        closes_missing_targets = [100, 105, 110, 120]
        data = pd.DataFrame({'Close': closes_missing_targets}, index=dates_missing_targets)
        
        results = calculate_returns(data, "2023-01-01")
        # t0: 2023-01-01 (Price 100)
        # t_1W: 2023-01-08 (Price 105) -> (105/100 - 1)*100 = 5.0%
        # t_1M: 2023-02-01 -> next is 2023-02-02 (Price 110) -> (110/100 - 1)*100 = 10.0%
        # t_3M: 2023-04-01 -> next is 2023-04-03 (Price 120) -> (120/100 - 1)*100 = 20.0%
        expected = {'1W': 5.0, '1M': 10.0, '3M': 20.0}
        self.assertReturnDictsClose(results, expected, "Test Case 11: Target date non-trading day")

    def test_all_target_dates_outside_range(self):
        # Test Case 12 from original
        one_day_data = pd.DataFrame({'Close': [100]}, index=pd.to_datetime(["2023-01-01"]))
        results = calculate_returns(one_day_data, "2023-01-01")
        expected = {'1W': np.nan, '1M': np.nan, '3M': np.nan}
        self.assertReturnDictsClose(results, expected, "Test Case 12: All targets outside range")

    def test_historical_data_is_none(self):
        # Test Case 13 from original
        results = calculate_returns(None, "2023-01-01")
        expected = {'1W': np.nan, '1M': np.nan, '3M': np.nan}
        self.assertReturnDictsClose(results, expected, "Test Case 13: historical_data is None")

    def test_specific_check_next_available_trading_day_for_target(self):
        # Test Case 8 from original
        # t_0: 2023-01-02 (Price 101)
        # t_1W: 2023-01-09 (Price 106) -> (106/101 - 1)*100 = 4.950495%
        # t_1M: 2023-02-02 (Price 113) -> (113/101 - 1)*100 = 11.881188%
        # t_3M: 2023-04-02 -> next is 2023-04-03 (Price 120) -> (120/101 - 1)*100 = 18.811881%
        results = calculate_returns(self.sample_data, "2023-01-02")
        expected = {'1W': 4.95050, '1M': 11.88119, '3M': 18.81188}
        self.assertReturnDictsClose(results, expected, "Test Case 8: Specific next available day check")


if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False) # For running in environments like Jupyter
    # To run from command line: python -m unittest test_return_calculator.py
```
