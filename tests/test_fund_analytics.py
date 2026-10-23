from datetime import date, timedelta

import pytest

from bahi_mcp import fund_analytics as fa


def growth_series(annual=0.12, days=6 * 365 + 10, start=date(2018, 1, 1)):
    """NAV compounding at exactly `annual` per 365 days."""
    return [(start + timedelta(days=i), 10.0 * (1 + annual) ** (i / 365)) for i in range(days)]


def test_trailing_return_matches_constant_growth():
    navs = growth_series(0.12)
    for years in (1, 3, 5):
        assert fa.trailing_return(navs, years) == pytest.approx(0.12, abs=1e-6)


def test_trailing_return_none_when_history_too_short():
    navs = growth_series(0.12, days=400)
    assert fa.trailing_return(navs, 3) is None
    assert fa.trailing_return([], 1) is None


def test_max_drawdown_known_values():
    navs = [(date(2020, 1, d), v) for d, v in enumerate([10, 12, 6, 9], start=1)]
    assert fa.max_drawdown(navs) == pytest.approx(-0.5)
    rising = [(date(2020, 1, d), v) for d, v in enumerate([1, 2, 3], start=1)]
    assert fa.max_drawdown(rising) == 0.0


def test_volatility_zero_for_constant_growth_and_positive_for_noisy():
    assert fa.annualised_volatility(growth_series(0.12)) == pytest.approx(0.0, abs=1e-6)
    noisy = [(date(2020, 1, 1) + timedelta(days=i), 10 + (i % 5)) for i in range(100)]
    assert fa.annualised_volatility(noisy) > 0.1


def test_risk_metrics_shape_and_none_sharpe_when_no_volatility():
    out = fa.risk_metrics(growth_series(0.12), years=3)
    assert out["annualised_return_pct"] == pytest.approx(12.0, abs=0.1)
    assert out["max_drawdown_pct"] == pytest.approx(0.0, abs=0.01)
    assert out["sharpe_ratio"] is None
    with pytest.raises(ValueError):
        fa.risk_metrics(growth_series(days=2), years=3)


def test_rolling_returns_constant_growth():
    out = fa.rolling_returns(growth_series(0.12), window_years=3, step_days=30)
    assert out["windows_analysed"] > 10
    assert out["min_pct"] == pytest.approx(12.0, abs=0.01)
    assert out["max_pct"] == pytest.approx(12.0, abs=0.01)
    assert out["pct_of_windows_positive"] == 100.0
    # thresholds either side of 12% avoid float noise exactly at the boundary
    low = fa.rolling_returns(growth_series(0.12), window_years=3, threshold_pct=11.0)
    high = fa.rolling_returns(growth_series(0.12), window_years=3, threshold_pct=13.0)
    assert low["pct_of_windows_above_threshold"] == 100.0
    assert high["pct_of_windows_above_threshold"] == 0.0
    with pytest.raises(ValueError):
        fa.rolling_returns(growth_series(days=300), window_years=3)


def test_fund_summary_fields():
    out = fa.fund_summary(growth_series(0.10))
    assert out["return_1y_pct"] == pytest.approx(10.0, abs=0.01)
    assert out["return_5y_pct"] == pytest.approx(10.0, abs=0.01)
    assert "risk" in out
