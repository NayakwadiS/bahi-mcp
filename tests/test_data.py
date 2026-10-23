"""Tests for the data layer using a fake mftool client (no network needed)."""

import json
from datetime import date
from urllib.error import URLError

import pytest

from bahi_mcp import data


class Patch:
    """Temporarily replace data._client with a fake."""

    def __init__(self, fake):
        self.fake = fake

    def __enter__(self):
        self.original = data._client
        data._client = lambda: self.fake
        return self.fake

    def __exit__(self, *exc):
        data._client = self.original
        return False


class FakeWithSearch:
    def search_schemes(self, query, limit=20):
        rows = [{"code": "1", "name": "Alpha Fund"}, {"code": "2", "name": "Beta Fund"}, {"bad": 1}]
        return rows[:limit]


class FakeNoSearch:
    def get_scheme_codes(self):
        return {"10": "SBI Midcap Direct Growth", "11": "SBI Large Cap", "12": "HDFC Midcap"}


def test_search_uses_native_ranked_search_and_normalises():
    with Patch(FakeWithSearch()):
        out = data.search_schemes("fund", limit=5)
    assert out == [
        {"scheme_code": "1", "scheme_name": "Alpha Fund"},
        {"scheme_code": "2", "scheme_name": "Beta Fund"},
    ]


def test_search_respects_limit():
    with Patch(FakeWithSearch()):
        assert len(data.search_schemes("fund", limit=1)) == 1


def test_search_falls_back_to_word_match_without_native():
    with Patch(FakeNoSearch()):
        out = data.search_schemes("sbi midcap")
    assert out == [{"scheme_code": "10", "scheme_name": "SBI Midcap Direct Growth"}]
    with pytest.raises(ValueError):
        with Patch(FakeNoSearch()):
            data.search_schemes("   ")


class FakeNav:
    def __init__(self, payload):
        self.payload = payload
        self.kwargs = None

    def get_scheme_historical_nav(self, code, **kwargs):
        self.kwargs = kwargs
        return self.payload


ROWS = [
    {"date": "03-01-2024", "nav": "12.5"},
    {"date": "01-01-2024", "nav": "10.0"},
    {"date": "bad-date", "nav": "11"},
    {"date": "02-01-2024", "nav": "not-a-number"},
]


def test_nav_series_from_dict_sorts_and_skips_bad_rows():
    fake = FakeNav({"data": ROWS})
    with Patch(fake):
        out = data.get_nav_series("123")
    assert out == [(date(2024, 1, 1), 10.0), (date(2024, 1, 3), 12.5)]
    assert fake.kwargs == {"as_Dataframe": False, "as_json": False}


def test_nav_series_from_json_string():
    with Patch(FakeNav(json.dumps({"data": ROWS}))):
        assert len(data.get_nav_series("123")) == 2


class FakeFrame:
    def iterrows(self):
        yield "01-01-2024", {"nav": "10"}
        yield "02-01-2024", {"nav": "11"}


def test_nav_series_from_dataframe_like():
    with Patch(FakeNav(FakeFrame())):
        out = data.get_nav_series("123")
    assert out == [(date(2024, 1, 1), 10.0), (date(2024, 1, 2), 11.0)]


def test_nav_series_empty_raises():
    with Patch(FakeNav({"data": []})):
        with pytest.raises(ValueError):
            data.get_nav_series("123")


class FakeOffline:
    def get_scheme_quote(self, code):
        raise URLError("no internet")


def test_network_errors_become_clear_runtime_errors():
    with Patch(FakeOffline()):
        with pytest.raises(RuntimeError):
            data.get_scheme_quote("123")


class FakePortfolio:
    def __init__(self):
        self.received = None

    def calculate_portfolio_value(self, holdings):
        self.received = holdings
        return {"total_value": 1000.0, "total_schemes": len(holdings), "holdings": holdings}


def test_portfolio_value_cleans_input_and_passes_through():
    fake = FakePortfolio()
    with Patch(fake):
        out = data.portfolio_value([{"scheme_code": 119551, "units": "10.5"}])
    assert fake.received == [{"scheme_code": "119551", "units": 10.5}]
    assert out["total_schemes"] == 1


def test_portfolio_value_validation():
    with Patch(FakePortfolio()):
        with pytest.raises(ValueError):
            data.portfolio_value([])
        with pytest.raises(ValueError):
            data.portfolio_value([{"scheme_code": "1"}])
        with pytest.raises(ValueError):
            data.portfolio_value([{"scheme_code": "1", "units": 0}])


class FakeCache:
    cleared = False

    def clear_cache(self):
        self.cleared = True


def test_clear_cache_calls_mftool_and_reports():
    fake = FakeCache()
    with Patch(fake):
        assert data.clear_cache() == {"cleared": True}
    assert fake.cleared is True
    with Patch(object()):
        with pytest.raises(RuntimeError):
            data.clear_cache()
