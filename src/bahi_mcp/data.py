"""Data access layer: thin wrapper around the `mftool` library (AMFI data).

Targets mftool 3.4+, which caches AMFI data itself (NAVs for 24 hours, scheme
codes for 7 days) and has built-in ranked scheme search. This layer is
defensive about return shapes (dict, JSON string or DataFrame) and turns
network failures into clear errors. mftool is imported lazily so analytics and
tests work without network access.
"""

from __future__ import annotations

import functools
import json
import socket
from datetime import date, datetime
from functools import lru_cache
from typing import Any
from urllib.error import URLError

from .analytics import NavSeries, parse_date

MAX_HOLDINGS = 50
_NETWORK_ERRORS = (URLError, ConnectionError, TimeoutError, socket.timeout)


@lru_cache(maxsize=1)
def _client() -> Any:
    from mftool import Mftool  # lazy import

    return Mftool()


def _guard(fn):
    """mftool does not handle network errors; give callers a clear message."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except _NETWORK_ERRORS as exc:
            raise RuntimeError(
                "Could not reach the AMFI data source. Check the internet "
                "connection and try again."
            ) from exc

    return wrapper


def _all_schemes() -> dict[str, str]:
    # mftool caches the scheme list itself, so no extra caching here.
    codes = _client().get_scheme_codes()
    if not codes:
        raise RuntimeError("Could not load the AMFI scheme list. Try again later.")
    return {str(code): str(name) for code, name in codes.items()}


def _normalise_search(results: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in results or []:
        if not isinstance(item, dict):
            continue
        code = item.get("code") or item.get("scheme_code")
        name = item.get("name") or item.get("scheme_name")
        if code and name:
            out.append({"scheme_code": str(code), "scheme_name": str(name)})
    return out


@_guard
def search_schemes(query: str, limit: int = 20) -> list[dict[str, str]]:
    """Search scheme names. Uses mftool's ranked search when available."""
    words = [w for w in query.lower().split() if w]
    if not words:
        raise ValueError("query must not be empty.")
    limit = max(1, min(int(limit), 100))

    native = getattr(_client(), "search_schemes", None)
    if callable(native):
        try:
            results = native(query, limit=limit)
        except TypeError:
            results = native(query)
        found = _normalise_search(results)
        if found:
            return found[:limit]

    matches = [
        {"scheme_code": code, "scheme_name": name}
        for code, name in _all_schemes().items()
        if all(w in name.lower() for w in words)
    ]
    return matches[:limit]


@_guard
def get_scheme_quote(scheme_code: str) -> dict[str, Any]:
    quote = _client().get_scheme_quote(str(scheme_code))
    if not quote:
        raise ValueError(f"No quote found for scheme code {scheme_code}.")
    return quote


@_guard
def get_scheme_details(scheme_code: str) -> dict[str, Any]:
    details = _client().get_scheme_details(str(scheme_code))
    if not details:
        raise ValueError(f"No details found for scheme code {scheme_code}.")
    return details


def _history_rows(raw: Any) -> list[tuple[Any, Any]]:
    """Extract (date, nav) pairs from a dict, JSON string or DataFrame."""
    if isinstance(raw, (str, bytes)):
        raw = json.loads(raw)
    if hasattr(raw, "iterrows"):  # pandas DataFrame indexed by date
        return [(idx, row["nav"]) for idx, row in raw.iterrows()]
    if isinstance(raw, dict):
        return [(r.get("date"), r.get("nav")) for r in (raw.get("data") or []) if isinstance(r, dict)]
    return []


@_guard
def get_nav_series(scheme_code: str) -> NavSeries:
    """Full NAV history as a list of (date, nav) sorted ascending."""
    raw = _client().get_scheme_historical_nav(
        str(scheme_code), as_Dataframe=False, as_json=False
    )
    series: list[tuple[date, float]] = []
    for raw_date, raw_nav in _history_rows(raw):
        try:
            d = raw_date.date() if isinstance(raw_date, datetime) else parse_date(raw_date)
            series.append((d, float(raw_nav)))
        except (ValueError, TypeError, AttributeError):
            continue  # skip malformed rows
    if not series:
        raise ValueError(f"No NAV history found for scheme code {scheme_code}.")
    series.sort(key=lambda x: x[0])
    return series


@_guard
def portfolio_value(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    """Value holdings at latest NAV. Each: {"scheme_code": "119551", "units": 10}."""
    if not holdings or len(holdings) > MAX_HOLDINGS:
        raise ValueError(f"Provide between 1 and {MAX_HOLDINGS} holdings.")
    cleaned = []
    for h in holdings:
        try:
            code = str(h["scheme_code"]).strip()
            units = float(h["units"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                'Each holding needs "scheme_code" and numeric "units".'
            ) from exc
        if not code or units <= 0:
            raise ValueError("scheme_code must be set and units must be positive.")
        cleaned.append({"scheme_code": code, "units": units})
    result = _client().calculate_portfolio_value(cleaned)
    if not result:
        raise ValueError("Could not value the portfolio. Check the scheme codes.")
    return result


def clear_cache() -> dict[str, Any]:
    """Clear mftool's cache so the next call fetches fresh data."""
    clear = getattr(_client(), "clear_cache", None)
    if not callable(clear):
        raise RuntimeError("This mftool version has no cache control. Upgrade to mftool>=3.4.")
    clear()
    return {"cleared": True}
