"""Stock and index data for NSE/BSE via Yahoo Finance (the `yfinance` package).

This is an UNOFFICIAL, best-effort data source: it can be delayed, rate-limited
or change without notice. yfinance is an optional install:

    pip install "bahi-mcp[stocks]"
"""

from __future__ import annotations

from typing import Any

INDEX_MAP = {
    "nifty": "^NSEI",
    "nifty50": "^NSEI",
    "sensex": "^BSESN",
    "banknifty": "^NSEBANK",
    "niftybank": "^NSEBANK",
    "niftyit": "^CNXIT",
    "indiavix": "^INDIAVIX",
}
VALID_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
VALID_INTERVALS = {"1d", "5d", "1wk", "1mo"}
EXCHANGE_SUFFIX = {"NSE": ".NS", "BSE": ".BO"}


def normalize_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Turn 'reliance' into 'RELIANCE.NS'. Index tickers and suffixed symbols pass through."""
    sym = symbol.strip().upper()
    if not sym:
        raise ValueError("symbol must not be empty.")
    if sym.startswith("^") or "." in sym:
        return sym
    ex = exchange.strip().upper()
    if ex not in EXCHANGE_SUFFIX:
        raise ValueError("exchange must be 'NSE' or 'BSE'.")
    return sym + EXCHANGE_SUFFIX[ex]


def resolve_index(name: str) -> str:
    key = "".join(ch for ch in name.lower() if ch.isalnum())
    if key in INDEX_MAP:
        return INDEX_MAP[key]
    raise ValueError(f"Unknown index '{name}'. Supported: {', '.join(sorted(set(INDEX_MAP)))}.")


def _yf():
    try:
        import yfinance  # lazy import
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Stock data needs yfinance. Install with: pip install 'bahi-mcp[stocks]'"
        ) from exc
    return yfinance


def _fast(info: Any, snake: str, camel: str) -> Any:
    for getter in (lambda: getattr(info, snake), lambda: info[camel], lambda: info[snake]):
        try:
            value = getter()
            if value is not None:
                return value
        except Exception:  # noqa: BLE001 - different yfinance versions expose different keys
            continue
    return None


def get_quote(ticker: str) -> dict[str, Any]:
    info = _yf().Ticker(ticker).fast_info
    last = _fast(info, "last_price", "lastPrice")
    prev = _fast(info, "previous_close", "previousClose")
    if last is None:
        raise ValueError(f"No quote found for '{ticker}'. Check the symbol and exchange.")
    change = (last - prev) if prev else None
    return {
        "symbol": ticker,
        "last_price": round(float(last), 2),
        "previous_close": round(float(prev), 2) if prev else None,
        "change": round(float(change), 2) if change is not None else None,
        "change_pct": round(change / prev * 100.0, 2) if change is not None and prev else None,
        "day_high": _round(_fast(info, "day_high", "dayHigh")),
        "day_low": _round(_fast(info, "day_low", "dayLow")),
        "year_high": _round(_fast(info, "year_high", "yearHigh")),
        "year_low": _round(_fast(info, "year_low", "yearLow")),
        "currency": _fast(info, "currency", "currency"),
        "source": "Yahoo Finance (unofficial, may be delayed)",
    }


def _round(value: Any) -> float | None:
    return round(float(value), 2) if value is not None else None


def get_history(
    ticker: str, period: str = "1y", interval: str = "1d", max_points: int = 120
) -> dict[str, Any]:
    if period not in VALID_PERIODS:
        raise ValueError(f"period must be one of {sorted(VALID_PERIODS)}.")
    if interval not in VALID_INTERVALS:
        raise ValueError(f"interval must be one of {sorted(VALID_INTERVALS)}.")
    frame = _yf().Ticker(ticker).history(period=period, interval=interval)
    if frame is None or frame.empty:
        raise ValueError(f"No price history found for '{ticker}'.")
    max_points = max(1, min(int(max_points), 1000))
    tail = frame.tail(max_points)
    rows = [
        {
            "date": idx.date().isoformat(),
            "open": round(float(r["Open"]), 2),
            "high": round(float(r["High"]), 2),
            "low": round(float(r["Low"]), 2),
            "close": round(float(r["Close"]), 2),
            "volume": int(r["Volume"]),
        }
        for idx, r in tail.iterrows()
    ]
    return {
        "symbol": ticker,
        "period": period,
        "interval": interval,
        "points_returned": len(rows),
        "history": rows,
        "source": "Yahoo Finance (unofficial, may be delayed)",
    }
