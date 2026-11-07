"""Interface translations (English is the source language, Spanish the translation).

``t(text)`` returns the Spanish version when the language is ``"es"`` and the
text is known, and the text itself otherwise, so a missing entry degrades to
English instead of breaking the page. ``untranslate`` maps a Spanish label
chosen in a table back to the internal English value.
"""

from __future__ import annotations

_LANG = "en"

ES: dict[str, str] = {
    # ---- navigation and general
    "Overview": "Resumen", "Optimiser": "Optimizador", "My portfolio": "Mi cartera", "Savings plan": "Plan de ahorro",
    "Backtest": "Backtest", "Methodology": "Metodología",
    "Optimisation, backtests and savings plans for ETFs, ETCs, index funds and active funds.":
        "Optimización, backtests y planes de ahorro para ETFs, ETCs, fondos indexados y fondos de gestión activa.",
    "Load a saved session (.json)": "Cargar una sesión guardada (.json)",
    "Restores your universe, holdings and settings.": "Recupera tus activos, posiciones y ajustes.",
    "Data source": "Fuente de datos", "Yahoo Finance (live)": "Yahoo Finance (en directo)",
    "Offline demo dataset": "Datos de demostración (sin conexión)",
    "The demo dataset ships with the repo (8 UCITS products in EUR, 2018-2026) and works without internet.":
        "El dataset de demostración viene con el repositorio (8 productos UCITS en EUR, 2018-2026) y funciona sin internet.",
    "Assets": "Activos", "Asset": "Activo", "Start from a preset": "Partir de una plantilla",
    "ETFs, ETCs, index funds and active funds": "ETFs, ETCs, fondos indexados y fondos activos",
    "Other Yahoo tickers or ISINs (comma separated)": "Otros tickers de Yahoo o ISINs (separados por comas)",
    "Add a fund that is not on the list": "Añadir un fondo que no está en la lista",
    "For funds Yahoo does not cover well (for example an Amundi fund bought at Openbank). Give the ISIN if you have it "
    "and an ETF that follows the same index as proxy: real prices are used when they exist, otherwise the fund is "
    "simulated as the proxy minus the fee difference. A blend works too: EUNL.DE:0.6,EUNA.DE:0.4":
        "Para fondos que Yahoo no cubre bien (por ejemplo un fondo de Amundi contratado en Openbank). Pon el ISIN si lo "
        "tienes y, como proxy, un ETF que siga el mismo índice: si hay precios reales se usan y, si no, el fondo se "
        "simula como el proxy menos la diferencia de comisiones. También vale una mezcla: EUNL.DE:0.6,EUNA.DE:0.4",
    "Name": "Nombre", "ISIN or ticker": "ISIN o ticker", "Proxy": "Proxy", "Class": "Clase", "Region": "Región",
    "Management": "Gestión", "Type": "Tipo", "Data": "Datos", "Quote ccy": "Divisa de cotización",
    "Your own NAV history (CSV)": "Tu propio histórico de valores liquidativos (CSV)",
    "First column = date, then one column per fund, prices in the base currency. Semicolons and decimal commas are fine.":
        "Primera columna = fecha y después una columna por fondo, con precios en la divisa base. Se admiten punto y "
        "coma y decimales con coma.",
    "Base currency": "Divisa base",
    "Every price is converted to this currency with daily FX rates, so returns include the currency risk you actually bear.":
        "Cada precio se convierte a esta divisa con el tipo de cambio diario, así las rentabilidades incluyen el riesgo "
        "de divisa que soportas de verdad.",
    "Period and data quality": "Periodo y calidad de datos", "Start": "Inicio", "End": "Fin",
    "Backfill short fund histories with an ETF on the same index":
        "Alargar históricos cortos de fondos con un ETF del mismo índice",
    "Remove one-day bad prints": "Eliminar precios erróneos de un día",
    "Estimation": "Estimación", "Return frequency": "Frecuencia de rentabilidades",
    "Weekly avoids the bias from exchanges closing at different times.":
        "La semanal evita el sesgo de que cada bolsa cierre a una hora distinta.",
    "Expected returns": "Rentabilidades esperadas",
    "Long-term forecasts use forward-looking assumptions per asset class instead of extrapolating the past. Edit them "
    "in the Optimiser tab.":
        "Las previsiones a largo plazo usan hipótesis por clase de activo en lugar de extrapolar el pasado. Puedes "
        "editarlas en la pestaña Optimizador.",
    "Expected alpha of active funds (annual %)": "Alfa esperado de los fondos activos (% anual)",
    "Extra return you expect from active managers before fees. The evidence (SPIVA) suggests about zero: most active "
    "funds trail their index by their fee difference.":
        "Rentabilidad extra que esperas de los gestores activos antes de comisiones. La evidencia (SPIVA) apunta a "
        "cero: la mayoría de fondos activos quedan por detrás de su índice más o menos en lo que cobran de más.",
    "Covariance": "Covarianza", "Risk-free rate (annual %)": "Tipo libre de riesgo (% anual)",
    "Average short-term rate: about 1-2% for EUR since 2015, 2% today.":
        "Tipo a corto plazo medio: entre el 1 % y el 2 % en euros desde 2015, en torno al 2 % hoy.",
    "Constraints": "Restricciones", "Max weight per asset": "Peso máximo por activo",
    "Min weight per asset": "Peso mínimo por activo",
    "Caps stop the optimiser from betting everything on one asset.":
        "Los límites evitan que el optimizador lo apueste todo a un solo activo.",
    "Limits by asset class (look-through for mixed funds) and on active funds. They apply to Max Sharpe, Min variance "
    "and Max diversification.":
        "Límites por clase de activo (los fondos mixtos cuentan según su composición) y sobre fondos activos. Se "
        "aplican a Máximo Sharpe, Mínima varianza y Máxima diversificación.",
    "Group": "Grupo", "Active funds": "Fondos activos",
    "Pick at least two assets in the sidebar to begin.": "Elige al menos dos activos en la barra lateral para empezar.",
    "Downloading prices and converting currencies...": "Descargando precios y convirtiendo divisas...",
    "Could not load prices: {err}": "No se pudieron cargar los precios: {err}",
    "Tip: switch to the offline demo dataset, or check the ticker on finance.yahoo.com.":
        "Consejo: cambia a los datos de demostración o comprueba el ticker en finance.yahoo.com.",
    "Need at least two assets with a common history of 60+ days in the chosen period.":
        "Hacen falta al menos dos activos con más de 60 días de histórico común en el periodo elegido.",
    "Simulated from {p}": "Simulado con {p}", "Real + backfilled with {p}": "Real + alargado con {p}", "Real": "Real",
    "Period": "Periodo", "Years of data": "Años de datos", "Return observations": "Observaciones",
    "Instruments": "Instrumentos",
    "Type, management, class, region and TER are editable: they drive the forecasts, the breakdowns and the limits. "
    "TERs are indicative; check the KID.":
        "Tipo, gestión, clase, región y TER son editables: de ellos dependen las previsiones, los desgloses y los "
        "límites. Los TER son orientativos; compruébalos en el documento de datos fundamentales.",
    # ---- estimation / optimiser
    "Long-term assumptions by asset class (editable)": "Hipótesis a largo plazo por clase de activo (editables)",
    "Nominal annual returns in EUR for the next 10-20 years, before fees. Defaults are round numbers in the middle of "
    "the ranges published by large asset managers in 2025-2026. Each asset gets the figure of its class and region, "
    "minus its TER (plus alpha for active funds). Volatilities and correlations still come from the data.":
        "Rentabilidades anuales nominales en euros para los próximos 10 a 20 años, antes de comisiones. Los valores "
        "por defecto son cifras redondas en mitad de los rangos que publicaron las grandes gestoras en 2025-2026. Cada "
        "activo recibe la cifra de su clase y región menos su TER (más el alfa si es un fondo activo). Volatilidades y "
        "correlaciones siguen saliendo de los datos.",
    "Assumption": "Hipótesis",
    "Fine-tune the expected return of each asset": "Ajustar la rentabilidad esperada de cada activo",
    "Compare the forecast with the past and type your own figure in the last column.":
        "Compara la previsión con el pasado y escribe tu propia cifra en la última columna.",
    "Forecast %": "Previsión %", "Historical %": "Histórica %", "Std. error %": "Error estándar %", "Use %": "Usar %",
    "Max weight raised to {w}: with {n} assets a lower cap cannot add up to 100%.":
        "Peso máximo subido al {w}: con {n} activos un límite menor no puede sumar el 100 %.",
    "Constraints are infeasible: {err}": "Las restricciones son imposibles de cumplir: {err}",
    "Expected returns: long-term forecasts net of TER.": "Rentabilidades esperadas: previsiones a largo plazo netas de TER.",
    "Bayes-Stein pulled the means {p} of the way towards the common mean.":
        "Bayes-Stein ha acercado las medias un {p} hacia la media común.",
    "Ledoit-Wolf shrinkage intensity: {p}.": "Intensidad del shrinkage de Ledoit-Wolf: {p}.",
    "Build your own point on the frontier": "Elige tu punto en la frontera",
    "Target volatility": "Volatilidad objetivo", "Expected return": "Rentabilidad esperada",
    "Show random portfolios": "Mostrar carteras aleatorias", "Strategy comparison": "Comparativa de estrategias",
    "Expected return and volatility are forward-looking estimates. The Backtest tab shows how each strategy really "
    "behaved, out of sample.":
        "Rentabilidad y volatilidad esperadas son estimaciones de futuro. La pestaña Backtest muestra cómo se comportó "
        "de verdad cada estrategia fuera de muestra.",
    "Weights and breakdown": "Pesos y desglose", "Portfolios": "Carteras", "Portfolio": "Cartera",
    "Download weights (CSV)": "Descargar pesos (CSV)", "Where does the risk come from?": "¿De dónde viene el riesgo?",
    "Risk contribution = share of portfolio variance coming from each asset. In a typical 60/40 portfolio equities "
    "bring around 90% of the risk.":
        "Contribución al riesgo = parte de la varianza de la cartera que aporta cada activo. En una cartera 60/40 "
        "típica la renta variable aporta alrededor del 90 % del riesgo.",
    "Volatility": "Volatilidad", "TER": "TER", "Effective N": "N efectivo",
    "Diversification ratio": "Ratio de diversificación", "Largest weight": "Mayor peso",
    "Honours constraints": "Cumple restricciones", "yes": "sí", "no": "no", "equity sleeve": "parte de renta variable",
    # ---- strategies
    "Maximum Sharpe": "Máximo Sharpe", "Minimum variance": "Mínima varianza",
    "Maximum diversification": "Máxima diversificación", "Risk parity": "Paridad de riesgo", "HRP": "HRP",
    "Inverse volatility": "Volatilidad inversa", "Equal weight": "Pesos iguales",
    # ---- classifications
    "Equity": "Renta variable", "Fixed income": "Renta fija", "Money market": "Monetario",
    "Commodities": "Materias primas", "Crypto": "Cripto", "Mixed": "Mixto",
    "Global": "Global", "US": "EE. UU.", "Europe": "Europa", "Eurozone": "Eurozona", "Emerging": "Emergentes",
    "Japan": "Japón", "n/a": "n/a", "Passive": "Pasiva", "Active": "Activa",
    "ETF": "ETF", "ETC": "ETC", "ETN": "ETN", "Index fund": "Fondo indexado", "Active fund": "Fondo activo",
    "Stock": "Acción", "Spot": "Contado", "Custom": "Personalizado",
    "Asset class": "Clase de activo", "Vehicle": "Vehículo",
    # ---- presets
    "(custom)": "(personalizada)",
    "Boglehead core (world + EM + bonds + gold)": "Cartera Boglehead (mundo + emergentes + bonos + oro)",
    "Index funds (Spanish traspaso-friendly)": "Fondos indexados (traspasables en España)",
    "Openbank / Amundi index funds": "Fondos indexados de Amundi (Openbank)",
    "Active vs passive (Spanish value funds vs MSCI World)": "Activa frente a pasiva (value español frente a MSCI World)",
    "All-weather style": "Estilo all-weather", "Equity tilts": "Sesgos de renta variable",
    "Growth + crypto": "Crecimiento + cripto",
    # ---- methods
    "Long-term forecasts (recommended)": "Previsiones a largo plazo (recomendado)",
    "Bayes-Stein shrinkage of history": "Histórico con shrinkage Bayes-Stein",
    "Historical mean": "Media histórica", "Exponentially weighted mean": "Media ponderada exponencial",
    "Ledoit-Wolf shrinkage (recommended)": "Shrinkage de Ledoit-Wolf (recomendado)",
    "Sample covariance": "Covarianza muestral", "Exponentially weighted (RiskMetrics)": "Ponderada exponencial (RiskMetrics)",
    "daily": "diaria", "weekly": "semanal", "monthly": "mensual",
    "Monthly": "Mensual", "Quarterly": "Trimestral", "Semi-annual": "Semestral", "Annual": "Anual",
    "Log-normal": "Log-normal", "Student-t (fat tails)": "t de Student (colas gruesas)",
    "Historical block bootstrap": "Bootstrap de bloques históricos",
    # ---- CMA keys
    "Equity · Global": "Renta variable · Global", "Equity · US": "Renta variable · EE. UU.",
    "Equity · Europe": "Renta variable · Europa", "Equity · Eurozone": "Renta variable · Eurozona",
    "Equity · Emerging": "Renta variable · Emergentes", "Equity · Japan": "Renta variable · Japón",
    "Equity · small cap / value premium": "Renta variable · prima small cap / value",
    "Fixed income · Government": "Renta fija · Deuda pública", "Fixed income · Aggregate": "Renta fija · Agregada",
    "Fixed income · Inflation-linked": "Renta fija · Ligada a la inflación",
    "Commodities · Gold": "Materias primas · Oro", "Commodities · Other": "Materias primas · Otras",
    # ---- overview
    "Historical performance (daily data, in {c})": "Rentabilidad histórica (datos diarios, en {c})",
    "Simulated funds show their proxy's history minus fees, not the fund's own record.":
        "Los fondos simulados muestran el histórico de su proxy menos comisiones, no el del propio fondo.",
    "Log scale": "Escala logarítmica", "Growth of 100": "Evolución de 100", "Correlation": "Correlación",
    "Calendar-year returns": "Rentabilidad por año natural", "Notes on the instruments": "Notas sobre los instrumentos",
    "CAGR": "Rentab. anualizada (CAGR)", "Sortino": "Sortino", "Max drawdown": "Caída máxima", "Calmar": "Calmar",
    "VaR 95%": "VaR 95 %", "CVaR 95%": "CVaR 95 %", "Best period": "Mejor periodo", "Worst period": "Peor periodo",
    "Positive periods": "Periodos positivos", "Longest drawdown (days)": "Caída más larga (días)", "Beta": "Beta",
    "Tracking error": "Tracking error", "Information ratio": "Ratio de información",
    "Avg turnover / rebalance": "Rotación media por rebalanceo",
    # ---- notes from the catalogue
    "Tracks the euro overnight rate: a good cash / risk-free proxy.":
        "Sigue el tipo a un día del euro: buena referencia de liquidez y de activo sin riesgo.",
    "No TER; custody fees may apply depending on the broker.": "Sin TER; puede haber comisión de custodia según el bróker.",
    "Quoted in GBp (pence) on the LSE; converted automatically.":
        "Cotiza en GBp (peniques) en Londres; se convierte automáticamente.",
    "Common at Openbank. Yahoo history starts in 2022; earlier years use the proxy.":
        "Habitual en Openbank. El histórico de Yahoo empieza en 2022; los años anteriores usan el proxy.",
    "Also charges a performance fee, not included in the TER.": "Cobra además comisión de éxito, no incluida en el TER.",
    "No usable Yahoo history: simulated from a 40/60 blend minus fees.":
        "Sin histórico útil en Yahoo: se simula con una mezcla 40/60 menos comisiones.",
    "No usable Yahoo history: simulated from a blend minus fees.":
        "Sin histórico útil en Yahoo: se simula con una mezcla de ETFs menos comisiones.",
    "No usable Yahoo history: simulated from MSCI Europe minus fees.":
        "Sin histórico útil en Yahoo: se simula con el MSCI Europe menos comisiones.",
    "No usable Yahoo history: simulated from MSCI ACWI minus fees.":
        "Sin histórico útil en Yahoo: se simula con el MSCI ACWI menos comisiones.",
    "No usable Yahoo history: simulated from the Nasdaq 100 minus fees.":
        "Sin histórico útil en Yahoo: se simula con el Nasdaq 100 menos comisiones.",
    "US-domiciled: EU retail investors usually cannot buy it (no PRIIPs KID).":
        "Domiciliado en EE. UU.: el inversor minorista europeo normalmente no puede comprarlo (sin KID PRIIPs).",
    # ---- my portfolio
    "Your current positions": "Tus posiciones actuales",
    "Enter the market value of each position (and what you paid, for the tax estimate). Leave zeros for assets you do "
    "not own. Funds that are not in the list can be added from the sidebar.":
        "Introduce el valor de mercado de cada posición (y lo que pagaste, para estimar impuestos). Deja a cero lo que "
        "no tengas. Los fondos que no estén en la lista se pueden añadir desde la barra lateral.",
    "Market value ({c})": "Valor de mercado ({c})", "Cost basis ({c})": "Coste de adquisición ({c})",
    "Enter your positions above to compare them with the optimised portfolios and plan a rebalance.":
        "Introduce tus posiciones arriba para compararlas con las carteras optimizadas y planificar un rebalanceo.",
    "Portfolio value": "Valor de la cartera", "Unrealised gain": "Plusvalía latente",
    "Annual cost (TER)": "Coste anual (TER)",
    "With the same volatility ({v}), the efficient portfolio would expect **{r}** a year, {g} more than yours (about "
    "{m} a year on your current balance).":
        "Con la misma volatilidad ({v}), la cartera eficiente esperaría un **{r}** anual, {g} más que la tuya (unos {m} "
        "al año sobre tu saldo actual).",
    "Your portfolio is already on (or very close to) the efficient frontier.":
        "Tu cartera ya está sobre la frontera eficiente o muy cerca de ella.",
    "Rebalancing plan": "Plan de rebalanceo", "Target portfolio": "Cartera objetivo",
    "New money to invest ({c})": "Dinero nuevo a invertir ({c})",
    "Allow selling (full rebalance)": "Permitir ventas (rebalanceo completo)",
    "Off: only the new money is used, nothing is sold and no tax is triggered.":
        "Desactivado: solo se usa el dinero nuevo, no se vende nada y no hay impuestos.",
    "Current value": "Valor actual", "Current weight": "Peso actual", "Target weight": "Peso objetivo",
    "Trade": "Operación", "Value after": "Valor después", "Weight after": "Peso después",
    "Realised gain": "Plusvalía realizada", "Estimated tax": "Impuesto estimado", "Traspaso eligible": "Traspasable",
    "Distance to target before": "Distancia al objetivo antes", "Distance to target after": "Distancia al objetivo después",
    "Estimated Spanish tax (IRPF)": "IRPF estimado",
    "Tax: savings-base brackets 19% to 30% on realised gains, average-cost method, no loss offsetting. Fund sales are "
    "assumed to go by traspaso (tax-deferred). Order of magnitude only, not tax advice.":
        "Impuestos: tramos de la base del ahorro del 19 % al 30 % sobre las plusvalías realizadas, con coste medio y "
        "sin compensar pérdidas. Las ventas de fondos se suponen por traspaso (sin tributar). Es una aproximación, no "
        "asesoramiento fiscal.",
    "Your allocation vs the target": "Tu distribución frente al objetivo", "Save this session": "Guardar esta sesión",
    "Downloads your universe, settings, own funds and holdings so you can load them next time.":
        "Descarga tus activos, ajustes, fondos propios y posiciones para cargarlos la próxima vez.",
    "Download session (.json)": "Descargar sesión (.json)",
    # ---- savings plan
    "Project a portfolio with monthly contributions. The expected path uses the long-term return; the Monte Carlo "
    "shows the range of outcomes around it.":
        "Proyecta una cartera con aportaciones mensuales. La senda esperada usa la rentabilidad a largo plazo y el "
        "Monte Carlo muestra el abanico de resultados a su alrededor.",
    "Initial capital ({c})": "Capital inicial ({c})", "Monthly contribution ({c})": "Aportación mensual ({c})",
    "Negative = monthly withdrawal (retirement phase).": "En negativo = retirada mensual (fase de jubilación).",
    "Horizon (years)": "Horizonte (años)",
    "Expected return (annual %, net of TER)": "Rentabilidad esperada (% anual, neta de TER)",
    "Volatility (annual %)": "Volatilidad (% anual)", "Other annual costs (%)": "Otros costes anuales (%)",
    "Platform or custody fees. Fund TERs are already inside the expected return.":
        "Comisiones de plataforma o custodia. El TER de los fondos ya está descontado de la rentabilidad esperada.",
    "Inflation (annual %)": "Inflación (% anual)",
    "Heads-up: {r} a year is above the long-run nominal return of global equities (roughly 6-8%).":
        "Ojo: un {r} anual está por encima de la rentabilidad nominal a largo plazo de la renta variable global "
        "(entre el 6 % y el 8 % aproximadamente).",
    "Contribution growth (annual %)": "Crecimiento de la aportación (% anual)",
    "Goal in today's money ({c}, 0 = none)": "Objetivo en euros de hoy ({c}, 0 = ninguno)",
    "Return model": "Modelo de rentabilidad", "Simulations": "Simulaciones",
    "Show in today's money (inflation-adjusted)": "Mostrar en dinero de hoy (descontando inflación)",
    "Expected path": "Senda esperada", "Value at the end": "Valor final", "Money contributed": "Dinero aportado",
    "Investment gains": "Rendimientos generados", "Value in today's money": "Valor final en dinero de hoy",
    "What the final amount would buy today, after {i} inflation a year.":
        "Lo que podrías comprar hoy con el importe final, descontando una inflación del {i} anual.",
    "over contributions": "sobre lo aportado",
    "Contributed": "Aportado", "Value": "Valor", "Gains": "Rendimientos",
    "Value (today's money)": "Valor (dinero de hoy)", "Year": "Año",
    "Median outcome": "Resultado mediano", "Bad case (P5)": "Caso malo (P5)", "Good case (P95)": "Caso bueno (P95)",
    "Median worst drawdown": "Peor caída mediana", "Chance of reaching the goal": "Probabilidad de llegar al objetivo",
    "Chance of running out": "Probabilidad de quedarse sin dinero",
    "Chance of ending below contributions": "Probabilidad de acabar por debajo de lo aportado",
    "How much should I contribute each month to reach the goal?":
        "¿Cuánto debería aportar cada mes para llegar al objetivo?",
    "Solving...": "Calculando...", "Probability of success": "Probabilidad de éxito",
    # ---- backtest
    "Walk-forward: at every rebalance date each strategy is re-optimised using only the past lookback years, then held "
    "until the next date. Prices are already net of each fund's TER; trading costs are deducted on every rebalance.":
        "Walk-forward: en cada rebalanceo la estrategia se vuelve a optimizar usando solo los años anteriores de la "
        "ventana y se mantiene hasta la siguiente fecha. Los precios ya son netos del TER de cada fondo y los costes "
        "de compraventa se descuentan en cada rebalanceo.",
    "Lookback (years)": "Ventana de estimación (años)", "Rebalance": "Rebalanceo",
    "Trading cost (bps)": "Coste de compraventa (pb)", "Benchmark": "Índice de referencia", "Strategies": "Estrategias",
    "Long-term forecasts are not available point-in-time, so the walk-forward uses Bayes-Stein estimates from each past "
    "window.":
        "Las previsiones a largo plazo no existían en cada fecha pasada, así que el walk-forward usa estimaciones "
        "Bayes-Stein de cada ventana.",
    "Not enough history for this lookback. Shorten it or pick assets with longer histories.":
        "No hay histórico suficiente para esta ventana. Acórtala o elige activos con más historia.",
    "Running walk-forward backtests...": "Ejecutando los backtests walk-forward...",
    "buy and hold": "comprar y mantener", "Growth of 100, out-of-sample": "Evolución de 100, fuera de muestra",
    "Investing every month over this period": "Invirtiendo cada mes durante este periodo",
    "Final value": "Valor final", "Money-weighted return (IRR)": "Rentabilidad ponderada por dinero (TIR)",
    "The money-weighted return (IRR / TIR) accounts for when each contribution was made, so it is the return you would "
    "actually have earned.":
        "La TIR tiene en cuenta cuándo se hizo cada aportación, así que es la rentabilidad que habrías obtenido de "
        "verdad.",
    "Weights over time": "Pesos a lo largo del tiempo",
    # ---- charts
    "Random portfolios": "Carteras aleatorias", "Efficient frontier": "Frontera eficiente",
    "Capital market line": "Línea del mercado de capitales", "Return": "Rentabilidad",
    "Annualised volatility": "Volatilidad anualizada", "Expected annual return": "Rentabilidad anual esperada",
    "Capital weight": "Peso en capital", "Risk contribution": "Contribución al riesgo", "5% to 95%": "Del 5 % al 95 %",
    "25% to 75%": "Del 25 % al 75 %", "Median": "Mediana", "Goal": "Objetivo",
}

