from portfolio_optimizer.classify import guess_instrument, guess_kind
from portfolio_optimizer.search import instrument_from_dict, instrument_to_dict


def test_guess_kind():
    assert guess_kind("iShares Core MSCI World UCITS ETF", "ETF") == "ETF"
    assert guess_kind("iShares Physical Gold ETC", "ETF") == "ETC"
    assert guess_kind("Vanguard Global Stock Index Fund", "MUTUALFUND") == "Index fund"
    assert guess_kind("Cobas Internacional FI", "MUTUALFUND") == "Active fund"
    assert guess_kind("Myinvestor Indexado Global PP", "MUTUALFUND") == "Pension plan"
    assert guess_kind("Apple Inc.", "EQUITY") == "Stock"


def test_guess_classes_and_regions():
    mm = guess_instrument("X", "Amundi Euro Liquidity-Rated Responsible P", "MUTUALFUND")
    assert mm.asset_class == "Money market" and mm.proxy == "XEON.DE"
    bond = guess_instrument("X", "Fidelity Euro Short Term Bond A-Acc-EUR", "MUTUALFUND")
    assert bond.asset_class == "Fixed income" and bond.category == "Short-term" and bond.management == "Active"
    us = guess_instrument("X", "Myinvestor S&P500 Equiponderado FI", "MUTUALFUND")
    assert us.asset_class == "Equity" and us.region == "US" and us.kind == "Index fund"
    em = guess_instrument("X", "Amundi Index MSCI Emerging Markets AE-C", "MUTUALFUND")
    assert em.region == "Emerging" and em.proxy == "IS3N.DE"
    mixed = guess_instrument("X", "Myinvestor Cartera Permanente FI", "MUTUALFUND")
    assert mixed.asset_class == "Mixed" and abs(sum(mixed.exposures.values()) - 1) < 1e-12
    gold = guess_instrument("X", "WisdomTree Physical Gold", "ETF")
    assert gold.asset_class == "Commodities" and gold.kind == "ETC"


def test_instrument_roundtrip():
    inst = guess_instrument("0P0001BODO.F", "Myinvestor Cartera Permanente FI", "MUTUALFUND")
    assert instrument_from_dict(instrument_to_dict(inst)) == inst
