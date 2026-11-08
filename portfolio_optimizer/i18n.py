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
    "For funds Yahoo does not cover well (for example some Amundi or Carmignac funds). Give the ISIN if you have it "
    "and an ETF that follows the same index as proxy: real prices are used when they exist, otherwise the fund is "
    "simulated as the proxy minus the fee difference. A blend works too: EUNL.DE:0.6,EUNA.DE:0.4":
        "Para fondos que Yahoo no cubre bien (por ejemplo algunos fondos de Amundi o Carmignac). Pon el ISIN si lo "
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
    "Amundi index funds": "Fondos indexados de Amundi",
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
    "Yahoo history starts in 2022; earlier years use the proxy.":
        "El histórico de Yahoo empieza en 2022; los años anteriores usan el proxy.",
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
    "Realised gain": "Plusvalía realizada", "Estimated tax": "Impuesto estimado",
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
    # ---- search, import / export, accounts, horizons
    "10% to 90%": "Del 10 % al 90 %", "Account": "Cuenta remunerada", "Deposit": "Depósito",
    "Pension plan": "Plan de pensiones",
    "Add cash at a known interest rate. Forecasts use the TAE; the history follows the ECB rate (via the €STR) with "
    "today's spread, never below zero.":
        "Añade liquidez a un tipo de interés conocido. Las previsiones usan la TAE; el histórico sigue al tipo del BCE "
        "(a través del €STR) con el diferencial de hoy, sin bajar nunca de cero.",
    "Add to the universe": "Añadir a la lista", "Added by search or import": "Añadidos por búsqueda o importación",
    "Added: {n}": "Añadido: {n}", "Annualised return": "Rentabilidad anualizada",
    "Columns are detected automatically (ISIN or ticker, name, value, cost, type, TAE). Download a template from the "
    "My portfolio tab.":
        "Las columnas se detectan solas (ISIN o ticker, nombre, valor, coste, tipo, TAE). Tienes una plantilla en la "
        "pestaña Mi cartera.",
    "Could not import the file: {err}": "No se pudo importar el archivo: {err}",
    "Download an import template": "Descargar plantilla de importación",
    "Download portfolio (CSV)": "Descargar cartera (CSV)", "Download portfolio (Excel)": "Descargar cartera (Excel)",
    "Export your positions to CSV or Excel, edit them anywhere and import them again from the sidebar. Works with any "
    "bank or broker: only an ISIN or ticker (or the name) and a value are needed.":
        "Exporta tus posiciones a CSV o Excel, edítalas donde quieras y vuelve a importarlas desde la barra lateral. "
        "Sirve para cualquier banco o bróker: basta con un ISIN o ticker (o el nombre) y un importe.",
    "Factsheet": "Ficha", "open": "abrir", "Import a portfolio (CSV or Excel)": "Importar una cartera (CSV o Excel)",
    "Import and export": "Importar y exportar", "Imported {n} positions.": "Importadas {n} posiciones.",
    "Name, ISIN or ticker": "Nombre, ISIN o ticker",
    "Not found (add them as your own fund): {m}": "No encontrados (añádelos como fondo propio): {m}",
    "Nothing with price history found. Try another name or add it as your own fund.":
        "No hay resultados con histórico de precios. Prueba con otro nombre o añádelo como fondo propio.",
    "Reading the portfolio and finding each product...": "Leyendo la cartera y buscando cada producto...",
    "Remunerated accounts and deposits": "Cuentas remuneradas y depósitos", "Results": "Resultados",
    "Return and money by horizon": "Rentabilidad y dinero por plazo", "Search": "Buscar",
    "Search failed: {err}": "La búsqueda falló: {err}", "Search funds, ETFs and shares": "Buscar fondos, ETFs y acciones",
    "Searches Yahoo Finance by name, ISIN or ticker and keeps only products with price history. The classification is "
    "guessed and can be edited in the instrument table.":
        "Busca en Yahoo Finance por nombre, ISIN o ticker y solo muestra productos con histórico de precios. La "
        "clasificación se deduce del nombre y puedes corregirla en la tabla de instrumentos.",
    "Searching...": "Buscando...",
    "The longer you stay invested, the narrower the range of annualised returns. Money columns include your "
    "contributions.":
        "Cuanto más tiempo inviertes, más se estrecha el abanico de rentabilidades anualizadas. Las columnas de dinero "
        "incluyen tus aportaciones.",
    "Years invested": "Años invertido",
    "Your best account pays {r}, so it is used as the risk-free rate: risky assets must beat it.":
        "Tu mejor cuenta paga un {r}, así que se usa como tipo libre de riesgo: lo que tenga riesgo debe superarla.",
    "since": "desde", "years": "años",
    "Conservative: money market and short-term bonds": "Conservadora: monetarios y renta fija a corto",
    "MyInvestor funds": "Fondos de MyInvestor",
    "Return P10": "Rentab. P10", "Return P50": "Rentab. mediana", "Return P90": "Rentab. P90",
    "Probability of a loss": "Probabilidad de pérdida", "Money P10": "Dinero P10", "Money P50": "Dinero mediano",
    "Money P90": "Dinero P90", "Tax-free switch": "Sin tributar al mover",
    "Fixed income · Corporate": "Renta fija · Corporativa", "Fixed income · Short-term": "Renta fija · Corto plazo",
    "Fixed income · Income / high yield": "Renta fija · Income / high yield",
    "Equal-weight S&P 500; backfilled with the cap-weighted index.":
        "S&P 500 equiponderado; los años anteriores se rellenan con el índice ponderado por capitalización.",
    "Pension plan: contributions deduct from taxable income (up to 1,500 EUR a year) but the money is locked until "
    "retirement.":
        "Plan de pensiones: las aportaciones reducen la base imponible (hasta 1.500 € al año), pero el dinero queda "
        "bloqueado hasta la jubilación.",
    "Classified automatically and TER estimated: check them in the instrument table.":
        "Clasificado automáticamente y con TER estimado: revísalos en la tabla de instrumentos.",
    # ---- explanations
    "1 = they move together, 0 = unrelated, negative = they tend to move in opposite directions. Mixing assets with "
    "low correlation lowers the risk of the whole.":
        "1 = se mueven igual, 0 = no tienen relación, negativo = tienden a moverse al revés. Combinar activos poco "
        "correlacionados reduce el riesgo del conjunto.",
    "2.2% is J.P. Morgan's long-term euro inflation assumption.":
        "2,2 % es la inflación a largo plazo del euro que asume J.P. Morgan.",
    "Compound %": "Compuesta %", "Mean %": "Media %", "Source": "Fuente", "Set of assumptions": "Conjunto de hipótesis",
    "J.P. Morgan LTCMA 2027 (EUR)": "J.P. Morgan LTCMA 2027 (EUR)", "Conservative (own)": "Conservadora (propia)",
    "Each point is a portfolio: further right means more risk (volatility), higher means more expected return. The "
    "green curve is the efficient frontier: the best return you can expect for each level of risk. Diamonds are the "
    "strategies; the star is your portfolio. Grey dots are random portfolios, to show how much worse a careless mix "
    "can be.":
        "Cada punto es una cartera: más a la derecha, más riesgo (volatilidad); más arriba, más rentabilidad esperada. "
        "La curva verde es la frontera eficiente, es decir, lo máximo que puedes esperar ganar para cada nivel de "
        "riesgo. Los rombos son las estrategias y la estrella tu cartera. Los puntos grises son carteras al azar, para "
        "ver cuánto peor puede salir una mezcla hecha sin criterio.",
    "Expected annual returns in EUR for the next 10-15 years, before fees. By default they are the euro figures of "
    "J.P. Morgan's 2027 Long-Term Capital Market Assumptions; rows marked 'own' are not in the report. The optimiser "
    "and the Monte Carlo use the mean return; the compound return is what a buy-and-hold investor typically earns per "
    "year. Each asset gets the figure of its class and region minus its TER (plus alpha for active funds). "
    "Volatilities and correlations come from the data.":
        "Rentabilidades anuales esperadas en euros para los próximos 10 a 15 años, antes de comisiones. Por defecto "
        "son las cifras en euros de las Long-Term Capital Market Assumptions 2027 de J.P. Morgan; las filas marcadas "
        "'own' no están en el informe y son hipótesis propias. El optimizador y el Monte Carlo usan la rentabilidad "
        "media; la compuesta es la que suele obtener al año quien compra y mantiene. Cada activo recibe la cifra de "
        "su clase y región menos su TER (más el alfa si es un fondo activo). Volatilidades y correlaciones salen de "
        "los datos.",
    "Expected return of euro cash: 2.6% a year in J.P. Morgan's 2027 assumptions.":
        "Rentabilidad esperada de la liquidez en euros: 2,6 % anual según las previsiones 2027 de J.P. Morgan.",
    "Falls from the peak (drawdowns)": "Caídas desde máximos (drawdowns)",
    "For each holding period, the bar shows the range of average yearly returns across scenarios: light = 80% of "
    "cases, dark = the middle half, dot = median. Over one year almost anything can happen; over 20 years the range "
    "narrows a lot. Money columns include your contributions.":
        "Para cada plazo, la barra muestra entre qué valores queda la rentabilidad media anual en los distintos "
        "escenarios: claro = el 80 % de los casos, oscuro = la mitad central, punto = la mediana. En un año puede "
        "pasar casi cualquier cosa; en 20 años el abanico se estrecha mucho. Las columnas de dinero incluyen tus "
        "aportaciones.",
    "Glossary": "Glosario", "Growth of 100 invested": "Evolución de 100 € invertidos",
    "How each strategy would really have done if you had followed it, deciding every rebalance with only the "
    "information available at the time.":
        "Cómo habría ido de verdad cada estrategia si la hubieras seguido, decidiendo cada rebalanceo solo con la "
        "información disponible en ese momento.",
    "How far each asset was below its previous high at every moment. -30% means it had lost 30% from its best value "
    "so far; the line returns to 0% when the loss is fully recovered. Deep and long dips are what test an investor's "
    "nerves.":
        "Cuánto estaba cada activo por debajo de su máximo anterior en cada momento. -30 % significa que había perdido "
        "un 30 % desde su mejor valor hasta entonces; la línea vuelve a 0 % cuando la pérdida se ha recuperado del "
        "todo. Las caídas profundas y largas son las que ponen a prueba los nervios de un inversor.",
    "How the final value is distributed across all scenarios. The further right the tail, the more the result "
    "depends on luck.":
        "Cómo se reparte el valor final entre todos los escenarios. Cuanto más larga la cola de la derecha, más "
        "depende el resultado de la suerte.",
    "How the strategy changed its allocation at each rebalance.":
        "Cómo cambió la estrategia su reparto en cada rebalanceo.",
    "Return of each asset in each calendar year (the first year may be partial). Blue = gain, red = loss.":
        "Rentabilidad de cada activo en cada año natural (el primero puede estar incompleto). Azul = ganancia, rojo = "
        "pérdida.",
    "Start here": "Empieza aquí", "The strategies, explained": "Las estrategias, explicadas",
    "The typical (median) path: half of the scenarios end above it and half below. It grows at {g} a year, less than "
    "the {m} average return, because ups and downs eat into compound growth (volatility drag).":
        "La senda típica (mediana): la mitad de los escenarios acaba por encima y la otra mitad por debajo. Crece al "
        "{g} anual, menos que la rentabilidad media del {m}, porque las subidas y bajadas restan crecimiento "
        "compuesto (el llamado lastre de la volatilidad).",
    "The worst moments of each strategy: how much it was below its previous high.":
        "Los peores momentos de cada estrategia: cuánto estaba por debajo de su máximo anterior.",
    "Thousands of possible futures. The dark band holds the middle half of the scenarios and the light band 90% of "
    "them; the blue line is the median and the dotted line the money you put in. Thin grey lines are individual "
    "scenarios: notice how bumpy each one is.":
        "Miles de futuros posibles. La banda oscura recoge la mitad central de los escenarios y la clara el 90 %; la "
        "línea azul es la mediana y la punteada el dinero que aportas. Las líneas grises finas son escenarios "
        "concretos: fíjate en lo irregular que es cada uno.",
    "What 100 euros invested at the start became in each asset, dividends included and already net of the fund's "
    "fees. The log scale makes equal percentage moves look equal.":
        "En qué se convirtieron 100 € invertidos al principio en cada activo, con dividendos incluidos y ya netos de "
        "comisiones. La escala logarítmica hace que subidas porcentuales iguales se vean iguales.",
    "What does each strategy mean?": "¿Qué significa cada estrategia?",
    # ---- portfolio builder and layout
    "Account or deposit": "Cuenta o depósito",
    "Add the funds, ETFs or accounts you own (or want to own), import them from a CSV or Excel file, or load an "
    "example. You need at least two products.":
        "Añade los fondos, ETFs o cuentas que tienes (o que quieres tener), impórtalos desde un CSV o Excel o carga "
        "un ejemplo. Hacen falta al menos dos productos.",
    "Add to my portfolio": "Añadir a mi cartera", "Added to your portfolio: {n}": "Añadido a tu cartera: {n}",
    "Amount you paid (€, optional)": "Lo que pagaste (€, opcional)",
    "Build your portfolio product by product, import it from a file or try the example.":
        "Crea tu cartera producto a producto, impórtala desde un archivo o prueba el ejemplo.",
    "Build, compare and plan your investment portfolio: ETFs, index and active funds, bonds and cash.":
        "Construye, compara y planifica tu cartera de inversión: ETFs, fondos indexados y activos, renta fija y "
        "liquidez.",
    "Change the value or the amount paid, or select a row and press delete to remove it.":
        "Cambia el valor o lo que pagaste, o selecciona una fila y pulsa suprimir para quitarla.",
    "Current value (€)": "Valor actual (€)", "Data since": "Datos desde",
    "Edit amounts or remove positions": "Editar importes o quitar posiciones",
    "Educational tool, not advice": "Herramienta educativa, no es asesoramiento",
    "From the list": "De la lista", "Gain": "Plusvalía", "Gain %": "Plusvalía %",
    "Load an example portfolio": "Cargar una cartera de ejemplo",
    "My portfolio: {n} positions · {v}": "Mi cartera: {n} posiciones · {v}",
    "No price data for: {m}. They are left out of the analysis.":
        "No hay precios para: {m}. Se dejan fuera del análisis.",
    "Press Add to my portfolio to choose a fund, ETF or account and type how much you have in it. You can also "
    "import a CSV or Excel file from the sidebar, or load an example to explore.":
        "Pulsa Añadir a mi cartera, elige un fondo, ETF o cuenta y escribe cuánto tienes. También puedes importar un "
        "CSV o Excel desde la barra lateral, o cargar un ejemplo para explorar.",
    "Product": "Producto", "Products": "Productos", "Products to compare": "Productos para comparar",
    "Remove all positions": "Quitar todas las posiciones", "Remunerated account": "Cuenta remunerada",
    "Search any fund or ETF": "Buscar cualquier fondo o ETF",
    "Start by building your portfolio": "Empieza construyendo tu cartera",
    "Type to filter: MSCI World, Vanguard, gold, bonds...": "Escribe para filtrar: MSCI World, Vanguard, oro, bonos...",
    "Used for the gain and the tax estimate. Leave 0 if you do not know it.":
        "Sirve para calcular la plusvalía y estimar impuestos. Déjalo en 0 si no lo sabes.",
    "Weight": "Peso", "What do you want to add?": "¿Qué quieres añadir?",
    "Your portfolio is empty": "Tu cartera está vacía",
    "Your positions are always included. Add other products here to compare them or use them in the optimiser.":
        "Tus posiciones siempre se incluyen. Añade aquí otros productos para compararlos o usarlos en el optimizador.",
    "empty": "vacía", "Import a portfolio or load a session": "Importar cartera o cargar sesión",
    # ---- landing, navigation and footer
    "About": "Autor", "Add at least one more product to start the analysis.":
        "Añade al menos un producto más para empezar el análisis.",
    "Add what you own, product by product, with its current value.":
        "Añade lo que tienes, producto a producto, con su valor actual.",
    "Build your portfolio": "Crea tu cartera",
    "Build your portfolio with any ETF, index or active fund, bond fund or savings account, see what you can expect "
    "at every horizon and compare it with the strategies professionals use.":
        "Crea tu cartera con cualquier ETF, fondo indexado o activo, fondo de renta fija o cuenta remunerada, mira qué "
        "puedes esperar a cada plazo y compárala con las estrategias que usan los profesionales.",
    "Build, compare and plan your investment portfolio": "Construye, compara y planifica tu cartera de inversión",
    "Choose ETFs, funds...": "Elige ETFs, fondos...", "Compare with": "Comparar con",
    "Data and sources": "Datos y fuentes",
    "Educational tool to build and analyse investment portfolios. It is not financial, investment or tax advice: "
    "past returns and forecasts do not guarantee future results.":
        "Herramienta educativa para construir y analizar carteras de inversión. No es asesoramiento financiero, de "
        "inversión ni fiscal: las rentabilidades pasadas y las previsiones no garantizan resultados futuros.",
    "Explore an example": "Explora un ejemplo", "Guide and methodology": "Guía y metodología",
    "Import a file": "Importa un archivo",
    "Loads a typical set of products to compare. Your own positions are always included.":
        "Carga un conjunto típico de productos para comparar. Tus posiciones siempre se incluyen.",
    "None": "Ninguna", "None selected": "Ninguno seleccionado",
    "Prices may be delayed. Use at your own risk.": "Los precios pueden ir con retraso. Úsalo bajo tu responsabilidad.",
    "Project": "Proyecto", "Ready-made selection": "Selección predefinida",
    "See every feature working with a realistic diversified portfolio.":
        "Mira todas las funciones con una cartera diversificada realista.",
    "Settings": "Ajustes", "Source code": "Código fuente", "Technical guide": "Guía técnica",
    "Tip: in the sidebar you can also pick products just to compare them, without adding them to your portfolio.":
        "Consejo: en la barra lateral también puedes elegir productos solo para compararlos, sin añadirlos a tu "
        "cartera.",
    "Upload a CSV or Excel export from your bank or broker; columns are detected automatically.":
        "Sube un CSV o Excel exportado de tu banco o bróker; las columnas se detectan solas.",
    "Your investments, clearly.": "Tus inversiones, con claridad.",
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
2. **Expected returns.** By default, J.P. Morgan's 2027 Long-Term Capital Market Assumptions (euro table) per asset
   class and region, net of each fund's TER, with an optional alpha for active funds (zero by default, as the SPIVA
   evidence suggests). Historical,
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
2. **Rentabilidad esperada.** Por defecto, las Long-Term Capital Market Assumptions 2027 de J.P. Morgan (tabla en
   euros) por clase de activo y región, netas del TER de cada fondo, con un alfa opcional para los fondos activos
   (cero por defecto, como sugieren los informes SPIVA).
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


