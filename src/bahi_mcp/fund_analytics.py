"""Fund-level analytics on a NAV series: trailing returns, risk, rolling returns.

Pure Python, no network. A NAV series is a list of (date, nav) sorted ascending.
"""

from __future__ import annotations

import math
import statistics
from bisect import bisect_right
from datetime import date, timedelta
from typing import Any

from .analytics import NavSeries, add_months, cagr, parse_date

TRADING_DAYS = 252
HISTORY_SLACK_DAYS = 7


def _on_or_before(dates: list[date], navs: NavSeries, d: date):
    i = bisect_right(dates, d)
    return navs[i - 1] if i > 0 else None


def trailing_return(navs: NavSeries, years: float, end: date | None = None) -> float | None:
    """Annualised (CAGR) return over the last `years` ending at `end`.

    Returns None when the fund does not have enough history.
    """
    if not navs:
        return None
    dates = [d for d, _ in navs]
    end_hit = _on_or_before(dates, navs, parse_date(end) if end else dates[-1])
    if end_hit is None:
        return None
    start_target = add_months(end_hit[0], -int(round(years * 12)))
    if (dates[0] - start_target).days > HISTORY_SLACK_DAYS:
        return None
    start_hit = _on_or_before(dates, navs, start_target) or navs[0]
    if start_hit[0] >= end_hit[0]:
        return None
    return cagr(start_hit[1], end_hit[1], start_hit[0], end_hit[0])


def daily_returns(navs: NavSeries) -> list[float]:
    return [navs[i][1] / navs[i - 1][1] - 1.0 for i in range(1, len(navs)) if navs[i - 1][1] > 0]


def annualised_volatility(navs: NavSeries) -> float | None:
    rets = daily_returns(navs)
    if len(rets) < 2:
        return None
    return statistics.stdev(rets) * math.sqrt(TRADING_DAYS)


def max_drawdown(navs: NavSeries) -> float | None:
    """Largest peak-to-trough fall as a negative fraction (-0.35 = -35%)."""
    if len(navs) < 2:
        return None
    peak = navs[0][1]
    worst = 0.0
    for _, nav in navs:
        peak = max(peak, nav)
        if peak > 0:
            worst = min(worst, nav / peak - 1.0)
    return worst


def last_years(navs: NavSeries, years: float) -> NavSeries:
    if not navs:
        return []
    start = add_months(navs[-1][0], -int(round(years * 12)))
    return [x for x in navs if x[0] >= start]


def risk_metrics(
    navs: NavSeries, years: float = 3.0, risk_free_rate: float = 0.065
) -> dict[str, Any]:
    """Volatility, max drawdown and Sharpe ratio over the last `years`."""
    window = last_years(navs, years)
    if len(window) < 3:
        raise ValueError("Not enough NAV history for risk metrics.")
    vol = annualised_volatility(window)
    dd = max_drawdown(window)
    ret = cagr(window[0][1], window[-1][1], window[0][0], window[-1][0])
    sharpe = (ret - risk_free_rate) / vol if vol and vol > 1e-12 else None
    return {
        "lookback_years": years,
        "window_start": window[0][0].isoformat(),
        "window_end": window[-1][0].isoformat(),
        "annualised_return_pct": round(ret * 100.0, 2),
        "volatility_pct": round(vol * 100.0, 2) if vol is not None else None,
        "max_drawdown_pct": round(dd * 100.0, 2) if dd is not None else None,
        "sharpe_ratio": round(sharpe, 2) if sharpe is not None else None,
        "risk_free_rate_pct": round(risk_free_rate * 100.0, 2),
    }


def rolling_returns(
    navs: NavSeries,
    window_years: float,
    step_days: int = 30,
    threshold_pct: float = 12.0,
) -> dict[str, Any]:
    """Distribution of annualised returns over rolling windows.

    A window starts every `step_days`. Shows how often the fund beat zero and
    `threshold_pct`, which is more informative than a single point-to-point return.
    """
    if not navs:
        raise ValueError("No NAV history available.")
    if window_years <= 0 or step_days < 1:
        raise ValueError("window_years and step_days must be positive.")
    dates = [d for d, _ in navs]
    months = int(round(window_years * 12))
    first, last = dates[0], dates[-1]

    returns: list[float] = []
    d = first
    while add_months(d, months) <= last:
        start_hit = _on_or_before(dates, navs, d)
        end_hit = _on_or_before(dates, navs, add_months(d, months))
        if start_hit and end_hit and end_hit[0] > start_hit[0]:
            returns.append(cagr(start_hit[1], end_hit[1], start_hit[0], end_hit[0]))
        d += timedelta(days=step_days)

    if not returns:
        raise ValueError("NAV history is shorter than the rolling window.")
    n = len(returns)
    pct = lambda x: round(x * 100.0, 2)  # noqa: E731
    return {
        "window_years": window_years,
        "windows_analysed": n,
        "min_pct": pct(min(returns)),
        "max_pct": pct(max(returns)),
        "mean_pct": pct(statistics.fmean(returns)),
        "median_pct": pct(statistics.median(returns)),
        "pct_of_windows_positive": round(sum(r > 0 for r in returns) / n * 100.0, 1),
        "threshold_pct": threshold_pct,
        "pct_of_windows_above_threshold": round(
            sum(r * 100.0 > threshold_pct for r in returns) / n * 100.0, 1
        ),
    }


def fund_summary(navs: NavSeries, risk_years: float = 3.0, risk_free_rate: float = 0.065) -> dict[str, Any]:
    """Trailing returns plus risk metrics for one fund."""
    out: dict[str, Any] = {
        "latest_nav": round(navs[-1][1], 4),
        "latest_nav_date": navs[-1][0].isoformat(),
        "history_start": navs[0][0].isoformat(),
    }
    for years in (1, 3, 5):
        r = trailing_return(navs, years)
        out[f"return_{years}y_pct"] = round(r * 100.0, 2) if r is not None else None
    try:
        out["risk"] = risk_metrics(navs, risk_years, risk_free_rate)
    except ValueError as exc:
        out["risk"] = {"error": str(exc)}
    return out
