"""Data access layer: thin wrapper around the `mftool` library (AMFI data).

mftool is imported lazily so analytics and tests work without network access.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .analytics import NavSeries, parse_date


@lru_cache(maxsize=1)
def _client() -> Any:
    from mftool import Mftool  # lazy import

    return Mftool()


@lru_cache(maxsize=1)
def _all_schemes() -> dict[str, str]:
    codes = _client().get_scheme_codes()
    if not codes:
        raise RuntimeError("Could not load the AMFI scheme list. Try again later.")
    return {str(code): str(name) for code, name in codes.items()}


def search_schemes(query: str, limit: int = 20) -> list[dict[str, str]]:
    """Case-insensitive search of scheme names. All words must match."""
    words = [w for w in query.lower().split() if w]
    if not words:
        raise ValueError("query must not be empty.")
    matches = [
        {"scheme_code": code, "scheme_name": name}
        for code, name in _all_schemes().items()
        if all(w in name.lower() for w in words)
    ]
    return matches[: max(1, min(limit, 100))]


def get_scheme_quote(scheme_code: str) -> dict[str, Any]:
    quote = _client().get_scheme_quote(str(scheme_code))
    if not quote:
        raise ValueError(f"No quote found for scheme code {scheme_code}.")
    return quote


def get_scheme_details(scheme_code: str) -> dict[str, Any]:
    details = _client().get_scheme_details(str(scheme_code))
    if not details:
        raise ValueError(f"No details found for scheme code {scheme_code}.")
    return details


def get_nav_series(scheme_code: str) -> NavSeries:
    """Full NAV history as a list of (date, nav) sorted ascending."""
    raw = _client().get_scheme_historical_nav(str(scheme_code))
    rows = (raw or {}).get("data") or []
    series: list[tuple] = []
    for row in rows:
        try:
            series.append((parse_date(row["date"]), float(row["nav"])))
        except (KeyError, ValueError, TypeError):
            continue  # skip malformed rows
    if not series:
        raise ValueError(f"No NAV history found for scheme code {scheme_code}.")
    series.sort(key=lambda x: x[0])
    return series
