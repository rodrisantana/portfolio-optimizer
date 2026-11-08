from pathlib import Path

from portfolio_optimizer.report import load_config, run, write_report

CONFIG = Path(__file__).resolve().parent.parent / "config.toml"


def test_offline_end_to_end(tmp_path):
    cfg = load_config(CONFIG)
    cfg["universe"]["offline_demo"] = True
    cfg["universe"]["assets"] = ["EUNL.DE", "IS3N.DE", "SXRQ.DE", "4GLD.DE"]
    cfg["constraints"].pop("groups", None)
    cfg["montecarlo"]["simulations"] = 500
    res = run(cfg)
    assert set(res.portfolios) >= {"Maximum Sharpe", "Minimum variance", "Risk parity", "HRP"}
    assert res.backtest is not None and res.simulation is not None
    path = write_report(res, tmp_path)
    text = path.read_text()
    assert "Efficient frontier" in text and "Monte Carlo" in text
    assert (tmp_path / "results.md").exists()
