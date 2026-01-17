"""FMP API client for S&P 500 data ingestion.

Uses FMP Stable API endpoints (as of Jan 2025):
- /stable/earnings: Historical earnings by symbol
- /stable/historical-price-eod/full: Historical daily OHLCV

Note: /stable/sp500-constituent requires higher tier subscription.
For Phase 1 smoke test, we use a hardcoded S&P 500 sample.
"""

import os
import time
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

FMP_BASE_URL = "https://financialmodelingprep.com"


class FMPClient:
    """Client for Financial Modeling Prep API (Stable endpoints)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY not found in environment or argument")
        self._request_delay = 0.25  # Rate limiting

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make GET request to FMP API."""
        params = params or {}
        params["apikey"] = self.api_key
        url = f"{FMP_BASE_URL}/{endpoint}"

        time.sleep(self._request_delay)  # Rate limiting
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_sp500_constituents_sample(self, tickers: list[str]) -> pd.DataFrame:
        """Get sample S&P 500 constituents for selected tickers.

        Note: The /stable/sp500-constituent endpoint requires a higher tier.
        For Phase 1, we create a sample DataFrame with selected tickers.

        Args:
            tickers: List of ticker symbols

        Returns:
            DataFrame with basic ticker info
        """
        # Hardcoded sector info for our Phase 1 tickers
        sector_map = {
            "AAPL": ("Apple Inc.", "Technology"),
            "JPM": ("JPMorgan Chase & Co.", "Financials"),
            "JNJ": ("Johnson & Johnson", "Healthcare"),
            "XOM": ("Exxon Mobil Corporation", "Energy"),
            "WMT": ("Walmart Inc.", "Consumer Defensive"),
        }

        data = []
        for ticker in tickers:
            name, sector = sector_map.get(ticker, (ticker, "Unknown"))
            data.append({
                "symbol": ticker,
                "name": name,
                "sector": sector,
            })

        return pd.DataFrame(data)

    def get_earnings_historical(
        self,
        symbol: str,
        limit: int = 20
    ) -> pd.DataFrame:
        """Get historical earnings dates for a symbol.

        Uses /stable/earnings endpoint.

        Args:
            symbol: Stock ticker
            limit: Max number of earnings events to return

        Returns:
            DataFrame with earnings dates and EPS data
        """
        try:
            data = self._get("stable/earnings", {"symbol": symbol, "limit": limit})
        except requests.HTTPError as e:
            print(f"  Warning: Failed to fetch earnings for {symbol}: {e}")
            return pd.DataFrame()

        if not data or isinstance(data, str):
            return pd.DataFrame()

        df = pd.DataFrame(data)
        if df.empty:
            return df

        # Add symbol column if not present
        if "symbol" not in df.columns:
            df["symbol"] = symbol

        # Rename date column for consistency
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        return df

    def get_historical_prices(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Get historical daily OHLCV data.

        Uses /stable/historical-price-eod/full endpoint.

        Args:
            symbol: Stock ticker
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with date, open, high, low, close, volume
        """
        params = {"symbol": symbol}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        try:
            data = self._get("stable/historical-price-eod/full", params)
        except requests.HTTPError as e:
            print(f"  Warning: Failed to fetch prices for {symbol}: {e}")
            return pd.DataFrame()

        if not data or isinstance(data, str):
            return pd.DataFrame()

        df = pd.DataFrame(data)
        if df.empty:
            return df

        # Ensure symbol column
        if "symbol" not in df.columns:
            df["symbol"] = symbol

        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