_REVERSE = {v: k for k, v in ES.items()}


def set_language(lang: str) -> None:
    global _LANG
    _LANG = lang if lang in ("en", "es") else "en"


def get_language() -> str:
    return _LANG


def t(text: str) -> str:
    if _LANG == "es":
        return ES.get(text, text)
    return text


def untranslate(text: str) -> str:
    """Spanish label -> internal English value (identity for English or unknown labels)."""
    return _REVERSE.get(text, text)


METHODOLOGY = {
    "en": r"""
### What the app does

1. **Data.** Total-return prices from Yahoo Finance. ISINs are resolved to a listing that has history, LSE prices in
   pence are converted, and every series is converted to the base currency with daily FX. Funds with short histories
   are backfilled with an ETF on the same index; funds Yahoo does not cover are simulated as that ETF (or a blend of
   ETFs) minus the fee difference.
2. **Expected returns.** By default, long-term capital market assumptions per asset class and region, net of each
   fund's TER, with an optional alpha for active funds (zero by default, as the SPIVA evidence suggests). Historical,
   EWMA and Bayes-Stein estimates are available for comparison.
3. **Risk.** Weekly returns and Ledoit-Wolf shrinkage of the covariance towards constant correlation.
4. **Optimisation.** For weights $w$, expected returns $\mu$ and covariance $\Sigma$:
   $\mu_p = w^\top\mu$, $\sigma_p^2 = w^\top\Sigma w$, $S = (\mu_p - r_f)/\sigma_p$.
   Maximum Sharpe and maximum diversification are solved as convex problems through the change of variables
   $y = \kappa w$; risk parity through Spinu's convex programme; HRP by clustering and recursive bisection. Limits per
   asset, per asset class (look-through for mixed funds) and on active funds are supported.
5. **Savings plan.** Expected path with monthly contributions, and a Monte Carlo (log-normal, Student-t or block
   bootstrap) with inflation, fees and withdrawals.
6. **Backtest.** Walk-forward: every rebalance only sees past data. Monthly investing over the same period gives the
   money-weighted return (IRR).

Expected returns cannot be estimated precisely, so treat the optimiser as a tool to understand trade-offs.
This is not financial advice.
""",
    "es": r"""
### Qué hace la app

1. **Datos.** Precios con dividendos reinvertidos de Yahoo Finance. Los ISIN se resuelven a una cotización con
   histórico, los precios de Londres en peniques se convierten y cada serie pasa a la divisa base con el tipo de
   cambio diario. Los fondos con poco histórico se alargan con un ETF del mismo índice, y los que Yahoo no cubre se
   simulan como ese ETF (o una mezcla de ETFs) menos la diferencia de comisiones.
2. **Rentabilidad esperada.** Por defecto, hipótesis a largo plazo por clase de activo y región, netas del TER de
   cada fondo, con un alfa opcional para los fondos activos (cero por defecto, como sugieren los informes SPIVA).
   También están disponibles la media histórica, la EWMA y Bayes-Stein para comparar.
3. **Riesgo.** Rentabilidades semanales y covarianza con shrinkage de Ledoit-Wolf hacia correlación constante.
4. **Optimización.** Con pesos $w$, rentabilidades esperadas $\mu$ y covarianza $\Sigma$:
   $\mu_p = w^\top\mu$, $\sigma_p^2 = w^\top\Sigma w$, $S = (\mu_p - r_f)/\sigma_p$.
   El máximo Sharpe y la máxima diversificación se resuelven como problemas convexos con el cambio de variable
   $y = \kappa w$; la paridad de riesgo con el programa convexo de Spinu; HRP con clustering y bisección recursiva.
   Admite límites por activo, por clase de activo (los mixtos cuentan según su composición) y sobre fondos activos.
5. **Plan de ahorro.** Senda esperada con aportaciones mensuales y un Monte Carlo (log-normal, t de Student o
   bootstrap de bloques) con inflación, comisiones y retiradas.
6. **Backtest.** Walk-forward: cada rebalanceo solo ve datos pasados. Invertir cada mes en el mismo periodo da la
   rentabilidad ponderada por dinero (TIR).

La rentabilidad esperada no se puede estimar con precisión, así que usa el optimizador para entender los
compromisos entre riesgo y rentabilidad. No es asesoramiento financiero.
""",
}
