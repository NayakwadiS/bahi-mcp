from datetime import date, timedelta

import pytest

from bahi_mcp import analytics


def test_parse_date_both_formats():
    assert analytics.parse_date("31-12-2023") == date(2023, 12, 31)
    assert analytics.parse_date("2023-12-31") == date(2023, 12, 31)
    with pytest.raises(ValueError):
        analytics.parse_date("31/12/2023")


def test_add_months_clamps_day():
    assert analytics.add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert analytics.add_months(date(2024, 1, 31), 2, day=31) == date(2024, 3, 31)
    assert analytics.add_months(date(2023, 11, 15), 3) == date(2024, 2, 15)


def test_xirr_lumpsum_matches_closed_form():
    flows = [(date(2021, 1, 1), -100000), (date(2024, 1, 1), 145000)]
    # 1095 days = exactly 3.0 years on a 365-day basis
    expected = 1.45 ** (1 / 3) - 1
    assert analytics.xirr(flows) == pytest.approx(expected, abs=1e-6)


def test_xirr_requires_both_signs():
    with pytest.raises(ValueError):
        analytics.xirr([(date(2021, 1, 1), -100), (date(2022, 1, 1), -50)])
    with pytest.raises(ValueError):
        analytics.xirr([(date(2021, 1, 1), -100)])


def test_cagr():
    rate = analytics.cagr(100, 200, date(2020, 1, 1), date(2025, 1, 1))
    assert 0.14 < rate < 0.15
    with pytest.raises(ValueError):
        analytics.cagr(100, 200, date(2025, 1, 1), date(2020, 1, 1))


def _daily_navs(start, days, fn):
    return [(start + timedelta(days=i), fn(i)) for i in range(days)]


def test_sip_constant_nav_gives_zero_return():
    navs = _daily_navs(date(2022, 1, 1), 800, lambda i: 10.0)
    out = analytics.sip_simulation(navs, 5000, date(2022, 1, 5), date(2023, 12, 5))
    assert out["installments"] == 24
    assert out["total_invested"] == 5000 * 24
    assert out["absolute_return_pct"] == pytest.approx(0.0, abs=0.01)
    assert out["xirr_pct"] == pytest.approx(0.0, abs=0.01)


def test_sip_rising_nav_gives_positive_return():
    navs = _daily_navs(date(2022, 1, 1), 800, lambda i: 10.0 + i * 0.01)
    out = analytics.sip_simulation(navs, 1000, date(2022, 1, 1), date(2023, 12, 1))
    assert out["absolute_return_pct"] > 0
    assert out["xirr_pct"] > 0


def test_sip_uses_next_available_nav_when_gap():
    # NAV missing on the 10th (holiday); instalment should use the 11th
    navs = [(date(2022, 1, d), 10.0) for d in range(1, 31) if d != 10]
    nav_hit = analytics.nav_on_or_after(navs, date(2022, 1, 10))
    assert nav_hit == (date(2022, 1, 11), 10.0)


def test_sip_validations():
    navs = _daily_navs(date(2022, 1, 1), 100, lambda i: 10.0)
    with pytest.raises(ValueError):
        analytics.sip_simulation(navs, 0, date(2022, 1, 1), date(2022, 3, 1))
    with pytest.raises(ValueError):
        analytics.sip_simulation(navs, 1000, date(2022, 3, 1), date(2022, 1, 1))
    with pytest.raises(ValueError):
        analytics.sip_simulation([], 1000, date(2022, 1, 1), date(2022, 3, 1))
