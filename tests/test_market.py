import pytest

from bahi_mcp import market


def test_normalize_symbol_adds_exchange_suffix():
    assert market.normalize_symbol("reliance") == "RELIANCE.NS"
    assert market.normalize_symbol(" tcs ", "bse") == "TCS.BO"


def test_normalize_symbol_passes_through_indexes_and_suffixed():
    assert market.normalize_symbol("^NSEI") == "^NSEI"
    assert market.normalize_symbol("infy.ns") == "INFY.NS"


def test_normalize_symbol_validation():
    with pytest.raises(ValueError):
        market.normalize_symbol("")
    with pytest.raises(ValueError):
        market.normalize_symbol("tcs", "NYSE")


def test_resolve_index_names():
    assert market.resolve_index("Nifty 50") == "^NSEI"
    assert market.resolve_index("SENSEX") == "^BSESN"
    assert market.resolve_index("bank-nifty") == "^NSEBANK"
    with pytest.raises(ValueError):
        market.resolve_index("dow jones")
