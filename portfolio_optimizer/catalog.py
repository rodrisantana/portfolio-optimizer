"""Curated catalogue of instruments a euro-based retail investor can actually buy.

Every Yahoo symbol and ISIN below was checked against Yahoo Finance when the
catalogue was written (November 2026). TER figures are indicative: confirm
them in the KID / factsheet, and edit them in the app if they have changed.

Each instrument is classified on four axes, used for the allocation breakdowns
and for the asset-class limits of the optimiser:

* ``asset_class``: Equity, Fixed income, Money market, Commodities, Crypto or
  Mixed (a mixed fund declares its split in ``exposure``)
* ``region``:      Global, US, Europe, Eurozone, Emerging, Japan, n/a
* ``management``:  Passive (tracks an index) or Active (a manager picks)
* ``kind``:        ETF, ETC, ETN, Index fund, Active fund, Pension plan, Account,
                   Deposit, Stock, Spot

Remunerated accounts and deposits carry a ``rate`` (the TAE you are offered).

Funds are resolved from their ISIN, because Yahoo stores them under opaque
Morningstar ids such as ``0P00000WLG.F``. Yahoo only has fund prices since
2018 (2022 for Amundi and Fundsmith), and some funds have no usable history at
all. Each fund therefore names a ``proxy``: an ETF, or a blend of ETFs written
``"EUNL.DE:0.4,EUNA.DE:0.6"``, that follows the same index or allocation. The
proxy backfills short histories and, when Yahoo has nothing, the fund is
simulated as proxy minus the extra fees.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

EQUITY, FIXED_INCOME, MONEY_MARKET, COMMODITIES, CRYPTO, MIXED = (
    "Equity", "Fixed income", "Money market", "Commodities", "Crypto", "Mixed")
ASSET_CLASSES = (EQUITY, FIXED_INCOME, MONEY_MARKET, COMMODITIES, CRYPTO)
REGIONS = ("Global", "US", "Europe", "Eurozone", "Emerging", "Japan", "n/a")
KINDS = ("ETF", "ETC", "ETN", "Index fund", "Active fund", "Pension plan", "Account", "Deposit", "Stock", "Spot",
         "Custom")
FUND_KINDS = ("Index fund", "Active fund")
CASH_KINDS = ("Account", "Deposit")
MANAGEMENT = ("Passive", "Active")


@dataclass(frozen=True)
class Instrument:
    symbol: str                  # Yahoo symbol, or the ISIN for funds
    name: str
    kind: str
    asset_class: str
    ter: float                   # annual total expense ratio, as a decimal
    isin: str = ""
    region: str = "Global"
    category: str = ""           # style detail: Broad, Small cap, Value, Govt, Gold...
    management: str = "Passive"
    proxy: str = ""              # ETF or ETF blend that follows the same index / allocation
    exposure: tuple[tuple[str, float], ...] = ()   # only for mixed funds
    rate: float | None = None    # interest rate (TAE) of an account or deposit
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
        return self.kind in FUND_KINDS

    @property
    def tax_free_switch(self) -> bool:
        """Moving money out triggers no capital-gains tax today.

        Funds (traspaso), pension plans (traspaso between plans) and cash
        accounts or deposits (their interest is taxed every year as it is paid).
        """
        return self.kind in FUND_KINDS + ("Pension plan",) + CASH_KINDS

    @property
    def exposures(self) -> dict[str, float]:
        """Look-through split by asset class (sums to one)."""
        if self.exposure:
            return dict(self.exposure)
        return {self.asset_class: 1.0}


def _etf(symbol, name, asset_class, ter, isin="", region="Global", category="Broad", **kw):
    return Instrument(symbol, name, "ETF", asset_class, ter, isin, region, category, **kw)


def _fund(symbol, name, asset_class, ter, region, category, proxy, short, management="Passive", isin=None, **kw):
    """A fund identified by its ISIN (default) or, when Yahoo only knows a share class, by its Yahoo symbol."""
    kind = "Active fund" if management == "Active" else "Index fund"
    return Instrument(symbol, name, kind, asset_class, ter, symbol if isin is None else isin, region, category,
                      management, proxy, short=short, **kw)


CATALOG: tuple[Instrument, ...] = (
    # ---------------- Equity ETFs (UCITS, EUR quotes) ----------------
    _etf("EUNL.DE", "iShares Core MSCI World", EQUITY, 0.0020, "IE00B4L5Y983"),
    _etf("VWCE.DE", "Vanguard FTSE All-World", EQUITY, 0.0019, "IE00BK5BQT80"),
    _etf("IUSQ.DE", "iShares MSCI ACWI", EQUITY, 0.0020, "IE00B6R52259"),
    _etf("SPYI.DE", "SPDR MSCI ACWI IMI", EQUITY, 0.0017, "IE00B3YLTY66"),
    _etf("XDWD.DE", "Xtrackers MSCI World 1C", EQUITY, 0.0019, "IE00BJ0KDQ92"),
    _etf("SXR8.DE", "iShares Core S&P 500", EQUITY, 0.0007, "IE00B5BMR087", "US"),
    _etf("SXRV.DE", "iShares Nasdaq 100", EQUITY, 0.0030, "IE00B53SZB19", "US", "Growth"),
    _etf("IMAE.AS", "iShares Core MSCI Europe", EQUITY, 0.0012, "IE00B4K48X80", "Europe"),
    _etf("SXR7.DE", "iShares Core MSCI EMU", EQUITY, 0.0012, "IE00B53QG562", "Eurozone"),
    _etf("SXRT.DE", "iShares Core EURO STOXX 50", EQUITY, 0.0010, "IE00B53L3W79", "Eurozone"),
    _etf("IS3N.DE", "iShares Core MSCI EM IMI", EQUITY, 0.0018, "IE00BKM4GZ66", "Emerging"),
    _etf("IUSN.DE", "iShares MSCI World Small Cap", EQUITY, 0.0035, "IE00BF4RFH31", category="Small cap"),
    _etf("ZPRV.DE", "SPDR MSCI USA Small Cap Value", EQUITY, 0.0030, "IE00BSPLC413", "US", "Small cap value"),
    _etf("ZPRX.DE", "SPDR MSCI Europe Small Cap Value", EQUITY, 0.0030, "IE00BSPLC298", "Europe", "Small cap value"),
    _etf("IS3Q.DE", "iShares MSCI World Quality", EQUITY, 0.0025, "IE00BP3QZ601", category="Quality"),
    _etf("IS3R.DE", "iShares MSCI World Momentum", EQUITY, 0.0025, "IE00BP3QZ825", category="Momentum"),
    # ---------------- Bond and money-market ETFs ----------------
    _etf("VGEA.DE", "Vanguard EUR Eurozone Govt Bond", FIXED_INCOME, 0.0007, "IE00BH04GL39", "Eurozone", "Govt"),
    _etf("SXRQ.DE", "iShares EUR Govt Bond 7-10yr", FIXED_INCOME, 0.0015, "IE00B3VTN290", "Eurozone", "Govt"),
    _etf("IBCI.DE", "iShares EUR Inflation Linked Govt Bond", FIXED_INCOME, 0.0009, "IE00B0M62X26", "Eurozone",
         "Inflation-linked"),
    _etf("EUNA.DE", "iShares Core Global Aggregate Bond (EUR hedged)", FIXED_INCOME, 0.0010, "IE00BDBRDM35",
         category="Aggregate"),
    _etf("VAGF.DE", "Vanguard Global Aggregate Bond (EUR hedged)", FIXED_INCOME, 0.0010, "IE00BG47KH54",
         category="Aggregate"),
    _etf("IBC5.DE", "iShares USD TIPS (EUR hedged)", FIXED_INCOME, 0.0012, "IE00BDZVH966", "US", "Inflation-linked"),
    _etf("XEON.DE", "Xtrackers EUR Overnight Rate Swap (ESTR)", MONEY_MARKET, 0.0010, "LU0290358497", "Eurozone",
         "Cash", note="Tracks the euro overnight rate: a good cash / risk-free proxy."),
    # ---------------- ETCs / ETNs / spot ----------------
    Instrument("4GLD.DE", "Xetra-Gold", "ETC", COMMODITIES, 0.0, "DE000A0S9GB0", "n/a", "Gold",
               note="No TER; custody fees may apply depending on the broker."),
    Instrument("SGLN.L", "iShares Physical Gold", "ETC", COMMODITIES, 0.0012, "IE00B4ND3602", "n/a", "Gold",
               note="Quoted in GBp (pence) on the LSE; converted automatically."),
    Instrument("PHAG.L", "WisdomTree Physical Silver", "ETC", COMMODITIES, 0.0049, "JE00B1VS3333", "n/a", "Silver"),
    Instrument("VBTC.DE", "VanEck Bitcoin ETN", "ETN", CRYPTO, 0.0100, "DE000A28M8D0", "n/a", "Bitcoin"),
    Instrument("BTC-EUR", "Bitcoin (spot, EUR)", "Spot", CRYPTO, 0.0, region="n/a", category="Bitcoin"),
    # ---------------- Passive index funds (resolved from the ISIN) ----------------
    _fund("IE00B03HD191", "Vanguard Global Stock Index Fund EUR Acc", EQUITY, 0.0018, "Global", "Broad",
          "EUNL.DE", "VG Global Stock"),
    _fund("IE00BYX5NX33", "Fidelity MSCI World Index Fund P-Acc-EUR", EQUITY, 0.0012, "Global", "Broad",
          "EUNL.DE", "Fidelity World"),
    _fund("IE00BD0NCM55", "iShares Developed World Index Fund D Acc EUR", EQUITY, 0.0010, "Global", "Broad",
          "EUNL.DE", "iShares Dev World"),
    _fund("IE0032126645", "Vanguard U.S. 500 Stock Index Fund EUR Acc", EQUITY, 0.0010, "US", "Broad",
          "SXR8.DE", "VG US 500"),
    _fund("IE0031786696", "Vanguard Emerging Markets Stock Index Fund EUR Acc", EQUITY, 0.0023, "Emerging", "Broad",
          "IS3N.DE", "VG Emerging"),
    _fund("IE00B42W4L06", "Vanguard Global Small-Cap Index Fund EUR Acc", EQUITY, 0.0029, "Global", "Small cap",
          "IUSN.DE", "VG Small Cap"),
    _fund("IE00B18GC888", "Vanguard Global Bond Index Fund EUR Hedged Acc", FIXED_INCOME, 0.0015, "Global",
          "Aggregate", "EUNA.DE", "VG Global Bond"),
    # Amundi Index Solutions share classes sold by Spanish banks and brokers (Openbank, MyInvestor...).
    _fund("LU0996182563", "Amundi Index MSCI World AE-C", EQUITY, 0.0030, "Global", "Broad", "EUNL.DE",
          "Amundi World", note="Common at Openbank. Yahoo history starts in 2022; earlier years use the proxy."),
    _fund("LU0996179007", "Amundi Index S&P 500 (Screened) AE-C", EQUITY, 0.0030, "US", "Broad", "SXR8.DE",
          "Amundi S&P 500"),
    _fund("LU0389811885", "Amundi Index MSCI Europe AE-C", EQUITY, 0.0030, "Europe", "Broad", "IMAE.AS",
          "Amundi Europe"),
    _fund("LU0996177134", "Amundi Index MSCI Emerging Markets AE-C", EQUITY, 0.0040, "Emerging", "Broad", "IS3N.DE",
          "Amundi EM"),
    _fund("LU0389812933", "Amundi Index Global Government Bond AHE-C", FIXED_INCOME, 0.0030, "Global", "Govt",
          "EUNA.DE", "Amundi Global Govt"),
    # ---------------- Actively managed funds ----------------
    _fund("ES0119199000", "Cobas Internacional FI (C)", EQUITY, 0.0180, "Global", "Value", "EUNL.DE",
          "Cobas Internacional", "Active"),
    _fund("ES0112611001", "Azvalor Internacional FI", EQUITY, 0.0180, "Global", "Value", "EUNL.DE",
          "Azvalor Internacional", "Active"),
    _fund("ES0159259011", "Magallanes European Equity FI (M)", EQUITY, 0.0185, "Europe", "Value", "IMAE.AS",
          "Magallanes European", "Active"),
    _fund("ES0114638036", "Bestinver Internacional FI", EQUITY, 0.0180, "Global", "Value", "EUNL.DE",
          "Bestinver Internacional", "Active"),
    _fund("ES0180792006", "True Value FI", EQUITY, 0.0160, "Global", "Small cap", "IUSN.DE", "True Value", "Active",
          note="Also charges a performance fee, not included in the TER."),
    _fund("LU0690375182", "Fundsmith Equity Fund T EUR Acc", EQUITY, 0.0105, "Global", "Quality", "IS3Q.DE",
          "Fundsmith", "Active"),
    _fund("IE00BF5H4C09", "Seilern World Growth EUR U I", EQUITY, 0.0100, "Global", "Growth", "IS3Q.DE",
          "Seilern World Growth", "Active"),
    _fund("LU0360483019", "Morgan Stanley Global Brands ZH EUR", EQUITY, 0.0090, "Global", "Quality", "IS3Q.DE",
          "MS Global Brands", "Active"),
    _fund("ES0110407097", "Baelo Patrimonio FI", MIXED, 0.0110, "Global", "Flexible",
          "EUNL.DE:0.75,EUNA.DE:0.25", "Baelo Patrimonio", "Active",
          exposure=((EQUITY, 0.75), (FIXED_INCOME, 0.25))),
    _fund("FR0010135103", "Carmignac Patrimoine A EUR Acc", MIXED, 0.0150, "Global", "Flexible",
          "EUNL.DE:0.4,EUNA.DE:0.6", "Carmignac Patrimoine", "Active",
          exposure=((EQUITY, 0.4), (FIXED_INCOME, 0.6)),
          note="No usable Yahoo history: simulated from a 40/60 blend minus fees."),
    _fund("LU0599946893", "DWS Concept Kaldemorgen LC", MIXED, 0.0155, "Global", "Flexible",
          "EUNL.DE:0.35,EUNA.DE:0.5,4GLD.DE:0.15", "DWS Kaldemorgen", "Active",
          exposure=((EQUITY, 0.35), (FIXED_INCOME, 0.5), (COMMODITIES, 0.15)),
          note="No usable Yahoo history: simulated from a blend minus fees."),
    _fund("IE0004766675", "Comgest Growth Europe EUR Acc", EQUITY, 0.0153, "Europe", "Quality", "IMAE.AS",
          "Comgest Europe", "Active", note="No usable Yahoo history: simulated from MSCI Europe minus fees."),
    _fund("LU1295551144", "Capital Group New Perspective (LUX) B EUR", EQUITY, 0.0160, "Global", "Growth", "IUSQ.DE",
          "CG New Perspective", "Active", note="No usable Yahoo history: simulated from MSCI ACWI minus fees."),
    _fund("LU0346389348", "Fidelity Global Technology A Acc EUR", EQUITY, 0.0189, "Global", "Technology", "SXRV.DE",
          "Fidelity Global Tech", "Active", note="No usable Yahoo history: simulated from the Nasdaq 100 minus fees."),
    # ---------------- Money market and short-term bond ETFs ----------------
    _etf("CSH2.PA", "Amundi Smart Overnight Return", MONEY_MARKET, 0.0010, "LU1190417599", "Eurozone", "Cash",
         proxy="XEON.DE"),
    _etf("ERNE.AS", "iShares EUR Ultrashort Bond", FIXED_INCOME, 0.0009, "IE00BCRY6557", "Eurozone", "Short-term",
         proxy="XEON.DE"),
    _etf("IEAC.AS", "iShares Core EUR Corp Bond", FIXED_INCOME, 0.0009, "IE00B3F81R35", "Eurozone", "Corporate"),
    _etf("VECA.DE", "Vanguard EUR Corporate Bond (Acc)", FIXED_INCOME, 0.0009, "IE00BGYWT403", "Eurozone",
         "Corporate", proxy="IEAC.AS"),
    # ---------------- Money market and bond funds (Yahoo symbol; share class verified) ----------------
    _fund("0P0000YFJY.F", "Amundi Euro Liquidity-Rated Responsible P", MONEY_MARKET, 0.0020, "Eurozone", "Cash",
          "XEON.DE", "Amundi Liquidity (MM)", isin=""),
    _fund("0P00000B50.F", "DWS Euro Ultra Short Fixed Income NC", FIXED_INCOME, 0.0035, "Eurozone", "Short-term",
          "ERNE.AS", "DWS Ultra Short", "Active", isin=""),
    _fund("0P00000N4I.F", "DWS Floating Rate Notes LC", FIXED_INCOME, 0.0030, "Eurozone", "Short-term", "ERNE.AS",
          "DWS Floating Rate", "Active", isin=""),
    _fund("0P0000AERX.F", "Fidelity Euro Short Term Bond A-Acc-EUR", FIXED_INCOME, 0.0070, "Eurozone", "Short-term",
          "ERNE.AS:0.5,IEAC.AS:0.5", "Fidelity Euro Short Bond", "Active", isin=""),
    _fund("0P00000M9H.F", "Evli Short Corporate Bond B", FIXED_INCOME, 0.0060, "Europe", "Corporate",
          "ERNE.AS:0.5,IEAC.AS:0.5", "Evli Short Corporate", "Active", isin=""),
    _fund("0P0000X9NY.F", "PIMCO GIS Income E EUR Hedged Acc", FIXED_INCOME, 0.0145, "Global", "Income", "EUNA.DE",
          "PIMCO Income", "Active", isin=""),
    # ---------------- MyInvestor funds and pension plans ----------------
    _fund("0P0001MRGY.F", "MyInvestor S&P500 Equiponderado FI", EQUITY, 0.0030, "US", "Equal weight", "SXR8.DE",
          "MyInvestor S&P500 EW", isin="", note="Equal-weight S&P 500; backfilled with the cap-weighted index."),
    _fund("0P0001MRGW.F", "MyInvestor Nasdaq 100 FI", EQUITY, 0.0030, "US", "Growth", "SXRV.DE",
          "MyInvestor Nasdaq 100", isin=""),
    _fund("0P0001NMUE.F", "MyInvestor Value B FI", EQUITY, 0.0105, "Global", "Value", "EUNL.DE", "MyInvestor Value",
          "Active", isin=""),
    _fund("0P0001BODO.F", "MyInvestor Cartera Permanente FI", MIXED, 0.0060, "Global", "Permanent portfolio",
          "EUNL.DE:0.25,SXRQ.DE:0.25,4GLD.DE:0.25,XEON.DE:0.25", "Cartera Permanente", "Active", isin="",
          exposure=((EQUITY, 0.25), (FIXED_INCOME, 0.25), (COMMODITIES, 0.25), (MONEY_MARKET, 0.25))),
    Instrument("0P0001LIG7.F", "MyInvestor Indexado Global PP", "Pension plan", EQUITY, 0.0030, "", "Global",
               "Broad", "Passive", "EUNL.DE", short="MyInvestor Global PP",
               note="Pension plan: contributions deduct from taxable income (up to 1,500 EUR a year) but the money "
                    "is locked until retirement."),
    # ---------------- US-listed ETFs (reference only) ----------------
    _etf("SPY", "SPDR S&P 500 ETF Trust", EQUITY, 0.000945, region="US", tags=("us",),
         note="US-domiciled: EU retail investors usually cannot buy it (no PRIIPs KID)."),
    _etf("QQQ", "Invesco QQQ Trust", EQUITY, 0.0020, region="US", category="Growth", tags=("us",)),
    _etf("VTI", "Vanguard Total Stock Market", EQUITY, 0.0003, region="US", tags=("us",)),
    _etf("TLT", "iShares 20+ Year Treasury Bond", FIXED_INCOME, 0.0015, region="US", category="Govt", tags=("us",)),
    _etf("BND", "Vanguard Total Bond Market", FIXED_INCOME, 0.0003, region="US", category="Aggregate", tags=("us",)),
    Instrument("GLD", "SPDR Gold Shares", "ETF", COMMODITIES, 0.0040, region="n/a", category="Gold", tags=("us",)),
)

# Readable chart and table labels: index or theme first, then the provider.
SHORT_NAMES = {'EUNL.DE': 'MSCI World · iShares',
    'VWCE.DE': 'FTSE All-World · Vanguard',
    'IUSQ.DE': 'MSCI ACWI · iShares',
    'SPYI.DE': 'ACWI IMI · SPDR',
    'XDWD.DE': 'MSCI World · Xtrackers',
    'SXR8.DE': 'S&P 500 · iShares',
    'SXRV.DE': 'Nasdaq 100 · iShares',
    'IMAE.AS': 'MSCI Europe · iShares',
    'SXR7.DE': 'MSCI EMU · iShares',
    'SXRT.DE': 'Euro Stoxx 50 · iShares',
    'IS3N.DE': 'EM IMI · iShares',
    'IUSN.DE': 'World Small Cap · iShares',
    'ZPRV.DE': 'USA Small Value · SPDR',
    'ZPRX.DE': 'Europe Small Value · SPDR',
    'IS3Q.DE': 'World Quality · iShares',
    'IS3R.DE': 'World Momentum · iShares',
    'VGEA.DE': 'Euro Govt Bond · Vanguard',
    'SXRQ.DE': 'Euro Govt 7-10y · iShares',
    'IBCI.DE': 'Euro Inflation Bond · iShares',
    'EUNA.DE': 'Global Agg Bond · iShares',
    'VAGF.DE': 'Global Agg Bond · Vanguard',
    'IBC5.DE': 'US TIPS (EUR-H) · iShares',
    'XEON.DE': '€STR Cash · Xtrackers',
    '4GLD.DE': 'Gold · Xetra-Gold',
    'SGLN.L': 'Gold · iShares',
    'PHAG.L': 'Silver · WisdomTree',
    'VBTC.DE': 'Bitcoin · VanEck',
    'BTC-EUR': 'Bitcoin (spot)',
    'CSH2.PA': 'Overnight Cash · Amundi',
    'ERNE.AS': 'Euro Ultrashort · iShares',
    'IEAC.AS': 'Euro Corp Bond · iShares',
    'VECA.DE': 'Euro Corp Bond · Vanguard',
    'SPY': 'S&P 500 · SPY (US)',
    'QQQ': 'Nasdaq 100 · QQQ (US)',
    'VTI': 'US Total Market · VTI (US)',
    'TLT': 'US Treasury 20y+ · TLT (US)',
    'BND': 'US Bonds · BND (US)',
    'GLD': 'Gold · GLD (US)',
    'IE00B03HD191': 'MSCI World · Vanguard fund',
    'IE00BYX5NX33': 'MSCI World · Fidelity fund',
    'IE00BD0NCM55': 'MSCI World · iShares fund',
    'IE0032126645': 'S&P 500 · Vanguard fund',
    'IE0031786696': 'Emerging · Vanguard fund',
    'IE00B42W4L06': 'Small Cap · Vanguard fund',
    'IE00B18GC888': 'Global Bond · Vanguard fund',
    'LU0996182563': 'MSCI World · Amundi fund',
    'LU0996179007': 'S&P 500 · Amundi fund',
    'LU0389811885': 'MSCI Europe · Amundi fund',
    'LU0996177134': 'Emerging · Amundi fund',
    'LU0389812933': 'Global Govt · Amundi fund'}
CATALOG = tuple(replace(i, short=SHORT_NAMES[i.symbol]) if i.symbol in SHORT_NAMES else i for i in CATALOG)

_BY_SYMBOL = {i.symbol: i for i in CATALOG}
_REGISTRY: dict[str, Instrument] = {}      # user-defined instruments added at runtime


def register(inst: Instrument) -> None:
    """Make a user-defined instrument (e.g. a fund typed in the app) known to describe()."""
    _REGISTRY[inst.symbol] = inst


_BY_ISIN = {i.isin: i for i in CATALOG if i.isin}


def get(symbol: str) -> Instrument | None:
    return _REGISTRY.get(symbol) or _BY_SYMBOL.get(symbol)


def find(identifier: str) -> Instrument | None:
    """Catalogue entry by symbol or by ISIN (an ETF is listed by ticker but often known by ISIN)."""
    code = identifier.strip()
    return get(code) or get(code.upper()) or _BY_ISIN.get(code.upper())


def describe(symbol: str) -> Instrument:
    """Catalogue entry, or a generic placeholder for a user-typed symbol."""
    found = get(symbol)
    if found is not None:
        return found
    if is_isin(symbol):
        return Instrument(symbol, symbol, "Index fund", EQUITY, 0.0, symbol)
    return Instrument(symbol, symbol, "Custom", EQUITY, 0.0)


def parse_proxy(spec: str) -> dict[str, float]:
    """``"A:0.4,B:0.6"`` -> {"A": 0.4, "B": 0.6}; a bare ticker gets weight 1."""
    out: dict[str, float] = {}
    for part in (p.strip() for p in spec.split(",") if p.strip()):
        sym, _, w = part.partition(":")
        out[sym.strip()] = float(w) if w else 1.0
    total = sum(out.values())
    if not out or total <= 0:
        raise ValueError(f"Invalid proxy {spec!r}")
    return {k: v / total for k, v in out.items()}


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
    "Openbank / Amundi index funds": ["LU0996182563", "LU0996179007", "LU0389811885", "LU0996177134", "LU0389812933"],
    "Active vs passive (Spanish value funds vs MSCI World)": ["EUNL.DE", "ES0119199000", "ES0112611001",
                                                             "ES0114638036", "LU0690375182"],
    "All-weather style": ["EUNL.DE", "SXRQ.DE", "IBCI.DE", "4GLD.DE", "XEON.DE"],
    "Conservative: money market and short-term bonds": ["0P0000YFJY.F", "ERNE.AS", "0P0000AERX.F", "IEAC.AS",
                                                        "EUNL.DE"],
    "MyInvestor funds": ["0P0001MRGY.F", "0P0001MRGW.F", "0P0001NMUE.F", "0P0001BODO.F", "IE00B18GC888"],
    "Equity tilts": ["EUNL.DE", "SXRV.DE", "IS3N.DE", "IUSN.DE", "ZPRV.DE", "IS3Q.DE"],
    "Growth + crypto": ["VWCE.DE", "SXRV.DE", "4GLD.DE", "BTC-EUR"],
}
