import numpy as np
import pandas as pd
import pytest

from portfolio_optimizer.catalog import CATALOG, PRESETS, get, is_isin
from portfolio_optimizer.data import (
    align,
    backfill_with_proxy,
    normalise_minor_units,
    parse_uploaded_csv,
    remove_spikes,
    to_base_currency,
    to_returns,
)


def _series(values, start="2024-01-01", name="X"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), name=name, dtype=float)


def test_catalog_isins_are_valid_and_unique():
    symbols = [i.symbol for i in CATALOG]
    assert len(symbols) == len(set(symbols))
    for inst in CATALOG:
        if inst.isin:
            assert is_isin(inst.isin), inst
        if inst.proxy:
            assert get(inst.proxy) is not None, inst
        assert 0 <= inst.ter < 0.02
    for members in PRESETS.values():
        assert all(get(m) is not None for m in members)


def test_isin_checksum():
    assert is_isin("IE00B4L5Y983")
    assert not is_isin("IE00B4L5Y984")
    assert not is_isin("EUNL.DE")


def test_minor_units():
    s, ccy = normalise_minor_units(_series([5892.0]), "GBp")
    assert ccy == "GBP" and s.iloc[0] == pytest.approx(58.92)
    s, ccy = normalise_minor_units(_series([10.0]), "EUR")
    assert ccy == "EUR" and s.iloc[0] == 10.0


def test_fx_conversion_uses_quote_per_base():
    usd = _series([110.0, 121.0])
    eurusd = _series([1.10, 1.10])            # 1 EUR = 1.10 USD
    out = to_base_currency(usd, "USD", "EUR", eurusd)
    np.testing.assert_allclose(out.values, [100.0, 110.0])


def test_fx_conversion_forward_fills_missing_rates():
    usd = _series([110.0, 110.0, 110.0])
    fx = _series([1.10, np.nan, 1.00]).dropna()
    out = to_base_currency(usd, "USD", "EUR", fx)
    np.testing.assert_allclose(out.values, [100.0, 100.0, 110.0])


def test_remove_spikes_only_drops_reverting_prints():
    s = _series([100, 101, 1010, 102, 103, 140, 141])     # 1010 is a bad tick; 140 is a real jump
    clean, n = remove_spikes(s)
    assert n == 1
    assert clean.iloc[2] == 101 and clean.iloc[5] == 140


def test_align_trims_to_common_history_and_fills_holidays():
    a = _series(np.arange(1, 61), "2024-01-01", "A")
    b = _series(np.arange(1, 51), "2024-01-15", "B").drop(pd.Timestamp("2024-02-01"))
    df = align({"A": a, "B": b})
    assert df.index[0] == pd.Timestamp("2024-01-15")
    assert not df.isna().any().any()
    assert pd.Timestamp("2024-02-01") in df.index


def test_backfill_joins_without_a_jump():
    proxy = _series(np.linspace(50, 100, 100), name="P")
    target = proxy.iloc[60:] * 3.0
    filled = backfill_with_proxy(target.rename("T"), proxy)
    assert filled.index[0] == proxy.index[0]
    np.testing.assert_allclose(filled.pct_change().dropna().values, proxy.pct_change().dropna().values)


def test_returns_frequency(demo_prices):
    w = to_returns(demo_prices, "weekly")
    m = to_returns(demo_prices, "monthly")
    assert len(w) > len(m) > 90
    assert (w.index.dayofweek == 4).all()
    with pytest.raises(ValueError):
        to_returns(demo_prices, "hourly")


def test_parse_spanish_csv():
    text = "Fecha;Mi fondo\n31/01/2024;10,50\n29/02/2024;10,75\n28/03/2024;11,00\n"
    df = parse_uploaded_csv(text)
    assert list(df.columns) == ["Mi fondo"]
    assert df.index[1] == pd.Timestamp("2024-02-29")
    assert df.iloc[2, 0] == pytest.approx(11.0)


def test_parse_iso_csv():
    df = parse_uploaded_csv(b"Date,A,B\n2024-01-02,1.5,2\n2024-01-03,1.6,2.1\n")
    assert df.shape == (2, 2) and df.index[0] == pd.Timestamp("2024-01-02")
