"""bahi-mcp MCP server entry point."""

from __future__ import annotations

from datetime import date
from typing import Any
from mcp.server.fastmcp import FastMCP
from . import analytics, data

DISCLAIMER = (
    "Informational only. Not investment advice. Figures are derived from "
    "publicly available AMFI data and may be delayed or inaccurate."
)

mcp = FastMCP("bahi-mcp")


@mcp.tool()
def search_schemes(query: str, limit: int = 20) -> list[dict[str, str]]:
    """Search Indian mutual fund schemes by name (e.g. 'sbi midcap direct growth').

    Returns scheme codes (AMFI) and names. Use a code with the other tools.
    """
    return data.search_schemes(query, limit)


@mcp.tool()
def get_scheme_quote(scheme_code: str) -> dict[str, Any]:
    """Latest NAV and basic quote for a scheme, by AMFI scheme code."""
    return data.get_scheme_quote(scheme_code)


@mcp.tool()
def get_scheme_details(scheme_code: str) -> dict[str, Any]:
    """Fund house, scheme type, category and start date for a scheme code."""
    return data.get_scheme_details(scheme_code)


@mcp.tool()
def get_nav_history(
    scheme_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    max_points: int = 100,
) -> dict[str, Any]:
    """NAV history for a scheme. Dates as DD-MM-YYYY or YYYY-MM-DD.

    Returns at most `max_points` of the most recent points in the range, to keep
    responses small.
    """
    series = data.get_nav_series(scheme_code)
    start = analytics.parse_date(start_date) if start_date else None
    end = analytics.parse_date(end_date) if end_date else None
    rows = [
        (d, nav)
        for d, nav in series
        if (start is None or d >= start) and (end is None or d <= end)
    ]
    max_points = max(1, min(max_points, 1000))
    trimmed = rows[-max_points:]
    return {
        "scheme_code": scheme_code,
        "points_returned": len(trimmed),
        "points_in_range": len(rows),
        "history": [{"date": d.isoformat(), "nav": nav} for d, nav in trimmed],
    }


@mcp.tool()
def calculate_sip_returns(
    scheme_code: str,
    monthly_amount: float,
    start_date: str,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Simulate a monthly SIP in a scheme using its real NAV history.

    Returns total invested, units, current value, absolute return and XIRR.
    `end_date` defaults to today. Dates as DD-MM-YYYY or YYYY-MM-DD.
    """
    series = data.get_nav_series(scheme_code)
    end = analytics.parse_date(end_date) if end_date else date.today()
    result = analytics.sip_simulation(
        series, monthly_amount, analytics.parse_date(start_date), end
    )
    result["scheme_code"] = scheme_code
    result["disclaimer"] = DISCLAIMER
    return result


@mcp.tool()
def calculate_xirr(cashflows: list[dict[str, Any]]) -> dict[str, Any]:
    """XIRR for dated cash flows.

    Each item: {"date": "YYYY-MM-DD", "amount": -10000}. Investments are
    negative, redemptions / current value positive.
    """
    flows = [(analytics.parse_date(c["date"]), float(c["amount"])) for c in cashflows]
    rate = analytics.xirr(flows)
    return {"xirr_pct": round(rate * 100.0, 2), "disclaimer": DISCLAIMER}


@mcp.tool()
def calculate_cagr(
    initial_value: float, final_value: float, start_date: str, end_date: str
) -> dict[str, Any]:
    """CAGR between two values over a date range."""
    rate = analytics.cagr(
        initial_value,
        final_value,
        analytics.parse_date(start_date),
        analytics.parse_date(end_date),
    )
    return {"cagr_pct": round(rate * 100.0, 2), "disclaimer": DISCLAIMER}


def main() -> None:
    """Run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
