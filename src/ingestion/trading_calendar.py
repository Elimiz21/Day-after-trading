"""NYSE trading calendar for T0/T1/T2 mapping.

Limitations (Phase 1):
- Uses a minimal NYSE holiday list for 2020-2025
- Does not include early close days
- For production, consider using `exchange_calendars` or `pandas_market_calendars`
"""

from datetime import date, timedelta
from typing import Optional

import pandas as pd

# NYSE observed holidays (2020-2025)
# Source: NYSE holiday schedule
NYSE_HOLIDAYS = {
    # 2020
    date(2020, 1, 1),   # New Year's Day
    date(2020, 1, 20),  # MLK Day
    date(2020, 2, 17),  # Presidents Day
    date(2020, 4, 10),  # Good Friday
    date(2020, 5, 25),  # Memorial Day
    date(2020, 7, 3),   # Independence Day (observed)
    date(2020, 9, 7),   # Labor Day
    date(2020, 11, 26), # Thanksgiving
    date(2020, 12, 25), # Christmas

    # 2021
    date(2021, 1, 1),   # New Year's Day
    date(2021, 1, 18),  # MLK Day
    date(2021, 2, 15),  # Presidents Day
    date(2021, 4, 2),   # Good Friday
    date(2021, 5, 31),  # Memorial Day
    date(2021, 7, 5),   # Independence Day (observed)
    date(2021, 9, 6),   # Labor Day
    date(2021, 11, 25), # Thanksgiving
    date(2021, 12, 24), # Christmas (observed)

    # 2022
    date(2022, 1, 17),  # MLK Day
    date(2022, 2, 21),  # Presidents Day
    date(2022, 4, 15),  # Good Friday
    date(2022, 5, 30),  # Memorial Day
    date(2022, 6, 20),  # Juneteenth (observed)
    date(2022, 7, 4),   # Independence Day
    date(2022, 9, 5),   # Labor Day
    date(2022, 11, 24), # Thanksgiving
    date(2022, 12, 26), # Christmas (observed)

    # 2023
    date(2023, 1, 2),   # New Year's Day (observed)
    date(2023, 1, 16),  # MLK Day
    date(2023, 2, 20),  # Presidents Day
    date(2023, 4, 7),   # Good Friday
    date(2023, 5, 29),  # Memorial Day
    date(2023, 6, 19),  # Juneteenth
    date(2023, 7, 4),   # Independence Day
    date(2023, 9, 4),   # Labor Day
    date(2023, 11, 23), # Thanksgiving
    date(2023, 12, 25), # Christmas

    # 2024
    date(2024, 1, 1),   # New Year's Day
    date(2024, 1, 15),  # MLK Day
    date(2024, 2, 19),  # Presidents Day
    date(2024, 3, 29),  # Good Friday
    date(2024, 5, 27),  # Memorial Day
    date(2024, 6, 19),  # Juneteenth
    date(2024, 7, 4),   # Independence Day
    date(2024, 9, 2),   # Labor Day
    date(2024, 11, 28), # Thanksgiving
    date(2024, 12, 25), # Christmas

    # 2025
    date(2025, 1, 1),   # New Year's Day
    date(2025, 1, 20),  # MLK Day
    date(2025, 2, 17),  # Presidents Day
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 26),  # Memorial Day
    date(2025, 6, 19),  # Juneteenth
    date(2025, 7, 4),   # Independence Day
    date(2025, 9, 1),   # Labor Day
    date(2025, 11, 27), # Thanksgiving
    date(2025, 12, 25), # Christmas
}


class TradingCalendar:
    """NYSE trading calendar for computing trading day offsets."""

    def __init__(self):
        self.holidays = NYSE_HOLIDAYS

    def is_trading_day(self, d: date) -> bool:
        """Check if a date is a NYSE trading day."""
        if isinstance(d, pd.Timestamp):
            d = d.date()
        # Weekends
        if d.weekday() >= 5:
            return False
        # Holidays
        if d in self.holidays:
            return False
        return True

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

        count = 0
        current = d
        while count < offset:
            current = current + timedelta(days=1)
            if self.is_trading_day(current):
                count += 1
        return current

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

        count = 0
        current = d
        while count < offset:
            current = current - timedelta(days=1)
            if self.is_trading_day(current):
                count += 1
        return current

    def get_t0_t1_t2(self, earnings_date: date) -> dict:
        """Get T0, T1, T2 dates for an earnings event.

        T0: The earnings date itself (or previous trading day if not a trading day)
        T1: Next trading day after earnings date
        T2: Next trading day after T1

        Args:
            earnings_date: The earnings announcement date

        Returns:
            Dict with t0, t1, t2 dates
        """
        if isinstance(earnings_date, pd.Timestamp):
            earnings_date = earnings_date.date()

        # T0: Use earnings_date if it's a trading day, else previous trading day
        if self.is_trading_day(earnings_date):
            t0 = earnings_date
        else:
            t0 = self.prev_trading_day(earnings_date)

        # T1: Next trading day after earnings date
        t1 = self.next_trading_day(earnings_date)

        # T2: Next trading day after T1
        t2 = self.next_trading_day(t1)

        return {"t0": t0, "t1": t1, "t2": t2}
