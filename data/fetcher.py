import yfinance as yf # Yahoo Finance API for fetching historical price data.
import pandas as pd # Pandas for data manipulation and analysis.


class DataFetcher:
    """
    Downloads and cleans historical price data from Yahoo Finance.
    """

    def __init__(self, tickers: list[str], start: str, end: str): # Initialize with list of tickers and date range.
        self.tickers = tickers # List of stock tickers to fetch data for. ["AAPL", "MSFT", ...]
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
        close = raw["Close"]
        
        # yfinance returns columns sorted alphabetically, NOT in the order requested.
        # Reindexing explicitly is what guarantees weights map to the right asset.
        missing = [ticket for ticket in self.tickers if ticket not in close.columns]
        if missing:
            raise ValueError(f"No data returned for: {missing}")
        close = close[self.tickers]
        
        before = len(close)
        self.prices = close.dropna()
        dropped = before - len(self.prices)
        if dropped > 0:
            print(f"Warning: Dropped {dropped} of {before} rows with missing data.")
        if self.prices.empty:
            raise ValueError("No valid price data after dropping missing rows.")



        return self.prices

    def get_returns(self) -> pd.DataFrame:
        if self.prices is None:
            raise ValueError("Call fetch() before get_returns().")
        return self.prices.pct_change().dropna()