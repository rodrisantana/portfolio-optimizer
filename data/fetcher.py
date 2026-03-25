import yfinance as yf # Yahoo Finance API for fetching historical price data.
import pandas as pd # Pandas for data manipulation and analysis.


class DataFetcher:
    """
    Downloads and cleans historical price data from Yahoo Finance.
    """

    def __init__(self, tickers: list[str], start: str, end: str): # Initialize with list of tickers and date range.
        self.tickers = tickers # List of stock tickers to fetch data for. ["AAPL", "MSFT"]
        self.start = start
        self.end = end
        self.prices = None 

    # Fetch historical price data for the specified tickers and date range.
    # The data is auto-adjusted for corporate actions and stored in self.prices.
    def fetch(self) -> pd.DataFrame:
        raw = yf.download( 
            tickers=self.tickers,
            start=self.start,
            end=self.end,
            auto_adjust=True,
            progress=False,
        )
        self.prices = raw["Close"].dropna()  # Keep only the 'Close' price and drop any rows with missing values.
        return self.prices

    def get_returns(self) -> pd.DataFrame:
        if self.prices is None:
            raise ValueError("Call fetch() before get_returns().")
        return self.prices.pct_change().dropna()