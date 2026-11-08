import pandas as pd
import pytest

from portfolio_optimizer.holdings import Holding, rebalance_plan, spanish_savings_tax, tracking_gap


def test_spanish_tax_brackets():
    assert spanish_savings_tax(-100) == 0
    assert spanish_savings_tax(6_000) == pytest.approx(1_140)
    assert spanish_savings_tax(10_000) == pytest.approx(1_140 + 4_000 * 0.21)
    assert spanish_savings_tax(400_000) == pytest.approx(
        6_000 * .19 + 44_000 * .21 + 150_000 * .23 + 100_000 * .27 + 100_000 * .30)


def test_cash_only_rebalance_never_sells():
    h = [Holding("EUNL.DE", 8000, 6000), Holding("VGEA.DE", 2000, 2100)]
    target = pd.Series({"EUNL.DE": 0.6, "VGEA.DE": 0.4})
    plan = rebalance_plan(h, target, new_cash=1000)
    assert (plan["Trade"] >= 0).all()
    assert plan["Trade"].sum() == pytest.approx(1000)
    assert plan.loc["VGEA.DE", "Trade"] == pytest.approx(1000)       # all cash to the underweight asset
    assert plan["Estimated tax"].sum() == 0


def test_full_rebalance_hits_target_and_taxes_etf_gains_only():
    h = [Holding("EUNL.DE", 8000, 4000), Holding("IE00B03HD191", 8000, 4000), Holding("VGEA.DE", 4000, 4000)]
    target = pd.Series({"EUNL.DE": 0.2, "IE00B03HD191": 0.2, "VGEA.DE": 0.6})
    plan = rebalance_plan(h, target, allow_sells=True)
    assert plan["Weight after"].values == pytest.approx(target.values)
    assert plan.loc["EUNL.DE", "Realised gain"] == pytest.approx(2000)
    assert plan.loc["EUNL.DE", "Estimated tax"] == pytest.approx(380)
    assert plan.loc["IE00B03HD191", "Estimated tax"] == 0               # traspaso between funds


def test_tracking_gap():
    assert tracking_gap(pd.Series({"A": 0.7, "B": 0.3}), pd.Series({"A": 0.5, "B": 0.5})) == pytest.approx(0.2)
