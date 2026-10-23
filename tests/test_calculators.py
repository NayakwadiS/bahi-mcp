import pytest

from bahi_mcp import calculators as c


def test_emi_known_value():
    out = c.emi(1_000_000, 8.5, 20)
    assert out["monthly_emi"] == pytest.approx(8678, abs=2)
    assert out["months"] == 240
    assert out["total_interest"] == pytest.approx(out["total_payment"] - 1_000_000, abs=0.01)


def test_emi_zero_rate():
    assert c.emi(12000, 0, 1)["monthly_emi"] == 1000.0


def test_fd_quarterly_compounding():
    out = c.fd_maturity(100000, 8, 1)
    assert out["maturity_amount"] == pytest.approx(108243.22, abs=0.01)


def test_rd_is_between_simple_and_full_year_interest():
    out = c.rd_maturity(1000, 7, 12)
    assert out["total_invested"] == 12000.0
    assert 12000 < out["maturity_amount"] < 12000 + 12000 * 0.07


def test_sip_future_value_matches_annuity_due_formula():
    i = 1.12 ** (1 / 12) - 1
    n = 120
    expected = 1000 * (((1 + i) ** n - 1) / i) * (1 + i)
    out = c.sip_future_value(1000, 12, 10)
    assert out["future_value"] == pytest.approx(expected, abs=0.05)
    assert out["total_invested"] == 120000.0


def test_sip_step_up_increases_invested_amount():
    out = c.sip_future_value(1000, 10, 2, annual_step_up_pct=10)
    assert out["total_invested"] == pytest.approx(12 * 1000 + 12 * 1100, abs=0.01)


def test_swp_exhausts_at_zero_return():
    out = c.swp_projection(1_000_000, 10_000, 0, 20)
    assert out["corpus_exhausted"] is True
    assert out["months_sustained"] == 100
    assert out["total_withdrawn"] == 1_000_000.0


def test_swp_lasts_when_return_covers_withdrawal():
    out = c.swp_projection(1_000_000, 5_000, 12, 5)
    assert out["corpus_exhausted"] is False
    assert out["remaining_corpus"] > 0


def test_retirement_corpus_basic_sanity():
    out = c.retirement_corpus(50000, 30, 60, 85)
    assert out["years_to_retirement"] == 30
    assert out["monthly_expense_at_retirement"] > 50000
    assert out["corpus_required"] > 0
    assert out["required_monthly_sip"] > 0
    # existing savings reduce the SIP required
    with_savings = c.retirement_corpus(50000, 30, 60, 85, existing_savings=2_000_000)
    assert with_savings["required_monthly_sip"] < out["required_monthly_sip"]


def test_retirement_rejects_bad_ages():
    with pytest.raises(ValueError):
        c.retirement_corpus(50000, 60, 55, 85)


def test_capital_gains_equity_long_term_uses_exemption():
    out = c.mf_capital_gains(500000, 700000, 400)
    assert out["category"] == "LTCG"
    assert out["taxable_gain"] == 75000.0
    assert out["tax_before_cess"] == 9375.0
    assert out["total_tax"] == 9750.0


def test_capital_gains_equity_short_term():
    out = c.mf_capital_gains(500000, 600000, 100)
    assert out["category"] == "STCG"
    assert out["total_tax"] == 20800.0


def test_capital_gains_boundary_is_short_term_at_365_days():
    assert c.mf_capital_gains(500000, 600000, 365)["category"] == "STCG"
    assert c.mf_capital_gains(500000, 600000, 366)["category"] == "LTCG"


def test_capital_gains_loss_and_debt_slab():
    assert c.mf_capital_gains(500000, 400000, 100)["total_tax"] == 0.0
    debt = c.mf_capital_gains(500000, 600000, 500, fund_type="debt", slab_rate_pct=30)
    assert debt["category"] == "slab"
    assert debt["total_tax"] == 31200.0


def test_capital_gains_validates_fund_type():
    with pytest.raises(ValueError):
        c.mf_capital_gains(1000, 2000, 10, fund_type="gold")
