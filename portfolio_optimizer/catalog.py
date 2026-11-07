"""Curated catalogue of instruments a euro-based retail investor can actually buy.

Every Yahoo symbol below was checked against Yahoo Finance when the catalogue
was written (November 2026). TER figures are indicative: always confirm them in
the KID / factsheet, and edit them in the app if they have changed.

Index funds (Vanguard, Fidelity, Amundi, iShares) are resolved from their ISIN,
because Yahoo stores them under opaque Morningstar ids such as ``0P00000WLG.F``.
Their Yahoo history only starts in 2018 (or 2022 for the Amundi share classes),
so each one names an ETF ``proxy`` that tracks the same index and can be used to
backfill the missing years.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ASSET_CLASSES = (
    "Global equity",
    "Regional equity",
    "Factor / small cap",
    "Bonds",
    "Money market",
    "Commodities",
    "Crypto",
)


@dataclass(frozen=True)
class Instrument:
    symbol: str                  # Yahoo symbol, or the ISIN for index funds
    name: str
    kind: str                    # "ETF", "ETC", "ETN", "Index fund", "Spot"
    asset_class: str
    ter: float                   # annual total expense ratio, as a decimal
    isin: str = ""
    proxy: str = ""              # ETF used to backfill history before inception
    note: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    short: str = ""              # compact chart label; defaults to the symbol

    @property
    def label(self) -> str:
        return f"{self.name} ({self.symbol})"

    @property
    def display(self) -> str:
        return self.short or self.symbol

    @property
    def is_fund(self) -> bool:
        """Spanish tax law lets you switch between funds tax-free (traspaso)."""
        return self.kind == "Index fund"


CATALOG: tuple[Instrument, ...] = (
    # ---------------- Global / regional equity ETFs (UCITS, EUR quotes) ----------------
    Instrument("EUNL.DE", "iShares Core MSCI World", "ETF", "Global equity", 0.0020, "IE00B4L5Y983"),
    Instrument("VWCE.DE", "Vanguard FTSE All-World", "ETF", "Global equity", 0.0019, "IE00BK5BQT80"),
    Instrument("IUSQ.DE", "iShares MSCI ACWI", "ETF", "Global equity", 0.0020, "IE00B6R52259"),
    Instrument("SPYI.DE", "SPDR MSCI ACWI IMI", "ETF", "Global equity", 0.0017, "IE00B3YLTY66"),
    Instrument("XDWD.DE", "Xtrackers MSCI World 1C", "ETF", "Global equity", 0.0019, "IE00BJ0KDQ92"),
    Instrument("SXR8.DE", "iShares Core S&P 500", "ETF", "Regional equity", 0.0007, "IE00B5BMR087"),
    Instrument("SXRV.DE", "iShares Nasdaq 100", "ETF", "Regional equity", 0.0030, "IE00B53SZB19"),
    Instrument("IMAE.AS", "iShares Core MSCI Europe", "ETF", "Regional equity", 0.0012, "IE00B4K48X80"),
    Instrument("SXR7.DE", "iShares Core MSCI EMU", "ETF", "Regional equity", 0.0012, "IE00B53QG562"),
    Instrument("SXRT.DE", "iShares Core EURO STOXX 50", "ETF", "Regional equity", 0.0010, "IE00B53L3W79"),
    Instrument("IS3N.DE", "iShares Core MSCI EM IMI", "ETF", "Regional equity", 0.0018, "IE00BKM4GZ66"),
    # ---------------- Factor and small-cap ETFs ----------------
    Instrument("IUSN.DE", "iShares MSCI World Small Cap", "ETF", "Factor / small cap", 0.0035, "IE00BF4RFH31"),
    Instrument("ZPRV.DE", "SPDR MSCI USA Small Cap Value", "ETF", "Factor / small cap", 0.0030, "IE00BSPLC413"),
    Instrument("ZPRX.DE", "SPDR MSCI Europe Small Cap Value", "ETF", "Factor / small cap", 0.0030, "IE00BSPLC298"),
    Instrument("IS3Q.DE", "iShares MSCI World Quality", "ETF", "Factor / small cap", 0.0025, "IE00BP3QZ601"),
    Instrument("IS3R.DE", "iShares MSCI World Momentum", "ETF", "Factor / small cap", 0.0025, "IE00BP3QZ825"),
    # ---------------- Bond and money-market ETFs ----------------
    Instrument("VGEA.DE", "Vanguard EUR Eurozone Govt Bond", "ETF", "Bonds", 0.0007, "IE00BH04GL39"),
    Instrument("SXRQ.DE", "iShares EUR Govt Bond 7-10yr", "ETF", "Bonds", 0.0015, "IE00B3VTN290"),
    Instrument("IBCI.DE", "iShares EUR Inflation Linked Govt Bond", "ETF", "Bonds", 0.0009, "IE00B0M62X26"),
    Instrument("EUNA.DE", "iShares Core Global Aggregate Bond (EUR hedged)", "ETF", "Bonds", 0.0010, "IE00BDBRDM35"),
    Instrument("VAGF.DE", "Vanguard Global Aggregate Bond (EUR hedged)", "ETF", "Bonds", 0.0010, "IE00BG47KH54"),
    Instrument("IBC5.DE", "iShares USD TIPS (EUR hedged)", "ETF", "Bonds", 0.0012, "IE00BDZVH966"),
    Instrument("XEON.DE", "Xtrackers EUR Overnight Rate Swap (ESTR)", "ETF", "Money market", 0.0010, "LU0290358497",
               note="Tracks the euro overnight rate: a good cash / risk-free proxy."),
    # ---------------- ETCs / ETNs ----------------
    Instrument("4GLD.DE", "Xetra-Gold", "ETC", "Commodities", 0.0, "DE000A0S9GB0",
               note="No TER; custody fees may apply depending on the broker."),
    Instrument("SGLN.L", "iShares Physical Gold", "ETC", "Commodities", 0.0012, "IE00B4ND3602",
               note="Quoted in GBp (pence) on the LSE; converted automatically."),
    Instrument("PHAG.L", "WisdomTree Physical Silver", "ETC", "Commodities", 0.0049, "JE00B1VS3333"),
    Instrument("VBTC.DE", "VanEck Bitcoin ETN", "ETN", "Crypto", 0.0100, "DE000A28M8D0"),
    Instrument("BTC-EUR", "Bitcoin (spot, EUR)", "Spot", "Crypto", 0.0),
    # ---------------- Index funds (resolved from the ISIN) ----------------
    Instrument("IE00B03HD191", "Vanguard Global Stock Index Fund EUR Acc", "Index fund", "Global equity", 0.0018,
               "IE00B03HD191", proxy="EUNL.DE", short="VG Global Stock (fund)"),
    Instrument("IE00BYX5NX33", "Fidelity MSCI World Index Fund P-Acc-EUR", "Index fund", "Global equity", 0.0012,
               "IE00BYX5NX33", proxy="EUNL.DE", short="Fidelity World (fund)"),
    Instrument("IE00BD0NCM55", "iShares Developed World Index Fund D Acc EUR", "Index fund", "Global equity", 0.0010,
               "IE00BD0NCM55", proxy="EUNL.DE", short="iShares Dev World (fund)"),
    Instrument("LU0996182563", "Amundi Index MSCI World AE-C", "Index fund", "Global equity", 0.0030,
               "LU0996182563", proxy="EUNL.DE", short="Amundi World (fund)"),
    Instrument("IE0032126645", "Vanguard U.S. 500 Stock Index Fund EUR Acc", "Index fund", "Regional equity", 0.0010,
               "IE0032126645", proxy="SXR8.DE", short="VG US 500 (fund)"),
    Instrument("IE0031786696", "Vanguard Emerging Markets Stock Index Fund EUR Acc", "Index fund", "Regional equity",
               0.0023, "IE0031786696", proxy="IS3N.DE", short="VG Emerging (fund)"),
    Instrument("LU0996177134", "Amundi Index MSCI Emerging Markets AE-C", "Index fund", "Regional equity", 0.0020,
               "LU0996177134", proxy="IS3N.DE", short="Amundi EM (fund)"),
    Instrument("IE00B42W4L06", "Vanguard Global Small-Cap Index Fund EUR Acc", "Index fund", "Factor / small cap",
               0.0029, "IE00B42W4L06", proxy="IUSN.DE", short="VG Small Cap (fund)"),
    Instrument("IE00B18GC888", "Vanguard Global Bond Index Fund EUR Hedged Acc", "Index fund", "Bonds", 0.0015,
               "IE00B18GC888", proxy="EUNA.DE", short="VG Global Bond (fund)"),
    # ---------------- US-listed ETFs (reference only) ----------------
    Instrument("SPY", "SPDR S&P 500 ETF Trust", "ETF", "Regional equity", 0.000945,
               note="US-domiciled: EU retail investors usually cannot buy it (no PRIIPs KID).", tags=("us",)),
    Instrument("QQQ", "Invesco QQQ Trust", "ETF", "Regional equity", 0.0020, tags=("us",)),
    Instrument("VTI", "Vanguard Total Stock Market", "ETF", "Regional equity", 0.0003, tags=("us",)),
    Instrument("TLT", "iShares 20+ Year Treasury Bond", "ETF", "Bonds", 0.0015, tags=("us",)),
    Instrument("BND", "Vanguard Total Bond Market", "ETF", "Bonds", 0.0003, tags=("us",)),
    Instrument("GLD", "SPDR Gold Shares", "ETF", "Commodities", 0.0040, tags=("us",)),
)

_BY_SYMBOL = {i.symbol: i for i in CATALOG}


def get(symbol: str) -> Instrument | None:
    return _BY_SYMBOL.get(symbol)


def describe(symbol: str) -> Instrument:
    """Catalogue entry, or a generic placeholder for a user-typed symbol."""
    found = get(symbol)
    if found is not None:
        return found
    kind = "Index fund" if is_isin(symbol) else "Custom"
    return Instrument(symbol, symbol, kind, "Other", 0.0)


def is_isin(code: str) -> bool:
    """ISO 6166 format check including the Luhn check digit."""
    code = code.strip().upper()
    if len(code) != 12 or not code[:2].isalpha() or not code[-1].isdigit() or not code.isalnum():
        return False
    digits = "".join(str(int(c, 36)) for c in code[:-1])
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10 == int(code[-1])


# Ready-made starting universes for the app and the CLI.
PRESETS: dict[str, list[str]] = {
    "Boglehead core (world + EM + bonds + gold)": ["EUNL.DE", "IS3N.DE", "VGEA.DE", "EUNA.DE", "4GLD.DE"],
    "Index funds (Spanish traspaso-friendly)": ["IE00B03HD191", "IE0031786696", "IE00B42W4L06", "IE00B18GC888"],
    "All-weather style": ["EUNL.DE", "SXRQ.DE", "IBCI.DE", "4GLD.DE", "XEON.DE"],
    "Equity tilts": ["EUNL.DE", "SXRV.DE", "IS3N.DE", "IUSN.DE", "ZPRV.DE", "IS3Q.DE"],
    "Growth + crypto": ["VWCE.DE", "SXRV.DE", "4GLD.DE", "BTC-EUR"],
}
