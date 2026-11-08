"""Import and export portfolios as CSV or Excel, whatever bank or broker they come from.

Import is forgiving: column names are matched in Spanish or English
("ISIN", "Ticker", "Nombre", "Valor", "Importe", "Coste", "Peso"...), numbers
may use Spanish separators (1.234,56) and a currency sign, and a row may
describe a remunerated account or deposit with its interest rate.
"""

from __future__ import annotations

import io
import re
import unicodedata

import pandas as pd

from .catalog import CASH_KINDS, Instrument, is_isin

COLUMN_ALIASES = {
    "identifier": ["isin", "ticker", "symbol", "simbolo", "codigo", "code", "identificador", "identifier", "yahoo"],
    "name": ["name", "nombre", "producto", "fondo", "activo", "descripcion", "description", "instrumento", "asset"],
    "value": ["value", "valor", "importe", "valoracion", "valor de mercado", "market value", "saldo", "posicion",
              "importe actual", "valor actual", "amount", "balance"],
    "cost": ["cost", "coste", "coste de adquisicion", "cost basis", "invertido", "aportado", "importe invertido",
             "precio de compra total", "purchase cost"],
    "weight": ["weight", "peso", "porcentaje", "%", "peso %", "weight %", "asignacion"],
    "type": ["type", "tipo", "vehiculo", "vehicle", "kind"],
    "rate": ["rate", "tae", "tin", "interes", "tipo de interes", "interest", "rentabilidad"],
}
ACCOUNT_WORDS = {"account": "Account", "cuenta": "Account", "cuenta remunerada": "Account", "deposit": "Deposit",
                 "deposito": "Deposit", "plazo fijo": "Deposit"}
TEMPLATE = (
    "ISIN o ticker;Nombre;Tipo;Valor;Coste;TAE %\n"
    "IE00B4L5Y983;iShares Core MSCI World;ETF;12000;9500;\n"
    "IE00B03HD191;Vanguard Global Stock Index Fund;Fondo indexado;5000;4200;\n"
    "ES0119199000;Cobas Internacional FI;Fondo activo;2000;1800;\n"
    ";Cuenta remunerada de ejemplo;Cuenta remunerada;6000;6000;2,25\n"
)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[()\[\]€$:]", " ", text)).strip()


def to_number(value) -> float:
    """'1.234,56 €' -> 1234.56; '1,234.56' -> 1234.56; '12%' -> 12.0; blanks -> nan."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value)
    s = re.sub(r"[^\d,.\-]", "", str(value))
    if not s or s in "-.,":
        return float("nan")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):        # 12.000 / 1.234.567: Spanish thousands
        return float(s.replace(".", ""))
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+", s):         # 12,000 / 1,234,567: English thousands
        return float(s.replace(",", ""))
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _match_columns(columns) -> dict[str, str]:
    out: dict[str, str] = {}
    normed = {c: _norm(c) for c in columns}
    for field, aliases in COLUMN_ALIASES.items():
        for col, n in normed.items():
            if col in out.values():
                continue
            if n in aliases or any(n.startswith(a + " ") or n.endswith(" " + a) for a in aliases if len(a) > 2):
                out[field] = col
                break
    return out


def read_table(content: bytes, filename: str = "") -> pd.DataFrame:
    """CSV (comma, semicolon or tab) or Excel into a raw DataFrame."""
    if filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        return pd.read_excel(io.BytesIO(content))
    text = content.decode("utf-8-sig", errors="replace")
    first = text.splitlines()[0] if text else ""
    sep = max([";", ",", "\t"], key=first.count)
    return pd.read_csv(io.StringIO(text), sep=sep, dtype=str)


def parse_portfolio(content: bytes, filename: str = "", total_if_weights: float = 10_000.0) -> pd.DataFrame:
    """Normalised positions: identifier, name, kind, value, cost, rate.

    If the file only has weights, values are weight x ``total_if_weights``.
    """
    raw = read_table(content, filename)
    cols = _match_columns(raw.columns)
    if "identifier" not in cols and "name" not in cols:
        raise ValueError("The file needs an ISIN / ticker column or a name column.")
    if "value" not in cols and "weight" not in cols:
        raise ValueError("The file needs a value (importe / valor) or a weight (peso) column.")
    rows = []
    for _, r in raw.iterrows():
        ident = str(r.get(cols.get("identifier"), "") or "").strip()
        ident = "" if ident.lower() == "nan" else ident
        name = str(r.get(cols.get("name"), "") or "").strip()
        name = "" if name.lower() == "nan" else name
        if not ident and not name:
            continue
        value = to_number(r.get(cols["value"])) if "value" in cols else float("nan")
        if pd.isna(value) and "weight" in cols:
            w = to_number(r.get(cols["weight"]))
            value = (w / 100 if w > 1.0 else w) * total_if_weights if pd.notna(w) else float("nan")
        cost = to_number(r.get(cols["cost"])) if "cost" in cols else float("nan")
        rate = to_number(r.get(cols["rate"])) if "rate" in cols else float("nan")
        kind_txt = _norm(r.get(cols.get("type"), "") or "") if "type" in cols else ""
        kind = next((v for k, v in ACCOUNT_WORDS.items() if k in kind_txt), "")
        rows.append({"identifier": ident, "name": name, "kind": kind,
                     "value": 0.0 if pd.isna(value) else value, "cost": 0.0 if pd.isna(cost) else cost,
                     "rate": None if pd.isna(rate) else (rate / 100 if rate > 0.5 else rate)})
    if not rows:
        raise ValueError("No positions found in the file.")
    return pd.DataFrame(rows)


def account_instrument(name: str, rate: float, kind: str = "Account") -> Instrument:
    """A remunerated account or deposit paying ``rate`` (TAE)."""
    kind = kind if kind in CASH_KINDS else "Account"
    return Instrument(name, name, kind, "Money market", 0.0, "", "Eurozone", "Cash", "Passive", "XEON.DE",
                      rate=float(rate), short=name[:28])


def export_portfolio(holdings: dict[str, tuple[float, float]], instruments: dict[str, Instrument]) -> pd.DataFrame:
    """Positions with their classification, ready to save as CSV / Excel and import again."""
    total = sum(v for v, _ in holdings.values()) or 1.0
    rows = []
    for label, (value, cost) in holdings.items():
        inst = instruments.get(label)
        if inst is None:
            continue
        rows.append({
            "ISIN o ticker": inst.isin if is_isin(inst.isin) else inst.symbol,
            "Nombre": inst.name, "Tipo": inst.kind, "Gestión": inst.management, "Clase": inst.asset_class,
            "Región": inst.region, "TER %": round(inst.ter * 100, 3),
            "TAE %": round(inst.rate * 100, 3) if inst.rate is not None else None,
            "Valor": round(value, 2), "Coste": round(cost, 2), "Peso %": round(100 * value / total, 2),
        })
    return pd.DataFrame(rows)


def to_excel_bytes(frames: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet, df in frames.items():
            df.to_excel(writer, sheet_name=sheet[:31], index=False)
    return buf.getvalue()