GUIDE = {
    "es": """
### Cómo usar Portfolio Optimizer

Portfolio Optimizer sirve para construir y revisar una cartera de inversión a largo plazo, sea cual sea tu banco o bróker.
No te dice qué comprar: te ayuda a ver qué riesgo asumes, cómo se reparte tu dinero y qué puedes esperar a cada plazo.

1. **Crea tu cartera** con el botón **Añadir a mi cartera** de la barra lateral: eliges un producto de la lista,
   buscas cualquier fondo o ETF por nombre o ISIN, o añades una cuenta remunerada, y escribes cuánto tienes. También
   puedes importar tu cartera desde un CSV o Excel, o cargar un ejemplo. Debajo puedes añadir otros productos solo
   para compararlos.
2. **Mira el Resumen.** Cómo se ha comportado cada producto, cuánto llegó a caer y si se parecen entre sí.
3. **Compara estrategias en el Optimizador.** Cada estrategia es una forma distinta de repartir el dinero entre los
   mismos productos. Abajo tienes cada una explicada.
4. **Introduce lo que tienes en Mi cartera.** Verás tu distribución por tipo de activo, región y gestión, y un plan
   para acercarte a la cartera objetivo usando primero el dinero nuevo (sin vender ni pagar impuestos).
5. **Proyecta tu ahorro en Plan de ahorro.** Con tu aportación mensual y tu plazo verás el dinero esperado y los
   escenarios buenos y malos.
6. **Comprueba en Backtest** cómo habría funcionado cada estrategia en los últimos años, sin trampas.

### Cuatro ideas para no perderse

- **Rentabilidad y riesgo van juntos.** Más rentabilidad esperada siempre implica aceptar caídas más grandes por el
  camino. La pregunta útil es cuánto puedes ver caer tu cartera sin vender.
- **Diversificar es lo único gratis.** Combinar activos que no se mueven igual reduce el riesgo sin reducir tanto la
  rentabilidad. Por eso importa la correlación.
- **El plazo lo cambia todo.** En un año casi cualquier resultado es posible; en veinte, el abanico se estrecha
  mucho. La pestaña Plan de ahorro lo muestra.
- **Los costes se acumulan.** Un 1 % de comisión anual durante 30 años se come cerca de una cuarta parte del
  capital final. Fíjate en el TER.

### De dónde salen las previsiones

Por defecto, las rentabilidades esperadas son las de J.P. Morgan Asset Management en sus *Long-Term Capital Market
Assumptions 2027* para un inversor en euros (horizonte de 10 a 15 años), menos el TER de cada producto. Son una
referencia profesional, no una promesa: puedes cambiarlas en el Optimizador. Volatilidades y correlaciones salen del
histórico de precios.

*Esta herramienta es educativa y no constituye asesoramiento financiero ni fiscal.*
""",
    "en": """
### How to use Portfolio Optimizer

Portfolio Optimizer helps you build and review a long-term investment portfolio, whatever your bank or broker. It does not
tell you what to buy: it shows the risk you take, how your money is spread and what you can expect at each horizon.

1. **Build your portfolio** with the **Add to my portfolio** button in the sidebar: pick a product from the list,
   search any fund or ETF by name or ISIN, or add a remunerated account, and type how much you hold. You can also
   import it from a CSV or Excel file or load an example. Below, add other products just to compare them.
2. **Look at the Overview**: how each product behaved, how far it fell and whether they move alike.
3. **Compare strategies in the Optimiser.** Each strategy is a different way of splitting money between the same
   products. Each one is explained below.
4. **Enter what you own in My portfolio** to see your allocation by asset class, region and management, and a plan to
   move towards the target using new money first (no selling, no tax).
5. **Project your savings in Savings plan**: expected money plus good and bad scenarios for your monthly contribution
   and horizon.
6. **Check in Backtest** how each strategy would really have done in recent years.

### Four ideas to keep in mind

- **Return and risk go together.** Higher expected return always means bigger falls along the way. The useful
  question is how big a fall you can watch without selling.
- **Diversification is the only free lunch.** Combining assets that do not move alike lowers risk without cutting
  return as much. That is why correlation matters.
- **Time changes everything.** Over one year almost anything can happen; over twenty the range narrows a lot.
- **Costs compound.** A 1% annual fee over 30 years eats about a quarter of the final capital. Watch the TER.

### Where the forecasts come from

By default, expected returns are J.P. Morgan Asset Management's *2027 Long-Term Capital Market Assumptions* for a euro
investor (10-15 year horizon), minus each product's TER. They are a professional reference, not a promise; you can
change them in the Optimiser. Volatilities and correlations come from price history.

*This tool is educational and is not financial or tax advice.*
""",
}

