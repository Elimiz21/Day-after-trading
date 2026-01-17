"""NYSE trading calendar for T0/T1/T2 mapping.

Uses exchange_calendars library for production-grade NYSE calendar
covering the full 15+ year historical range required by the strategy.

BMO/AMC Handling:
-----------------
FMP API does not provide announcement time (BMO/AMC) in the current
subscription tier. We handle this as follows:

- BMO (Before Market Open): T1 = same trading day as earnings date
- AMC (After Market Close): T1 = next trading day after earnings date
- UNKNOWN: Treated as AMC (conservative default, most common case)

The session field is tracked per event for transparency and sensitivity analysis.
"""

from datetime import date, timedelta
from enum import Enum
from typing import Optional

import exchange_calendars as xcals
import pandas as pd


class EarningsSession(Enum):
    """Earnings announcement timing."""
    BMO = "bmo"  # Before Market Open
    AMC = "amc"  # After Market Close
    UNKNOWN = "unknown"  # Unknown timing (treated as AMC)


class TradingCalendar:
    """NYSE trading calendar using exchange_calendars library.

    Provides accurate trading day calculations for the full
    historical range (2010-2025+) required by the strategy.
    """

    def __init__(self):
        # NYSE calendar - covers 1885 to ~2050
        self.calendar = xcals.get_calendar("XNYS")

        # Cache schedule for faster lookups
        self._schedule = None
        self._schedule_start = None
        self._schedule_end = None

    def _ensure_schedule(self, start: date, end: date):
        """Ensure we have a cached schedule covering the date range."""
        buffer = timedelta(days=30)
        start_ts = pd.Timestamp(start) - buffer
        end_ts = pd.Timestamp(end) + buffer

        if (self._schedule is None or
            start_ts < self._schedule_start or
            end_ts > self._schedule_end):
            self._schedule_start = start_ts
            self._schedule_end = end_ts
            self._schedule = self.calendar.schedule(
                start=start_ts.strftime("%Y-%m-%d"),
                end=end_ts.strftime("%Y-%m-%d")
            )

    def is_trading_day(self, d: date) -> bool:
        """Check if a date is a NYSE trading day."""
        if isinstance(d, pd.Timestamp):
            d = d.date()

        ts = pd.Timestamp(d)
        return self.calendar.is_session(ts)

    def next_trading_day(self, d: date, offset: int = 1) -> date:
        """Get the next N-th trading day after d.

        Args:
            d: Starting date
            offset: Number of trading days to advance (default 1)

        Returns:
            The next trading day
        """
        if isinstance(d, pd.Timestamp):
            d = d.date()

        ts = pd.Timestamp(d)

        # Find next session after d
        count = 0
        current = ts
        while count < offset:
            try:
                next_session = self.calendar.next_session(current)
                current = next_session
                count += 1
            except ValueError:
                # Beyond calendar range
                current = current + pd.Timedelta(days=1)
                while current.weekday() >= 5:  # Skip weekends
                    current = current + pd.Timedelta(days=1)
                count += 1

        return current.date()

    def prev_trading_day(self, d: date, offset: int = 1) -> date:
        """Get the previous N-th trading day before d.

        Args:
            d: Starting date
            offset: Number of trading days to go back (default 1)

        Returns:
            The previous trading day
        """
        if isinstance(d, pd.Timestamp):
            d = d.date()

        ts = pd.Timestamp(d)

        count = 0
        current = ts
        while count < offset:
            try:
                prev_session = self.calendar.previous_session(current)
                current = prev_session
                count += 1
            except ValueError:
                current = current - pd.Timedelta(days=1)
                while current.weekday() >= 5:
                    current = current - pd.Timedelta(days=1)
                count += 1

        return current.date()

    def get_t0_t1_t2(
        self,
        earnings_date: date,
        session: EarningsSession = EarningsSession.UNKNOWN
    ) -> dict:
        """Get T0, T1, T2 dates for an earnings event.

        Trading day definitions per strategy spec:

        For AMC (After Market Close) or UNKNOWN:
        - T0: Earnings date (must be trading day, else previous trading day)
        - T1: Next trading day after earnings date (first reaction day)
        - T2: Next trading day after T1 (entry day)

        For BMO (Before Market Open):
        - T0: Previous trading day before earnings date
        - T1: Earnings date itself (if trading day) - first reaction day
        - T2: Next trading day after T1 (entry day)

        Args:
            earnings_date: The earnings announcement date
            session: BMO, AMC, or UNKNOWN timing

        Returns:
            Dict with t0, t1, t2 dates and session info
        """
        if isinstance(earnings_date, pd.Timestamp):
            earnings_date = earnings_date.date()

        # Treat UNKNOWN as AMC (most conservative, most common)
        effective_session = session if session != EarningsSession.UNKNOWN else EarningsSession.AMC

        if effective_session == EarningsSession.AMC:
            # AMC: Earnings announced after market close on earnings_date
            # T0 = earnings_date (the day the news drops after close)
            # T1 = next trading day (first day market reacts)
            # T2 = next trading day after T1 (entry day)

            if self.is_trading_day(earnings_date):
                t0 = earnings_date
            else:
                # If earnings date is not a trading day (weekend/holiday),
                # T0 is the previous trading day
                t0 = self.prev_trading_day(earnings_date)

            t1 = self.next_trading_day(t0)
            t2 = self.next_trading_day(t1)

        else:  # BMO
            # BMO: Earnings announced before market open on earnings_date
            # T0 = previous trading day (last day before news)
            # T1 = earnings_date (first day market reacts)
            # T2 = next trading day after T1 (entry day)

            if self.is_trading_day(earnings_date):
                t1 = earnings_date
                t0 = self.prev_trading_day(earnings_date)
            else:
                # If earnings date is not a trading day,
                # T1 is the next trading day
                t1 = self.next_trading_day(earnings_date)
                t0 = self.prev_trading_day(earnings_date)

            t2 = self.next_trading_day(t1)

        return {
            "t0": t0,
            "t1": t1,
            "t2": t2,
            "session": session.value,
            "effective_session": effective_session.value,
        }

    def get_trading_days_range(self, start: date, end: date) -> list[date]:
        """Get all trading days in a date range.

        Args:
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            List of trading day dates
        """
        sessions = self.calendar.sessions_in_range(
            pd.Timestamp(start),
            pd.Timestamp(end)
        )
        return [s.date() for s in sessions]
