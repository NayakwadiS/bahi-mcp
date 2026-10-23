"""Financial calculators for Indian investors (pure Python, no network).

All rates are annual percentages (8.5 means 8.5%). Results are estimates for
planning and are not investment or tax advice.
"""

from __future__ import annotations

from typing import Any

# Tax rules for listed equity / equity-oriented mutual funds, FY 2026-27.
# Verify against the latest Income Tax Act provisions before relying on them.
RULES_AS_OF = "FY 2026-27"
EQUITY_STCG_RATE_PCT = 20.0
EQUITY_LTCG_RATE_PCT = 12.5
EQUITY_LTCG_EXEMPTION = 125000.0
EQUITY_LONG_TERM_DAYS = 365  # held for MORE than 12 months
CESS_PCT = 4.0


def _positive(name: str, value: float) -> float:
    if value is None or float(value) <= 0:
        raise ValueError(f"{name} must be positive.")
    return float(value)


def _non_negative(name: str, value: float) -> float:
    if value is None or float(value) < 0:
        raise ValueError(f"{name} must not be negative.")
    return float(value)


def _r2(x: float) -> float:
    return round(x, 2)


def _monthly_rate(annual_pct: float) -> float:
    """Effective monthly rate equivalent to an annual return."""
    return (1.0 + annual_pct / 100.0) ** (1.0 / 12.0) - 1.0


def emi(principal: float, annual_rate_pct: float, years: float) -> dict[str, Any]:
    """Loan EMI (reducing balance)."""
    p = _positive("principal", principal)
    rate = _non_negative("annual_rate_pct", annual_rate_pct)
    n = int(round(_positive("years", years) * 12))
    if n < 1:
        raise ValueError("Loan tenure must be at least one month.")
    r = rate / 12.0 / 100.0
    if r == 0:
        e = p / n
    else:
        f = (1.0 + r) ** n
        e = p * r * f / (f - 1.0)
    total = e * n
    return {
        "monthly_emi": _r2(e),
        "months": n,
        "total_payment": _r2(total),
        "total_interest": _r2(total - p),
    }


def fd_maturity(
    principal: float,
    annual_rate_pct: float,
    years: float,
    compounding_per_year: int = 4,
) -> dict[str, Any]:
    """Fixed deposit maturity. Indian banks usually compound quarterly."""
    p = _positive("principal", principal)
    rate = _non_negative("annual_rate_pct", annual_rate_pct) / 100.0
    t = _positive("years", years)
    m = int(compounding_per_year)
    if m < 1:
        raise ValueError("compounding_per_year must be at least 1.")
    amount = p * (1.0 + rate / m) ** (m * t)
    return {
        "maturity_amount": _r2(amount),
        "interest_earned": _r2(amount - p),
        "effective_annual_yield_pct": _r2(((1.0 + rate / m) ** m - 1.0) * 100.0),
    }


def rd_maturity(
    monthly_deposit: float, annual_rate_pct: float, months: int
) -> dict[str, Any]:
    """Recurring deposit maturity, quarterly compounding, deposits at month start."""
    d = _positive("monthly_deposit", monthly_deposit)
    rate = _non_negative("annual_rate_pct", annual_rate_pct) / 100.0
    n = int(months)
    if n < 1:
        raise ValueError("months must be at least 1.")
    total = sum(d * (1.0 + rate / 4.0) ** (4.0 * (n - i) / 12.0) for i in range(n))
    invested = d * n
    return {
        "total_invested": _r2(invested),
        "maturity_amount": _r2(total),
        "interest_earned": _r2(total - invested),
    }


def lumpsum_future_value(
    principal: float, expected_return_pct: float, years: float
) -> dict[str, Any]:
    """Future value of a one-time investment at a constant assumed return."""
    p = _positive("principal", principal)
    r = _non_negative("expected_return_pct", expected_return_pct) / 100.0
    t = _positive("years", years)
    fv = p * (1.0 + r) ** t
    return {"future_value": _r2(fv), "gain": _r2(fv - p)}


def sip_future_value(
    monthly_amount: float,
    expected_return_pct: float,
    years: float,
    annual_step_up_pct: float = 0.0,
) -> dict[str, Any]:
    """Projected SIP value at a constant assumed return.

    Instalments are made at the start of each month. An optional annual step-up
    raises the instalment once every 12 months. Real returns will vary.
    """
    amount = _positive("monthly_amount", monthly_amount)
    _non_negative("expected_return_pct", expected_return_pct)
    months = int(round(_positive("years", years) * 12))
    step = _non_negative("annual_step_up_pct", annual_step_up_pct) / 100.0
    i = _monthly_rate(expected_return_pct)

    balance = 0.0
    invested = 0.0
    for m in range(months):
        if m > 0 and m % 12 == 0:
            amount *= 1.0 + step
        balance += amount
        invested += amount
        balance *= 1.0 + i
    return {
        "months": months,
        "total_invested": _r2(invested),
        "future_value": _r2(balance),
        "estimated_gain": _r2(balance - invested),
    }