STRATEGY_HELP = {
    "es": {
        "Maximum Sharpe": "Busca la cartera con más rentabilidad esperada por cada unidad de riesgo (el ratio de "
                          "Sharpe). Es la cartera óptima de la teoría de Markowitz.\n\n**Para quién:** quien confía en "
                          "las previsiones de rentabilidad. **Ventaja:** la más eficiente sobre el papel. **Cuidado:** "
                          "es muy sensible a las previsiones; un cambio pequeño puede mover mucho los pesos y tiende a "
                          "concentrarse en pocos activos. Por eso conviene limitar el peso máximo por activo.",
        "Minimum variance": "La cartera con la menor volatilidad posible, sin mirar la rentabilidad.\n\n**Para "
                            "quién:** perfiles conservadores o quien no se fía de ninguna previsión. **Ventaja:** solo "
                            "usa riesgos y correlaciones, que se estiman mucho mejor que las rentabilidades. "
                            "**Cuidado:** se carga de renta fija y liquidez, así que su rentabilidad esperada es baja.",
        "Maximum diversification": "Saca el máximo partido a diversificar: prefiere activos que se mueven de forma "
                                   "distinta entre sí.\n\n**Para quién:** quien quiere repartir de verdad. **Ventaja:** "
                                   "no depende de las previsiones de rentabilidad. **Cuidado:** puede dar mucho peso a "
                                   "un activo solo porque no se parece al resto.",
        "Risk parity": "Reparte el riesgo, no el dinero: cada activo aporta la misma parte de la volatilidad total. "
                       "Como los bonos se mueven menos que las acciones, reciben más dinero.\n\n**Para quién:** quien "
                       "quiere una cartera equilibrada para cualquier entorno económico (la idea de la cartera All "
                       "Weather). **Ventaja:** robusta y sin previsiones. **Cuidado:** sin endeudamiento, su "
                       "rentabilidad esperada es moderada.",
        "HRP": "Paridad de riesgo jerárquica: agrupa los activos que se parecen (por ejemplo, tres fondos del MSCI "
               "World) y reparte el riesgo primero entre grupos y luego dentro de cada grupo.\n\n**Para quién:** "
               "carteras con muchos productos parecidos. **Ventaja:** muy estable, no se descontrola con activos casi "
               "idénticos. **Cuidado:** es una regla de reparto, no busca la máxima rentabilidad.",
        "Inverse volatility": "Cada activo pesa en proporción inversa a su volatilidad: lo que se mueve el doble "
                              "recibe la mitad.\n\n**Para quién:** quien busca una regla sencilla de explicar. "
                              "**Ventaja:** transparente. **Cuidado:** ignora cómo se relacionan los activos entre sí.",
        "Equal weight": "El mismo dinero en cada activo.\n\n**Para quién:** como punto de referencia. **Ventaja:** no "
                        "necesita estimar nada y varios estudios muestran que es difícil de batir fuera de muestra "
                        "(DeMiguel, Garlappi y Uppal, 2009). **Cuidado:** el resultado depende por completo de qué "
                        "productos elijas: con cuatro de renta variable y uno de bonos, la cartera es muy arriesgada.",
    },
    "en": {
        "Maximum Sharpe": "The portfolio with the highest expected return per unit of risk (the Sharpe ratio): the "
                          "optimal portfolio of Markowitz theory.\n\n**For whom:** investors who trust the return "
                          "forecasts. **Pro:** the most efficient on paper. **Watch out:** very sensitive to the "
                          "forecasts and prone to concentration, so cap the weight per asset.",
        "Minimum variance": "The lowest possible volatility, ignoring returns.\n\n**For whom:** cautious investors or "
                            "anyone who distrusts forecasts. **Pro:** only uses risks and correlations, which are "
                            "estimated far better than returns. **Watch out:** loads up on bonds and cash, so its "
                            "expected return is low.",
        "Maximum diversification": "Gets the most out of diversification by favouring assets that move differently."
                                   "\n\n**For whom:** investors who want a truly spread portfolio. **Pro:** no return "
                                   "forecasts needed. **Watch out:** may overweight an asset just because it is "
                                   "different.",
        "Risk parity": "Spreads risk, not money: every asset contributes the same share of total volatility, so "
                       "calmer assets such as bonds get more money.\n\n**For whom:** investors who want balance in any "
                       "economic environment (the All Weather idea). **Pro:** robust, no forecasts. **Watch out:** "
                       "without leverage its expected return is moderate.",
        "HRP": "Hierarchical risk parity: groups similar assets (e.g. three MSCI World funds) and spreads risk first "
               "between groups and then within each group.\n\n**For whom:** portfolios with many similar products. "
               "**Pro:** very stable. **Watch out:** it is an allocation rule, it does not chase return.",
        "Inverse volatility": "Each asset weighs in inverse proportion to its volatility.\n\n**For whom:** anyone who "
                              "wants a simple rule. **Pro:** transparent. **Watch out:** ignores correlations.",
        "Equal weight": "The same money in each asset.\n\n**For whom:** as a benchmark. **Pro:** nothing to estimate, "
                        "and studies show it is hard to beat out of sample (DeMiguel, Garlappi and Uppal, 2009). "
                        "**Watch out:** the result depends entirely on which products you pick.",
    },
}

