"""Allocation breakdown of a portfolio along the catalogue's classification axes."""

from __future__ import annotations

import pandas as pd

from .catalog import Instrument

DIMENSIONS = ("Asset class", "Region", "Management", "Vehicle")


def breakdown(weights: pd.Series, instruments: dict[str, Instrument], dimension: str) -> pd.Series:
    """Weight per category (sums to the invested weight).

    Asset class is look-through: a 40/60 mixed fund adds 40% of its weight to
    equity and 60% to fixed income. Region is reported for the equity sleeve of
    each instrument only, because 'region' means little for gold or cash.
    """
    out: dict[str, float] = {}
    for asset, w in weights.items():
        if w <= 0 or asset not in instruments:
            continue
        inst = instruments[asset]
        if dimension == "Asset class":
            for cls, share in inst.exposures.items():
                out[cls] = out.get(cls, 0.0) + w * share
        elif dimension == "Region":
            eq = inst.exposures.get("Equity", 0.0)
            if eq > 0:
                out[inst.region] = out.get(inst.region, 0.0) + w * eq
        elif dimension == "Management":
            out[inst.management] = out.get(inst.management, 0.0) + w
        elif dimension == "Vehicle":
            out[inst.kind] = out.get(inst.kind, 0.0) + w
        else:
            raise ValueError(f"Unknown dimension {dimension!r}")
    s = pd.Series(out, dtype=float).sort_values(ascending=False)
    if dimension == "Region" and s.sum() > 0:
        s = s / s.sum()                     # share of the equity sleeve
    return s


def breakdown_table(portfolios: dict[str, pd.Series], instruments: dict[str, Instrument],
                    dimension: str) -> pd.DataFrame:
    return pd.DataFrame({n: breakdown(w, instruments, dimension) for n, w in portfolios.items()}).fillna(0.0)
