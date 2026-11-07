import pandas as pd
import pytest

from portfolio_optimizer.data import account_series
from portfolio_optimizer.portfolio_io import (
    TEMPLATE,
    account_instrument,
    export_portfolio,
    parse_portfolio,
    to_excel_bytes,
    to_number,
)


def test_to_number():
    assert to_number("1.234,56 €") == pytest.approx(1234.56)
    assert to_number("1,234.56") == pytest.approx(1234.56)
    assert to_number("2,25") == pytest.approx(2.25)
    assert to_number("12%") == 12.0
    assert to_number("12.000") == 12000
    assert to_number("1.234.567") == 1234567
    assert to_number("12,000") == 12000
    assert to_number("12.5") == 12.5
    assert pd.isna(to_number(""))


def test_parse_template():
    df = parse_portfolio(TEMPLATE.encode(), "cartera.csv")
    assert list(df["identifier"][:3]) == ["IE00B4L5Y983", "LU0996182563", "ES0119199000"]
    acc = df.iloc[3]
    assert acc["kind"] == "Account" and acc["rate"] == pytest.approx(0.0225) and acc["value"] == 6000


def test_parse_weights_and_english_headers():
    csv = "Ticker,Weight\nEUNL.DE,60%\nVGEA.DE,40%\n"
    df = parse_portfolio(csv.encode(), "w.csv", total_if_weights=1000)
    assert list(df["value"]) == pytest.approx([600, 400])


def test_excel_roundtrip(tmp_path):
    inst = {"EUNL.DE": account_instrument("x", 0.02)}
    exp = export_portfolio({"EUNL.DE": (1000.0, 900.0)}, inst)
    data = to_excel_bytes({"Cartera": exp})
    back = parse_portfolio(data, "c.xlsx")
    assert back["value"].iloc[0] == 1000 and back["rate"].iloc[0] == pytest.approx(0.02)


def test_account_series_hits_todays_rate_and_never_negative():
    idx = pd.bdate_range("2019-01-01", periods=1500)
    # a rate index that earns -0.5% a year for 700 days, then 3%
    daily = [(-0.005 if i < 700 else 0.03) / 252 for i in range(1500)]
    estr = pd.Series(100 * pd.Series(daily).add(1).cumprod().values, index=idx)
    acc = account_series(estr, 0.025)
    r = acc.pct_change().dropna()
    assert (r >= -1e-15).all()
    assert r.iloc[-1] * 252 == pytest.approx(0.025, abs=1e-3)


def test_parse_example_file():
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "examples" / "cartera_ejemplo.csv"
    df = parse_portfolio(path.read_bytes(), path.name)
    assert df["value"].sum() == pytest.approx(29_500)
    assert df.iloc[-1]["kind"] == "Account" and df.iloc[-1]["rate"] == pytest.approx(0.0225)
