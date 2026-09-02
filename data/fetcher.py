import os

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

    def fetch(self, cache_path: str = "data/prices.csv") -> pd.DataFrame:
        # Cached prices make the pipeline reproducible: yfinance revises historical
        # dividend/split adjustment factors, so a fresh download changes the results.
        if os.path.exists(cache_path):
            cached = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            # Guard against a stale cache built for a different universe.
            if list(cached.columns) != list(self.tickers):
                raise ValueError(
                    f"Cache {cache_path} holds {list(cached.columns)}, "
                    f"but TICKERS is {self.tickers}. Delete the cache to refresh."
                )
            self.prices = cached
            print(f"Loaded cached prices from {cache_path} ({len(cached)} rows)")
            return self.prices

        raw = yf.download(
            tickers=self.tickers,
            start=self.start,
            end=self.end,
            auto_adjust=True,   # adjusts for BOTH splits and dividends -> total returns
            progress=False,
        )
        close = raw["Close"]
        if isinstance(close, pd.Series):          # single-ticker edge case
            close = close.to_frame(self.tickers[0])

        # yfinance sorts columns alphabetically, NOT in the order requested.
        missing = [t for t in self.tickers if t not in close.columns]
        if missing:
            raise ValueError(f"No data returned for: {missing}")
        close = close[self.tickers]

        before = len(close)
        self.prices = close.dropna()
        if before - len(self.prices):
            print(f"WARNING: dropped {before - len(self.prices)} of {before} rows")
        if self.prices.empty:
            raise ValueError("No overlapping data across tickers.")

        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        self.prices.to_csv(cache_path)
        print(f"Cached prices to {cache_path}")
        return self.prices

    def get_returns(self) -> pd.DataFrame:
        if self.prices is None:
            raise ValueError("Call fetch() before get_returns().")
        return self.prices.pct_change().dropna()