def swp_projection(
    corpus: float,
    monthly_withdrawal: float,
    expected_return_pct: float,
    years: float,
) -> dict[str, Any]:
    """Systematic withdrawal plan: how long a corpus lasts at a given withdrawal."""
    balance = _positive("corpus", corpus)
    w = _positive("monthly_withdrawal", monthly_withdrawal)
    _non_negative("expected_return_pct", expected_return_pct)
    months = int(round(_positive("years", years) * 12))
    i = _monthly_rate(expected_return_pct)

    withdrawn = 0.0
    exhausted_in: int | None = None
    for m in range(months):
        take = min(w, balance)
        balance -= take
        withdrawn += take
        if balance <= 1e-9:
            exhausted_in = m + 1
            balance = 0.0
            break
        balance *= 1.0 + i
    return {
        "corpus_exhausted": exhausted_in is not None,
        "months_sustained": exhausted_in if exhausted_in is not None else months,
        "total_withdrawn": _r2(withdrawn),
        "remaining_corpus": _r2(balance),
    }


def retirement_corpus(
    current_monthly_expense: float,
    current_age: int,
    retirement_age: int,
    life_expectancy: int,
    inflation_pct: float = 6.0,
    post_retirement_return_pct: float = 8.0,
    pre_retirement_return_pct: float = 12.0,
    existing_savings: float = 0.0,
) -> dict[str, Any]:
    """Corpus needed at retirement and the monthly SIP required to reach it.

    Withdrawals are taken at the start of each year and rise with inflation.
    The SIP needed accounts for existing savings growing at the pre-retirement
    return. Assumptions are constant; treat the result as a planning estimate.
    """
    expense = _positive("current_monthly_expense", current_monthly_expense)
    if not (0 < current_age < retirement_age < life_expectancy):
        raise ValueError("Need current_age < retirement_age < life_expectancy.")
    inflation = _non_negative("inflation_pct", inflation_pct) / 100.0
    post = _non_negative("post_retirement_return_pct", post_retirement_return_pct) / 100.0
    pre = _non_negative("pre_retirement_return_pct", pre_retirement_return_pct)
    savings = _non_negative("existing_savings", existing_savings)

    years_to_retire = retirement_age - current_age
    retired_years = life_expectancy - retirement_age
    annual_at_retirement = expense * 12.0 * (1.0 + inflation) ** years_to_retire

    corpus = sum(
        annual_at_retirement * (1.0 + inflation) ** k / (1.0 + post) ** k
        for k in range(retired_years)
    )
    savings_future = savings * (1.0 + pre / 100.0) ** years_to_retire
    gap = max(0.0, corpus - savings_future)
    factor = sip_future_value(1.0, pre, years_to_retire)["future_value"]
    return {
        "years_to_retirement": years_to_retire,
        "years_in_retirement": retired_years,
        "monthly_expense_at_retirement": _r2(annual_at_retirement / 12.0),
        "corpus_required": _r2(corpus),
        "existing_savings_grown": _r2(savings_future),
        "corpus_gap": _r2(gap),
        "required_monthly_sip": _r2(gap / factor) if factor > 0 else None,
    }


def mf_capital_gains(
    purchase_amount: float,
    sale_amount: float,
    holding_days: int,
    fund_type: str = "equity",
    slab_rate_pct: float = 30.0,
    ltcg_exemption_available: float = EQUITY_LTCG_EXEMPTION,
    apply_cess: bool = True,
) -> dict[str, Any]:
    """Estimate tax on a mutual fund redemption.

    equity: STCG 20% (held up to 12 months) or LTCG 12.5% above the exemption.
    debt / other: taxed at your income-tax slab rate (units bought on/after
    1 Apr 2023). Surcharge, indexation for old units and set-off of losses are
    not modelled. Always confirm with a tax professional.
    """
    cost = _positive("purchase_amount", purchase_amount)
    proceeds = _non_negative("sale_amount", sale_amount)
    days = int(holding_days)
    if days < 0:
        raise ValueError("holding_days must not be negative.")
    kind = fund_type.strip().lower()
    if kind not in {"equity", "debt", "other"}:
        raise ValueError("fund_type must be 'equity', 'debt' or 'other'.")
    exemption = _non_negative("ltcg_exemption_available", ltcg_exemption_available)

    gain = proceeds - cost
    result: dict[str, Any] = {
        "gain": _r2(gain),
        "fund_type": kind,
        "rules_as_of": RULES_AS_OF,
    }
    if gain <= 0:
        result.update(
            category="loss",
            taxable_gain=0.0,
            tax_before_cess=0.0,
            cess=0.0,
            total_tax=0.0,
            net_proceeds=_r2(proceeds),
            note="Capital loss; it may be set off against other gains (not modelled).",
        )
        return result

    if kind == "equity":
        if days > EQUITY_LONG_TERM_DAYS:
            category, rate = "LTCG", EQUITY_LTCG_RATE_PCT
            taxable = max(0.0, gain - exemption)
        else:
            category, rate = "STCG", EQUITY_STCG_RATE_PCT
            taxable = gain
    else:
        category, rate = "slab", _non_negative("slab_rate_pct", slab_rate_pct)
        taxable = gain

    tax = taxable * rate / 100.0
    cess = tax * CESS_PCT / 100.0 if apply_cess else 0.0
    total = tax + cess
    result.update(
        category=category,
        tax_rate_pct=rate,
        taxable_gain=_r2(taxable),
        tax_before_cess=_r2(tax),
        cess=_r2(cess),
        total_tax=_r2(total),
        net_proceeds=_r2(proceeds - total),
    )
    return result
