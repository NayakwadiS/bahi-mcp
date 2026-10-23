"""Pure-Python investor analytics (no network, no third-party dependencies).

Everything here is deterministic and unit-testable offline.
"""

from __future__ import annotations

import calendar
from bisect import bisect_left, bisect_right
from datetime import date, datetime
from typing import Sequence

NavSeries = Sequence[tuple[date, float]]  # sorted ascending by date

DAYS_IN_YEAR = 365.0


def parse_date(value: str | date) -> date:
    """Parse DD-MM-YYYY (AMFI style) or YYYY-MM-DD into a date."""
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date '{value}'. Use DD-MM-YYYY or YYYY-MM-DD.")


def add_months(d: date, months: int, day: int | None = None) -> date:
    """Add months to a date, clamping the day to the month length."""
    day = day if day is not None else d.day
    index = d.year * 12 + (d.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    day = min(day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def xirr(cashflows: Sequence[tuple[date, float]]) -> float:
    """Extended IRR for dated cash flows. Returns an annual rate (0.12 = 12%).

    Outflows (investments) must be negative and inflows (redemptions or the
    current value) positive. Raises ValueError when no solution exists.
    """
    flows = [(parse_date(d), float(a)) for d, a in cashflows]
    if len(flows) < 2:
        raise ValueError("XIRR needs at least two cash flows.")
    if not any(a > 0 for _, a in flows) or not any(a < 0 for _, a in flows):
        raise ValueError("XIRR needs at least one negative and one positive cash flow.")

    t0 = min(d for d, _ in flows)

    def npv(rate: float) -> float:
        return sum(a / (1.0 + rate) ** ((d - t0).days / DAYS_IN_YEAR) for d, a in flows)

    lo, hi = -0.9999, 100.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        raise ValueError("XIRR could not be solved for these cash flows.")

    for _ in range(300):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


def cagr(initial_value: float, final_value: float, start: date, end: date) -> float:
    """Compound annual growth rate between two dates (0.12 = 12%)."""
    start, end = parse_date(start), parse_date(end)
    if initial_value <= 0 or final_value <= 0:
        raise ValueError("initial_value and final_value must be positive.")
    days = (end - start).days
    if days <= 0:
        raise ValueError("end date must be after start date.")
    years = days / DAYS_IN_YEAR
    return (final_value / initial_value) ** (1.0 / years) - 1.0


def nav_on_or_after(navs: NavSeries, d: date) -> tuple[date, float] | None:
    """First available NAV on or after d (handles weekends and holidays)."""
    dates = [x[0] for x in navs]
    i = bisect_left(dates, d)
    return navs[i] if i < len(navs) else None


def nav_on_or_before(navs: NavSeries, d: date) -> tuple[date, float] | None:
    """Latest available NAV on or before d."""
    dates = [x[0] for x in navs]
    i = bisect_right(dates, d)
    return navs[i - 1] if i > 0 else None


def sip_simulation(
    navs: NavSeries,
    monthly_amount: float,
    start: date,
    end: date,
) -> dict:
    """Simulate a monthly SIP over a NAV history.

    Each instalment is invested on the SIP day-of-month (taken from `start`),
    at the first NAV available on or after that day. The final value uses the
    latest NAV on or before `end`.
    """
    start, end = parse_date(start), parse_date(end)
    if monthly_amount <= 0:
        raise ValueError("monthly_amount must be positive.")
    if end <= start:
        raise ValueError("end date must be after start date.")
    if not navs:
        raise ValueError("No NAV history available.")

    sip_day = start.day
    units = 0.0
    invested = 0.0
    cashflows: list[tuple[date, float]] = []
    installments = 0

    n = 0
    while True:
        due = add_months(start, n, sip_day)
        if due > end:
            break
        hit = nav_on_or_after(navs, due)
        if hit is None or hit[0] > end:
            break
        nav_date, nav = hit
        if nav <= 0:
            raise ValueError(f"Invalid NAV {nav} on {nav_date}.")
        units += monthly_amount / nav
        invested += monthly_amount
        cashflows.append((nav_date, -monthly_amount))
        installments += 1
        n += 1

    if installments == 0:
        raise ValueError("No NAV data in the requested period.")

    last = nav_on_or_before(navs, end)
    if last is None:
        raise ValueError("No NAV on or before the end date.")
    last_date, last_nav = last
    current_value = units * last_nav
    cashflows.append((last_date, current_value))

    result = {
        "installments": installments,
        "total_invested": round(invested, 2),
        "units_accumulated": round(units, 4),
        "valuation_date": last_date.isoformat(),
        "valuation_nav": round(last_nav, 4),
        "current_value": round(current_value, 2),
        "absolute_return_pct": round((current_value / invested - 1.0) * 100.0, 2),
    }
    try:
        result["xirr_pct"] = round(xirr(cashflows) * 100.0, 2)
    except ValueError:
        result["xirr_pct"] = None
    return result