GLOSSARY = {
    "es": """
- **Volatilidad:** cuánto suben y bajan los precios. Un 15 % anual significa que, en un año normal, la rentabilidad
  suele moverse unos 15 puntos por encima o por debajo de la media.
- **Rentabilidad media y compuesta:** la media es el promedio de las rentabilidades anuales; la compuesta es la que
  de verdad hace crecer tu dinero y siempre es algo menor cuando hay volatilidad.
- **Ratio de Sharpe:** rentabilidad por encima de la liquidez dividida por la volatilidad. Más alto es mejor.
- **Caída máxima (drawdown):** la mayor pérdida desde un máximo hasta un mínimo posterior.
- **Correlación:** si dos activos suben y bajan a la vez (cerca de 1) o no (cerca de 0 o negativa).
- **Frontera eficiente:** las carteras que dan la mayor rentabilidad esperada para cada nivel de riesgo.
- **TER:** gastos corrientes anuales del fondo o ETF, ya descontados de su precio.
- **Monte Carlo:** simular miles de futuros posibles para ver el abanico de resultados, no solo uno.
- **Percentiles (P5, P50, P95):** P5 es un escenario malo (solo el 5 % de los casos acaba peor), P50 el escenario
  mediano y P95 uno bueno.
- **TIR:** rentabilidad anual que has obtenido teniendo en cuenta cuándo aportaste cada euro.
- **Traspaso:** mover dinero de un fondo a otro en España sin pagar impuestos hasta que vendas definitivamente. No
  existe para ETFs.
- **Rebalancear:** volver a los pesos objetivo cuando el mercado los ha desviado.
- **Backtest fuera de muestra:** probar una estrategia en el pasado usando en cada momento solo la información que
  existía entonces.
- **ETF, ETC, fondo indexado, fondo activo:** un ETF cotiza en bolsa y suele replicar un índice; un ETC replica una
  materia prima como el oro; un fondo indexado replica un índice pero no cotiza; un fondo activo tiene un gestor que
  elige las inversiones y suele cobrar más.
""",
    "en": """
- **Volatility:** how much prices go up and down. 15% a year means a typical year lands about 15 points above or
  below the average.
- **Mean and compound return:** the mean averages yearly returns; the compound return is what actually grows your
  money and is always a bit lower when there is volatility.
- **Sharpe ratio:** return above cash divided by volatility. Higher is better.
- **Max drawdown:** the largest fall from a peak to a later low.
- **Correlation:** whether two assets move together (near 1) or not (near 0 or negative).
- **Efficient frontier:** the portfolios with the highest expected return for each level of risk.
- **TER:** a fund's or ETF's annual running costs, already taken out of its price.
- **Monte Carlo:** simulating thousands of possible futures to see the range of outcomes.
- **Percentiles (P5, P50, P95):** P5 is a bad scenario (only 5% of cases end lower), P50 the median, P95 a good one.
- **IRR:** the yearly return you earned, taking into account when each euro went in.
- **Traspaso:** moving money between funds in Spain without paying tax until you finally sell. Not available for ETFs.
- **Rebalancing:** going back to the target weights after markets have moved them.
- **Out-of-sample backtest:** testing a strategy on the past using, at each moment, only the information available
  then.
- **ETF, ETC, index fund, active fund:** an ETF trades on an exchange and usually tracks an index; an ETC tracks a
  commodity such as gold; an index fund tracks an index but is not listed; an active fund has a manager who picks the
  investments and usually charges more.
""",
}
