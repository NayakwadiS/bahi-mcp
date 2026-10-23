"""bahi-mcp MCP server entry point."""

from __future__ import annotations

from datetime import date
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import analytics, calculators, data, fund_analytics, market

DISCLAIMER = (
    "Informational only. Not investment or tax advice. Figures come from public "
    "data sources or stated assumptions and may be delayed or inaccurate."
)

mcp = FastMCP("bahi-mcp")


def _with_disclaimer(result: dict[str, Any]) -> dict[str, Any]:
    result["disclaimer"] = DISCLAIMER
    return result


# --------------------------------------------------------------------------
# Mutual funds: data
# --------------------------------------------------------------------------


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
def get_portfolio_value(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    """Current value of a mutual fund portfolio at latest NAVs.

    Each holding: {"scheme_code": "119551", "units": 125.5}.
    """
    return _with_disclaimer(data.portfolio_value(holdings))


@mcp.tool()
def clear_cache() -> dict[str, Any]:
    """Clear cached AMFI data so the next call fetches fresh NAVs.

    NAVs are cached for 24 hours. AMFI usually publishes the day's NAVs after
    about 9 PM IST, so clear the cache after that to see them.
    """
    return data.clear_cache()


# --------------------------------------------------------------------------
# Mutual funds: analytics
# --------------------------------------------------------------------------


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
    return _with_disclaimer(result)


@mcp.tool()
def compare_funds(
    scheme_codes: list[str],
    risk_years: float = 3.0,
    risk_free_rate_pct: float = 6.5,
) -> dict[str, Any]:
    """Compare 1 to 5 mutual funds side by side.

    For each fund: latest NAV, 1/3/5-year annualised returns (null if the fund is
    too new), and risk over `risk_years`: volatility, max drawdown and Sharpe ratio.
    """
    if not 1 <= len(scheme_codes) <= 5:
        raise ValueError("Provide between 1 and 5 scheme codes.")
    funds: list[dict[str, Any]] = []
    for code in scheme_codes:
        entry: dict[str, Any] = {"scheme_code": code}
        try:
            try:
                entry["scheme_name"] = data.get_scheme_details(code).get("scheme_name")
            except Exception:  # noqa: BLE001 - name is a nice-to-have
                entry["scheme_name"] = None
            series = data.get_nav_series(code)
            entry.update(
                fund_analytics.fund_summary(series, risk_years, risk_free_rate_pct / 100.0)
            )
        except Exception as exc:  # noqa: BLE001 - one bad code should not sink the rest
            entry["error"] = str(exc)
        funds.append(entry)
    return _with_disclaimer({"funds": funds})


@mcp.tool()
def get_rolling_returns(
    scheme_code: str,
    window_years: float = 3.0,
    step_days: int = 30,
    threshold_pct: float = 12.0,
) -> dict[str, Any]:
    """Rolling-return distribution for a fund.

    Shows min, max, mean and median annualised return across all `window_years`
    windows in its history, plus how often it was positive and above
    `threshold_pct`. Better than a single start-to-end return.
    """
    series = data.get_nav_series(scheme_code)
    result = fund_analytics.rolling_returns(series, window_years, step_days, threshold_pct)
    result["scheme_code"] = scheme_code
    return _with_disclaimer(result)


# --------------------------------------------------------------------------
# Stocks and market data (needs: pip install "bahi-mcp[stocks]")
# --------------------------------------------------------------------------


@mcp.tool()
def get_stock_quote(symbol: str, exchange: str = "NSE") -> dict[str, Any]:
    """Latest price for an NSE/BSE stock, e.g. symbol 'RELIANCE' on exchange 'NSE'.

    Source is Yahoo Finance (unofficial, may be delayed).
    """
    return _with_disclaimer(market.get_quote(market.normalize_symbol(symbol, exchange)))


@mcp.tool()
def get_index_quote(index: str = "nifty50") -> dict[str, Any]:
    """Latest level of an Indian index: nifty50, sensex, banknifty, niftyit or indiavix."""
    return _with_disclaimer(market.get_quote(market.resolve_index(index)))


@mcp.tool()
def get_stock_history(
    symbol: str,
    exchange: str = "NSE",
    period: str = "1y",
    interval: str = "1d",
    max_points: int = 120,
) -> dict[str, Any]:
    """Price history (OHLCV) for an NSE/BSE stock or index ticker like '^NSEI'.

    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max.
    interval: 1d, 5d, 1wk, 1mo. Returns at most `max_points` recent rows.
    """
    return _with_disclaimer(
        market.get_history(
            market.normalize_symbol(symbol, exchange), period, interval, max_points
        )
    )


# --------------------------------------------------------------------------
# Calculators
# --------------------------------------------------------------------------


@mcp.tool()
def calculate_xirr(cashflows: list[dict[str, Any]]) -> dict[str, Any]:
    """XIRR for dated cash flows.

    Each item: {"date": "YYYY-MM-DD", "amount": -10000}. Investments are
    negative, redemptions / current value positive.
    """
    flows = [(analytics.parse_date(c["date"]), float(c["amount"])) for c in cashflows]
    rate = analytics.xirr(flows)
    return _with_disclaimer({"xirr_pct": round(rate * 100.0, 2)})


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
    return _with_disclaimer({"cagr_pct": round(rate * 100.0, 2)})


@mcp.tool()
def calculate_emi(principal: float, annual_rate_pct: float, years: float) -> dict[str, Any]:
    """Loan EMI, total payment and total interest (reducing balance)."""
    return _with_disclaimer(calculators.emi(principal, annual_rate_pct, years))


@mcp.tool()
def calculate_fd(
    principal: float,
    annual_rate_pct: float,
    years: float,
    compounding_per_year: int = 4,
) -> dict[str, Any]:
    """Fixed deposit maturity amount and effective yield (quarterly compounding by default)."""
    return _with_disclaimer(
        calculators.fd_maturity(principal, annual_rate_pct, years, compounding_per_year)
    )


@mcp.tool()
def calculate_rd(monthly_deposit: float, annual_rate_pct: float, months: int) -> dict[str, Any]:
    """Recurring deposit maturity amount (quarterly compounding)."""
    return _with_disclaimer(calculators.rd_maturity(monthly_deposit, annual_rate_pct, months))


@mcp.tool()
def calculate_lumpsum_value(
    principal: float, expected_return_pct: float, years: float
) -> dict[str, Any]:
    """Future value of a one-time investment at a constant assumed annual return."""
    return _with_disclaimer(
        calculators.lumpsum_future_value(principal, expected_return_pct, years)
    )


@mcp.tool()
def project_sip(
    monthly_amount: float,
    expected_return_pct: float,
    years: float,
    annual_step_up_pct: float = 0.0,
) -> dict[str, Any]:
    """Project a SIP at an assumed constant return, with an optional yearly step-up.

    This is a what-if projection. For a SIP on a real fund's history, use
    calculate_sip_returns.
    """
    return _with_disclaimer(
        calculators.sip_future_value(
            monthly_amount, expected_return_pct, years, annual_step_up_pct
        )
    )


@mcp.tool()
def calculate_swp(
    corpus: float,
    monthly_withdrawal: float,
    expected_return_pct: float,
    years: float,
) -> dict[str, Any]:
    """Systematic withdrawal plan: does the corpus last, and how much remains?"""
    return _with_disclaimer(
        calculators.swp_projection(corpus, monthly_withdrawal, expected_return_pct, years)
    )


@mcp.tool()
def plan_retirement(
    current_monthly_expense: float,
    current_age: int,
    retirement_age: int,
    life_expectancy: int,
    inflation_pct: float = 6.0,
    post_retirement_return_pct: float = 8.0,
    pre_retirement_return_pct: float = 12.0,
    existing_savings: float = 0.0,
) -> dict[str, Any]:
    """Corpus needed at retirement and the monthly SIP required to build it."""
    return _with_disclaimer(
        calculators.retirement_corpus(
            current_monthly_expense,
            current_age,
            retirement_age,
            life_expectancy,
            inflation_pct,
            post_retirement_return_pct,
            pre_retirement_return_pct,
            existing_savings,
        )
    )


@mcp.tool()
def estimate_mf_tax(
    purchase_amount: float,
    sale_amount: float,
    holding_days: int,
    fund_type: str = "equity",
    slab_rate_pct: float = 30.0,
    ltcg_exemption_available: float = calculators.EQUITY_LTCG_EXEMPTION,
) -> dict[str, Any]:
    """Estimate capital gains tax on a mutual fund redemption (FY 2026-27 rules).

    fund_type 'equity': STCG 20% (up to 12 months) or LTCG 12.5% above the
    exemption. 'debt'/'other': taxed at `slab_rate_pct`. Excludes surcharge and
    loss set-off. Confirm with a tax professional.
    """
    return _with_disclaimer(
        calculators.mf_capital_gains(
            purchase_amount,
            sale_amount,
            holding_days,
            fund_type,
            slab_rate_pct,
            ltcg_exemption_available,
        )
    )


def main() -> None:
    """Run the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
