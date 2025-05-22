import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
import sys
from io import StringIO

# Assuming data_fetcher.py is in the same directory or accessible via PYTHONPATH
from data_fetcher import fetch_stock_data

# Helper function to create a sample DataFrame
def create_sample_df():
    return pd.DataFrame({'Close': [100, 101, 102]})

class TestDataFetcher(unittest.TestCase):

    def setUp(self):
        # Redirect stderr to capture print statements for some tests
        self.held_stderr = sys.stderr
        sys.stderr = StringIO()

    def tearDown(self):
        # Restore stderr
        sys.stderr = self.held_stderr

    @patch('data_fetcher.yf.Ticker')
    def test_fetch_success_ns_suffix(self, mock_ticker):
        # a. Successful fetch with .NS suffix
        sample_df = create_sample_df()
        mock_instance = MagicMock()
        mock_instance.history.return_value = sample_df
        
        # Configure the mock_ticker to return different instances based on symbol
        def ticker_side_effect(symbol_arg):
            if symbol_arg == "RELIANCE.NS":
                return mock_instance
            # Add more conditions if other symbols are tried in this test, though not expected
            return MagicMock(history=MagicMock(return_value=pd.DataFrame())) # Default empty for others

        mock_ticker.side_effect = ticker_side_effect
        
        df, resolved_symbol = fetch_stock_data("reliance", "2023-01-01")
        
        self.assertIsNotNone(df)
        pd.testing.assert_frame_equal(df, sample_df)
        self.assertEqual(resolved_symbol, "RELIANCE.NS")
        mock_ticker.assert_any_call("RELIANCE.NS")


    @patch('data_fetcher.yf.Ticker')
    def test_fetch_success_bo_suffix(self, mock_ticker):
        # b. Successful fetch with .BO suffix (after .NS fails)
        sample_df = create_sample_df()
        
        mock_ns_instance = MagicMock()
        mock_ns_instance.history.return_value = pd.DataFrame() # .NS returns empty

        mock_bo_instance = MagicMock()
        mock_bo_instance.history.return_value = sample_df # .BO returns data
        
        def ticker_side_effect(symbol_arg):
            if symbol_arg == "MYCOMPANY.NS":
                return mock_ns_instance
            elif symbol_arg == "MYCOMPANY.BO":
                return mock_bo_instance
            return MagicMock(history=MagicMock(return_value=pd.DataFrame()))

        mock_ticker.side_effect = ticker_side_effect
        
        df, resolved_symbol = fetch_stock_data("mycompany", "2023-01-01")
        
        self.assertIsNotNone(df)
        pd.testing.assert_frame_equal(df, sample_df)
        self.assertEqual(resolved_symbol, "MYCOMPANY.BO")
        mock_ticker.assert_any_call("MYCOMPANY.NS")
        mock_ticker.assert_any_call("MYCOMPANY.BO")


    @patch('data_fetcher.yf.Ticker')
    def test_symbol_already_has_ns_suffix(self, mock_ticker):
        # c. Symbol already has .NS suffix (correct case)
        sample_df = create_sample_df()
        mock_instance = MagicMock()
        mock_instance.history.return_value = sample_df
        mock_ticker.return_value = mock_instance # Only INFY.NS should be called

        df, resolved_symbol = fetch_stock_data("INFY.NS", "2023-01-01")

        self.assertIsNotNone(df)
        pd.testing.assert_frame_equal(df, sample_df)
        self.assertEqual(resolved_symbol, "INFY.NS")
        mock_ticker.assert_called_once_with("INFY.NS")


    @patch('data_fetcher.yf.Ticker')
    def test_symbol_already_has_bo_suffix_mixed_case(self, mock_ticker):
        # d. Symbol already has .BO suffix (mixed case)
        sample_df = create_sample_df()
        mock_instance = MagicMock()
        mock_instance.history.return_value = sample_df
        mock_ticker.return_value = mock_instance # Only ASIANPAINT.BO should be called

        df, resolved_symbol = fetch_stock_data("asianpaint.bo", "2023-01-01")

        self.assertIsNotNone(df)
        pd.testing.assert_frame_equal(df, sample_df)
        self.assertEqual(resolved_symbol, "ASIANPAINT.BO")
        mock_ticker.assert_called_once_with("ASIANPAINT.BO")

    @patch('data_fetcher.yf.Ticker')
    def test_fetching_fails_for_all_attempts(self, mock_ticker):
        # e. Fetching fails for all attempts
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame() # Empty DataFrame for all attempts
        mock_ticker.return_value = mock_instance

        df, resolved_symbol = fetch_stock_data("nonexistentsymbol", "2023-01-01")

        self.assertIsNone(df)
        self.assertIsNone(resolved_symbol)
        mock_ticker.assert_any_call("NONEXISTENTSYMBOL.NS")
        mock_ticker.assert_any_call("NONEXISTENTSYMBOL.BO")
        self.assertEqual(mock_ticker.call_count, 2)


    @patch('data_fetcher.yf.Ticker')
    def test_fetching_fails_for_qualified_non_existent_symbol(self, mock_ticker):
        # f. Fetching fails for an already qualified but non-existent symbol
        mock_instance = MagicMock()
        mock_instance.history.return_value = pd.DataFrame() # Empty DataFrame
        mock_ticker.return_value = mock_instance

        df, resolved_symbol = fetch_stock_data("FAKESYMBOL.NS", "2023-01-01")

        self.assertIsNone(df)
        self.assertIsNone(resolved_symbol)
        mock_ticker.assert_called_once_with("FAKESYMBOL.NS")

    # No mock needed if date validation happens before Ticker call
    def test_invalid_date_format_string(self):
        # g. Invalid date format string
        # This test does not mock yf.Ticker as the function should fail before that.
        df, resolved_symbol = fetch_stock_data("RELIANCE", "2023/01/01")

        self.assertIsNone(df)
        self.assertIsNone(resolved_symbol)
        # Check stderr for the specific error message
        # self.assertIn("Error: Invalid date format for start_date_str '2023/01/01'", sys.stderr.getvalue())
        # Note: Checking stderr can be brittle. The primary check is the None return.
        # The data_fetcher already prints to stderr, so this is more of an integration check of that.


    @patch('data_fetcher.yf.Ticker')
    def test_case_sensitivity_resolves_uppercase(self, mock_ticker):
        # h. Test case sensitivity (input lowercase, resolves to uppercase)
        sample_df = create_sample_df()
        mock_instance = MagicMock()
        mock_instance.history.return_value = sample_df
        
        def ticker_side_effect(symbol_arg):
            if symbol_arg == "TCS.NS":
                return mock_instance
            return MagicMock(history=MagicMock(return_value=pd.DataFrame()))

        mock_ticker.side_effect = ticker_side_effect

        df, resolved_symbol = fetch_stock_data("tcs", "2023-01-01")

        self.assertIsNotNone(df)
        pd.testing.assert_frame_equal(df, sample_df)
        self.assertEqual(resolved_symbol, "TCS.NS")
        mock_ticker.assert_any_call("TCS.NS")
        # Depending on implementation, TCS.BO might or might not be called if TCS.NS is found first.
        # If TCS.NS is found, the loop should break.

    @patch('data_fetcher.yf.Ticker')
    def test_ns_fails_with_exception_bo_succeeds(self, mock_ticker):
        # Test case where .NS attempt raises an exception
        sample_df = create_sample_df()
        
        mock_ns_instance = MagicMock()
        mock_ns_instance.history.side_effect = Exception("Simulated yfinance error for NS")

        mock_bo_instance = MagicMock()
        mock_bo_instance.history.return_value = sample_df # .BO returns data
        
        def ticker_side_effect(symbol_arg):
            if symbol_arg == "ERRORSTOCK.NS":
                return mock_ns_instance
            elif symbol_arg == "ERRORSTOCK.BO":
                return mock_bo_instance
            return MagicMock(history=MagicMock(return_value=pd.DataFrame()))

        mock_ticker.side_effect = ticker_side_effect
        
        df, resolved_symbol = fetch_stock_data("errorstock", "2023-01-01")
        
        self.assertIsNotNone(df)
        pd.testing.assert_frame_equal(df, sample_df)
        self.assertEqual(resolved_symbol, "ERRORSTOCK.BO")
        mock_ticker.assert_any_call("ERRORSTOCK.NS")
        mock_ticker.assert_any_call("ERRORSTOCK.BO")

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
```
