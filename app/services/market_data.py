"""Market data access.

This is the ONLY module in StockEx that knows Yahoo Finance exists. Every
other part of the app asks for a Quote or a list of DailyBars and does not
care where they came from.

That isolation is not architectural decoration. yfinance is an unofficial
library scraping a free service; it will break or change at some point.
When it does, the fix is a new class in this file, not a hunt through the
codebase. The `MarketDataProvider` protocol below is the contract any
replacement has to satisfy.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Quote:
    """A single current (delayed) price."""

    symbol: str
    price: Decimal
    as_of: date


@dataclass(frozen=True)
class DailyBar:
    """One trading day of prices for a stock."""

    price_date: date
    open_price: Decimal | None
    high_price: Decimal | None
    low_price: Decimal | None
    close_price: Decimal
    volume: int | None


class MarketDataProvider(Protocol):
    """What any market data source must provide.

    A Protocol is a structural interface: a class satisfies it by having
    these methods, without inheriting anything. So a replacement provider
    — or a fake one in tests — just needs the same two methods.
    """

    def get_quote(self, yahoo_symbol: str) -> Quote | None: ...

    def get_history(self, yahoo_symbol: str, period: str = "1y") -> list[DailyBar]: ...


def _to_decimal(value: object) -> Decimal | None:
    """Convert a value from the data provider into an exact Decimal.

    Via str() deliberately. Decimal(0.1) captures the float's binary
    error and gives 0.1000000000000000055511151231257827; Decimal("0.1")
    gives exactly 0.1. Money must never inherit float noise.
    """
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if result.is_nan():
        return None
    return result.quantize(Decimal("0.01"))


class YahooFinanceProvider:
    """Market data from Yahoo Finance, via the yfinance library.

    Quotes are cached in memory for fifteen minutes, which matches the
    delay on the free feed — asking more often cannot produce a newer
    number, and would just risk being rate-limited.
    """

    def __init__(self, cache_seconds: int = 900) -> None:
        self._cache_seconds = cache_seconds
        self._quote_cache: dict[str, tuple[Quote, float]] = {}

    def get_quote(self, yahoo_symbol: str) -> Quote | None:
        cached = self._quote_cache.get(yahoo_symbol)
        if cached is not None:
            quote, fetched_at = cached
            if time.monotonic() - fetched_at < self._cache_seconds:
                return quote

        bars = self.get_history(yahoo_symbol, period="5d")
        if not bars:
            return None

        latest = bars[-1]
        quote = Quote(
            symbol=yahoo_symbol,
            price=latest.close_price,
            as_of=latest.price_date,
        )
        self._quote_cache[yahoo_symbol] = (quote, time.monotonic())
        return quote

    def get_history(self, yahoo_symbol: str, period: str = "1y") -> list[DailyBar]:
        """Fetch daily bars. Returns an empty list on any failure.

        Every failure mode is swallowed and logged rather than raised. A
        third-party outage must degrade the dashboard — showing holdings
        without current prices — not break it. The caller decides what to
        display when a price is missing.
        """
        try:
            import yfinance

            frame = yfinance.Ticker(yahoo_symbol).history(period=period)
        except Exception as error:  # noqa: BLE001 - deliberately broad
            logger.warning("Market data fetch failed for %s: %s", yahoo_symbol, error)
            return []

        if frame is None or frame.empty:
            logger.info("No market data returned for %s", yahoo_symbol)
            return []

        bars: list[DailyBar] = []
        for timestamp, row in frame.iterrows():
            close = _to_decimal(row.get("Close"))
            if close is None:
                continue

            volume_raw = row.get("Volume")
            try:
                volume = int(volume_raw) if volume_raw is not None else None
            except (ValueError, TypeError):
                volume = None

            bars.append(
                DailyBar(
                    price_date=timestamp.date(),
                    open_price=_to_decimal(row.get("Open")),
                    high_price=_to_decimal(row.get("High")),
                    low_price=_to_decimal(row.get("Low")),
                    close_price=close,
                    volume=volume,
                )
            )

        return bars


# One shared instance, so the cache is shared across requests.
market_data = YahooFinanceProvider()
