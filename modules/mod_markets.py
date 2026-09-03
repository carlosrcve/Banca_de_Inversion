# mod_markets.py
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from portfolio_controller import PortfolioController

# -------------------------------------------------------------------------
# FUNCIÓN EN CACHÉ PARA CARGAR LAS ACCIONES DEL S&P 500 DINÁMICAMENTE
# -------------------------------------------------------------------------
@st.cache_data(ttl=86400)  # Guarda la lista en caché durante 24 horas
def load_sp500_tickers():
    """Descarga la lista actualizada del S&P 500 desde Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df_sp500 = tables[0]

        dict_sp500 = {}
        for _, row in df_sp500.iterrows():
            symbol = str(row["Symbol"]).replace(".", "-")
            name = row["Security"]
            dict_sp500[f"{symbol} - {name}"] = symbol

        return dict_sp500
    except Exception:
        return {
            "AAPL - Apple Inc.": "AAPL",
            "NVDA - NVIDIA Corp.": "NVDA",
            "MSFT - Microsoft Corp.": "MSFT",
            "AMZN - Amazon.com Inc.": "AMZN",
            "GOOGL - Alphabet Inc.": "GOOGL",
            "META - Meta Platforms": "META",
            "TSLA - Tesla Inc.": "TSLA",
            "BRK-B - Berkshire Hathaway": "BRK-B",
            "JPM - JPMorgan Chase & Co.": "JPM",
            "V - Visa Inc.": "V",
        }


# -------------------------------------------------------------------------
# FUNCIÓN EN CACHÉ PARA OBTENER COTIZACIONES
# -------------------------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def get_ticker_snapshot(symbol: str):
    """Obtiene de forma segura el precio actual y variación del ticker con caché."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.get("lastPrice", 0.0) or 0.0
        prev = info.get("previousClose", price) or price
        change_pct = ((price - prev) / prev * 100) if prev else 0.0
        return float(price), float(change_pct)
    except Exception:
        return 0.0, 0.0


# -------------------------------------------------------------------------
# FRAGMENTOS CON ESTADO AISLADO
# -------------------------------------------------------------------------
@st.fragment
def render_metals_column():
    st.subheader("🪙 Metales y Commodities")
    dict_metales = {
        "Oro (Gold Spot)": "GC=F",
        "Plata (Silver)": "SI=F",
        "Cobre (Copper)": "HG=F",
        "Platino (Platinum)": "PL=F",
        "Petróleo WTI": "CL=F",
    }
    selected_metal_name = st.selectbox(
        "Seleccione el Metal:", list(dict_metales.keys()), key="sel_metal"
    )
    metal_ticker = dict_metales[selected_metal_name]

    state_key = f"data_{metal_ticker}"
    if state_key not in st.session_state or st.session_state.get("last_metal") != metal_ticker:
        st.session_state[state_key] = get_ticker_snapshot(metal_ticker)
        st.session_state["last_metal"] = metal_ticker

    m_price, m_chg = st.session_state[state_key]
    st.metric(selected_metal_name, f"${m_price:,.2f}", f"{m_chg:+.2f}%")

    if st.button(f"💾 Guardar {selected_metal_name}", key="save_metal_btn"):
        success, err_details = PortfolioController.save_market_quote(
            symbol=metal_ticker,
            asset_name=selected_metal_name,
            asset_type="Commodity",
            price=float(m_price),
            change_percent=float(m_chg),
        )
        if success:
            st.success(f"✅ {selected_metal_name} guardado en TiDB.")
        else:
            st.error(f"❌ Error al guardar en TiDB: {err_details}")

@st.fragment
def render_indices_column():
    st.subheader("📊 Índices Bursátiles")
    dict_indices = {
        "Nasdaq Composite": "^IXIC",
        "S&P 500": "^GSPC",
        "Dow Jones Industrial": "^DJI",
        "Russell 2000": "^RUT",
        "FTSE 100 (UK)": "^FTSE",
    }
    selected_index_name = st.selectbox(
        "Seleccione el Índice:", list(dict_indices.keys()), key="sel_index"
    )
    index_ticker = dict_indices[selected_index_name]

    state_key = f"data_{index_ticker}"
    if state_key not in st.session_state or st.session_state.get("last_index") != index_ticker:
        st.session_state[state_key] = get_ticker_snapshot(index_ticker)
        st.session_state["last_index"] = index_ticker

    i_price, i_chg = st.session_state[state_key]
    st.metric(selected_index_name, f"{i_price:,.2f} pts", f"{i_chg:+.2f}%")

    if st.button(f"💾 Guardar {selected_index_name}", key="save_index_btn"):
        if PortfolioController.save_market_quote(
            index_ticker, selected_index_name, "Index", i_price, i_chg
        ):
            st.success(f"✅ {selected_index_name} guardado en TiDB.")
        else:
            st.error("❌ Error al guardar en TiDB.")


@st.fragment
def render_stocks_column():
    st.subheader("🏢 Acciones Wall Street")
    dict_acciones = load_sp500_tickers()

    selected_stock_label = st.selectbox(
        f"Seleccione ({len(dict_acciones)} Acciones):",
        options=list(dict_acciones.keys()),
        key="sel_stock",
    )
    stock_ticker = dict_acciones[selected_stock_label]

    state_key = f"data_{stock_ticker}"
    if state_key not in st.session_state or st.session_state.get("last_stock") != stock_ticker:
        st.session_state[state_key] = get_ticker_snapshot(stock_ticker)
        st.session_state["last_stock"] = stock_ticker

    s_price, s_chg = st.session_state[state_key]
    display_name = selected_stock_label.split(" - ")[0]
    st.metric(display_name, f"${s_price:,.2f}", f"{s_chg:+.2f}%")

    if st.button(f"💾 Guardar {stock_ticker}", key="save_stock_btn"):
        if PortfolioController.save_market_quote(
            stock_ticker, selected_stock_label, "Equity", s_price, s_chg
        ):
            st.success(f"✅ {stock_ticker} guardado en TiDB.")
        else:
            st.error("❌ Error al guardar en TiDB.")


# -------------------------------------------------------------------------
# FUNCIÓN RENDER PRINCIPAL
# -------------------------------------------------------------------------
def render():
    st.title("📈 Análisis de Mercados & Clases de Activos Globales")
    
    # CSS personalizado para:
    # 1. Crear un contenedor con scroll horizontal.
    # 2. Asegurar que cada columna tenga un ancho mínimo fijo.
    st.markdown("""
        <style>
        .scrollable-container {
            display: flex;
            flex-direction: row;
            overflow-x: auto;
            gap: 15px;
            padding-bottom: 15px;
            width: 100%;
        }
        .scrollable-container > div {
            min-width: 250px;
            flex: 1;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="scrollable-container">', unsafe_allow_html=True)

    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

    # 1. COMMODITIES
    with col_m1:
        st.markdown("### 🪙 Commodities")
        dict_metales = {
            "Oro (Gold Spot)": "GC=F",
            "Plata (Silver)": "SI=F",
            "Cobre (Copper)": "HG=F",
            "Platino (Platinum)": "PL=F",
            "Petróleo WTI": "CL=F",
        }
        selected_metal_name = st.selectbox(
            "Seleccione:", list(dict_metales.keys()), key="sel_metal"
        )
        metal_ticker = dict_metales[selected_metal_name]

        m_price, m_chg = get_ticker_snapshot(metal_ticker)
        st.metric(selected_metal_name, f"${m_price:,.2f}", f"{m_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_metal_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(
                metal_ticker, selected_metal_name, "Commodity", m_price, m_chg
            )
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    # 2. ÍNDICES
    with col_m2:
        st.markdown("### 📊 Índices")
        dict_indices = {
            "Nasdaq Composite": "^IXIC",
            "S&P 500": "^GSPC",
            "Dow Jones Industrial": "^DJI",
            "Russell 2000": "^RUT",
            "FTSE 100 (UK)": "^FTSE",
        }
        selected_index_name = st.selectbox(
            "Seleccione:", list(dict_indices.keys()), key="sel_index"
        )
        index_ticker = dict_indices[selected_index_name]

        i_price, i_chg = get_ticker_snapshot(index_ticker)
        st.metric(selected_index_name, f"{i_price:,.2f} pts", f"{i_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_index_btn", use_container_width=True):
            if PortfolioController.save_market_quote(
                index_ticker, selected_index_name, "Index", i_price, i_chg
            ):
                st.success("✅ Guardado.")
            else:
                st.error("❌ Error al guardar.")

    # 3. ACCIONES
    with col_m3:
        st.markdown("### 🏢 Acciones")
        dict_acciones = load_sp500_tickers()
        
        selected_stock_label = st.selectbox(
            "Seleccione:",
            options=list(dict_acciones.keys()),
            key="sel_stock"
        )
        stock_ticker = dict_acciones[selected_stock_label]

        s_price, s_chg = get_ticker_snapshot(stock_ticker)
        st.metric(selected_stock_label.split(" - ")[0], f"${s_price:,.2f}", f"{s_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_stock_btn", use_container_width=True):
            if PortfolioController.save_market_quote(
                stock_ticker, selected_stock_label, "Equity", s_price, s_chg
            ):
                st.success("✅ Guardado.")
            else:
                st.error("❌ Error al guardar.")

    # 4. DIVISAS BCV
    with col_m4:
        st.markdown("### 🇻🇪 Divisas BCV")
        dict_divisas = {
            "Dólar Oficial (BCV)": "USDVES=X",
            "Euro Oficial (BCV)": "EURVES=X",
        }
        selected_divisa_name = st.selectbox(
            "Seleccione:", list(dict_divisas.keys()), key="sel_divisa"
        )
        divisa_ticker = dict_divisas[selected_divisa_name]

        d_price, d_chg = get_ticker_snapshot(divisa_ticker)
        price_str = f"Bs. {d_price:,.2f}" if d_price and d_price > 0 else "Bs. S/D"
        st.metric(selected_divisa_name, price_str, f"{d_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_divisa_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(
                divisa_ticker, selected_divisa_name, "Currency", d_price, d_chg
            )
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    # 5. FOREX MAJORS
    with col_m5:
        st.markdown("### 💱 Forex Majors")
        dict_forex = {
            "Euro / Dólar (EUR/USD)": "EURUSD=X",
            "Libra / Dólar (GBP/USD)": "GBPUSD=X",
            "Dólar / Yen (USD/JPY)": "USDJPY=X",
            "Dólar / Dólar Canadiense (USD/CAD)": "USDCAD=X",
            "Dólar / Corona Sueca (USD/SEK)": "USDSEK=X",
        }
        selected_forex_name = st.selectbox(
            "Seleccione:", list(dict_forex.keys()), key="sel_forex"
        )
        forex_ticker = dict_forex[selected_forex_name]

        f_price, f_chg = get_ticker_snapshot(forex_ticker)
        price_forex_str = f"{f_price:,.4f}" if f_price and f_price > 0 else "S/D"
        st.metric(selected_forex_name, price_forex_str, f"{f_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_forex_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(
                forex_ticker, selected_forex_name, "Forex", f_price, f_chg
            )
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 2. BUSCADOR E HISTÓRICO DE ACTIVOS (BLOQUE UNIFICADO)
    # -------------------------------------------------------------------------
    st.subheader("🔍 Buscador & Asesor Inteligente de Activos")

    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        input_usuario = st.text_input(
            "Ingrese el Ticker o Símbolo de Mercado (ej. AAPL, NVDA, Oro, Dolar BCV, S&P 500):",
            value="Oro",
            key="input_search_symbol",
        )
    with col_search2:
        period = st.selectbox(
            "Rango de Tiempo",
            ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            index=3,
            key="select_search_period",
        )

    # 2. Diccionario ampliado de lenguaje natural a Tickers de Yahoo Finance
    traductor_global = {
        # --- COMMODITIES / METALES ---
        "oro": "GC=F",
        "gold": "GC=F",
        "plata": "SI=F",
        "silver": "SI=F",
        "cobre": "HG=F",
        "copper": "HG=F",
        "platino": "PL=F",
        "platinum": "PL=F",
        "petroleo": "CL=F",
        "petróleo": "CL=F",
        "wti": "CL=F",

        # --- VENEZUELA (BCV / DIVISAS OFICIALES) ---
        "dolar bcv": "USDVES=X",
        "dólar bcv": "USDVES=X",
        "dolar": "USDVES=X",
        "dólar": "USDVES=X",
        "euro bcv": "EURVES=X",
        "euro": "EURVES=X",

        # --- ÍNDICES BURSÁTILES GLOBALES ---
        "s&p 500": "^GSPC",
        "sp500": "^GSPC",
        "nasdaq": "^IXIC",
        "nasdaq 100": "^NDX",
        "dow jones": "^DJI",
        "ibex": "^IBEX",
        "bitcoin": "BTC-USD",

        # --- ACCIONES POPULARES (Ejemplos) ---
        "apple": "AAPL",
        "tesla": "TSLA",
        "nvidia": "NVDA",
        "microsoft": "MSFT",
        "amazon": "AMZN"
    }

    # 3. Procesamiento y Limpieza Inteligente
    limpio = input_usuario.strip().lower()

    if limpio in traductor_global:
        symbol = traductor_global[limpio]
        
        # Asignación automática de categoría según el tipo de activo traducido
        if symbol in ["GC=F", "SI=F", "HG=F", "PL=F", "CL=F"]:
            asset_category = "Commodity"
        elif "VES" in symbol:
            asset_category = "Currency"  # O tu categoría para el BCV
        elif symbol.startswith("^"):
            asset_category = "Index"
        else:
            asset_category = "Equity"
            
    else:
        # Si el usuario escribe directamente un ticker tradicional (ej. AAPL, MSFT, ^IXIC)
        symbol = input_usuario.strip().upper()
        
        # Tu lógica original de respaldo para detectar categorías si escriben el ticker directo
        if symbol.startswith("^"):
            asset_category = "Index"
        elif "VES" in symbol:
            asset_category = "Currency"
        elif "=" in symbol or "-USD" in symbol:
            asset_category = "Forex"
        else:
            asset_category = "Equity"

    # ==========================================
    # INICIO DE EJECUCIÓN SI EXISTE SÍMBOLO
    # ==========================================
    if symbol:
        try:
            asset = yf.Ticker(symbol)
            df_hist = asset.history(period=period)

            if not df_hist.empty:
                curr_price, chg_pct = get_ticker_snapshot(symbol)

                # ==========================================
                # DETECCIÓN AUTOMÁTICA DE REFUERZO
                # ==========================================
                symbol_upper = symbol.upper()
                if "=" in symbol_upper or "-USD" in symbol_upper:
                    if any(m in symbol_upper for m in ["GC", "SI", "CL", "HG", "PL"]):
                        asset_category = "Commodity"
                    elif "VES" in symbol_upper:
                        asset_category = "Currency"
                    else:
                        asset_category = "Forex"
                elif symbol_upper.startswith("^"):
                    asset_category = "Index"
                else:
                    asset_category = "Equity"
                # ==========================================

                # METADATOS COMUNES
                info = getattr(asset, "info", {})
                long_name = info.get("longName", info.get("shortName", symbol))
                currency = info.get("currency", "USD")
                
                # Definición de variables preventivas para evitar errores en métricas o análisis
                target_price = info.get("targetMeanPrice", None)

                st.markdown(f"### 💡 Diagnóstico Financiero: **{long_name} ({symbol})**")

                # =========================================================================
                # 1. FRAME ESPECIALIZADO: ACCIONES (EQUITY)
                # =========================================================================
                if asset_category == "Equity":
                    pe_ratio = info.get("trailingPE", None)
                    recommendation = info.get("recommendationKey", "N/A").upper()
                    roe = info.get("returnOnEquity", None)
                    market_cap = info.get("marketCap", None)
                    shares_out = info.get("sharesOutstanding", None)
                    eps = info.get("trailingEps", None)
                    dividend_rate = info.get("dividendRate", None)
                    dividend_yield = info.get("dividendYield", None)

                    q_rev_str, q_net_str = "N/A", "N/A"
                    try:
                        qf = asset.quarterly_financials
                        if qf is not None and not qf.empty:
                            rev_rows = [r for r in qf.index if "Revenue" in str(r)]
                            net_rows = [r for r in qf.index if "Net Income" in str(r)]
                            if rev_rows:
                                val_rev = qf.loc[rev_rows[0]].iloc[0]
                                if pd.notnull(val_rev):
                                    q_rev_str = f"${val_rev:,.0f}"
                            if net_rows:
                                val_net = qf.loc[net_rows[0]].iloc[0]
                                if pd.notnull(val_net):
                                    q_net_str = f"${val_net:,.0f}"
                    except Exception:
                        pass

                    # Fila 1 Acciones
                    col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                    with col_i1:
                        st.metric("Precio Actual", f"${curr_price:,.2f} {currency}", f"{chg_pct:+.2f}%")
                    with col_i2:
                        pe_str = f"{pe_ratio:.1f}x" if pe_ratio else "N/A"
                        st.metric("P/E Ratio (Valuación)", pe_str, "Caro > 35 / Barato < 15")
                    with col_i3:
                        roe_str = f"{roe*100:.1f}%" if roe else "N/A"
                        st.metric("ROE (¿Da Ganancias?)", roe_str, "Eficiencia del capital")
                    with col_i4:
                        rec_display = recommendation.replace("_", " ") if recommendation else "NEUTRAL"
                        st.metric("Opinión Wall Street", rec_display, "Consenso de analistas")

                    # Fila 2 Acciones
                    col_j1, col_j2, col_j3, col_j4 = st.columns(4)
                    with col_j1:
                        mcap_str = f"${market_cap:,.0f}" if market_cap else "N/A"
                        st.metric("Capitalización Bursátil", mcap_str, "Valor total de mercado")
                    with col_j2:
                        shares_str = f"{shares_out:,.0f}" if shares_out else "N/A"
                        st.metric("Acciones en Circulación", shares_str, "Total de títulos vivos")
                    with col_j3:
                        st.metric("Ingresos Trimestrales", q_rev_str, "Último reporte trimestral")
                    with col_j4:
                        st.metric("Ganancias Trimestrales", q_net_str, "Utilidad neta trimestral")

                    # Fila 3 Acciones
                    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
                    with col_k1:
                        eps_str = f"${eps:,.2f}" if eps is not None else "N/A"
                        st.metric("Utilidad por Acción (EPS)", eps_str, "Ganancia neta por título")
                    with col_k2:
                        div_rate_str = f"${dividend_rate:,.2f}" if dividend_rate is not None else "$0.00"
                        st.metric("Dividendo Anual / Acción", div_rate_str, "Pago anual al inversor")
                    with col_k3:
                        div_yield_str = f"{dividend_yield*100:.2f}%" if dividend_yield is not None else "0.00%"
                        st.metric("Rendimiento por Dividendo", div_yield_str, "Yield porcentual anual")
                    with col_k4:
                        if dividend_rate is not None and shares_out is not None:
                            total_divs = dividend_rate * shares_out
                            tot_divs_str = f"${total_divs:,.0f}"
                        else:
                            tot_divs_str = "N/A"
                        st.metric("Total Dividendos Pagados", tot_divs_str, "Estimación global anual")

                    # Fila 4 Acciones
                    profit_margin = info.get("profitMargins", None)
                    debt_to_equity = info.get("debtToEquity", None)
                    pb_ratio = info.get("priceToBook", None)
                    beta = info.get("beta", None)

                    col_l1, col_l2, col_l3, col_l4 = st.columns(4)
                    with col_l1:
                        margin_str = f"{profit_margin*100:.1f}%" if profit_margin is not None else "N/A"
                        st.metric("Margen de Utilidad Neta", margin_str, "Eficiencia en ganancias")
                    with col_l2:
                        debt_str = f"{debt_to_equity:.1f}%" if debt_to_equity is not None else "N/A"
                        st.metric("Deuda / Capital (D/E)", debt_str, "Nivel de apalancamiento")
                    with col_l3:
                        pb_str = f"{pb_ratio:.2f}x" if pb_ratio is not None else "N/A"
                        st.metric("Precio / Valor en Libros", pb_str, "Valuación patrimonial")
                    with col_l4:
                        beta_str = f"{beta:.2f}" if beta is not None else "N/A"
                        st.metric("Beta (Volatilidad)", beta_str, "Riesgo frente al mercado")

                    st.markdown("---")
                    html_interpretation = (
                        '<div style="background-color: #e8f4f8; border-left: 5px solid #29b6f6; padding: 18px 20px; border-radius: 8px; color: #1a202c; margin-bottom: 20px;">'
                        '<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #0288d1;">📝 Diagnóstico Ejecutivo de Acciones (Equity):</div>'
                        '<p style="margin: 0; line-height: 1.6;">Evaluación integral basada en múltiplos de valuación (P/E, P/B), eficiencia de capital (ROE), estructura de deuda y directrices de consenso de Wall Street.</p>'
                        '</div>'
                    )

                # =========================================================================
                # 2. FRAME ESPECIALIZADO: METALES Y COMMODITIES (METALS)
                # =========================================================================
                elif asset_category == "Commodity":
                    volume = info.get("volume", 0) if info.get("volume") is not None else 0
                    
                    safe_curr_price = curr_price if curr_price is not None else 0.0
                    safe_chg_pct = chg_pct if chg_pct is not None else 0.0
                    
                    high_period = df_hist['High'].max() if not df_hist.empty and pd.notnull(df_hist['High'].max()) else safe_curr_price
                    low_period = df_hist['Low'].min() if not df_hist.empty and pd.notnull(df_hist['Low'].min()) else safe_curr_price

                    c1, c2, c3, c4 = st.columns(4)
                    with c1: 
                        st.metric("Cotización Spot", f"${safe_curr_price:,.2f} USD", f"{safe_chg_pct:+.2f}%")
                    with c2: 
                        st.metric("Máximo del Periodo", f"${high_period:,.2f}", "Techo técnico temporal")
                    with c3: 
                        st.metric("Mínimo del Periodo", f"${low_period:,.2f}", "Piso temporal")
                    with c4: 
                        st.metric("Volumen Negociado", f"{volume:,.0f}" if volume else "N/A", "Liquidez de mercado")

                    st.markdown("---")
                    html_interpretation = (
                        '<div style="background-color: #fff9e6; border-left: 5px solid #ffb300; padding: 18px 20px; border-radius: 8px; color: #1a202c; margin-bottom: 20px;">'
                        '<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #f57c00;">📝 Diagnóstico Especializado de Commodities / Metales:</div>'
                        '<p style="margin: 0; line-height: 1.6;">Activos tangibles de cobertura contra la inflación y refugio geopolítico. Su comportamiento está dictado por los flujos de contratos de futuros, la oferta física y las expectativas monetarias globales.</p>'
                        '</div>'
                    )

                # =========================================================================
                # 3. FRAME ESPECIALIZADO: ÍNDICES BURSÁTILES (INDEX)
                # =========================================================================
                elif asset_category == "Index":
                    high_index = df_hist['High'].max() if not df_hist.empty else 0
                    low_index = df_hist['Low'].min() if not df_hist.empty else 0

                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("Nivel del Índice", f"{curr_price:,.2f} pts", f"{chg_pct:+.2f}%")
                    with c2: st.metric("Máximo del Rango", f"{high_index:,.2f} pts", "Máximo en el periodo")
                    with c3: st.metric("Mínimo del Rango", f"{low_index:,.2f} pts", "Mínimo en el periodo")
                    with c4: st.metric("Estado de Tendencia", "Expansión / Alcista" if chg_pct >= 0 else "Contracción / Recorte", "Sentimiento general")

                    st.markdown("---")
                    html_interpretation = (
                        '<div style="background-color: #e8f8f0; border-left: 5px solid #2e7d32; padding: 18px 20px; border-radius: 8px; color: #1a202c; margin-bottom: 20px;">'
                        '<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #2e7d32;">📝 Diagnóstico de Índice Bursátil de Referencia:</div>'
                        '<p style="margin: 0; line-height: 1.6;">Termómetro agregado del mercado accionario o sectorial. Refleja la salud general de las principales empresas que lo componen y la dirección del apetito de riesgo institucional.</p>'
                        '</div>'
                    )

                # =========================================================================
                # 4. FRAME ESPECIALIZADO: DÓLAR / DIVISAS BANCO CENTRAL (BCV / VES)
                # =========================================================================
                elif "VES" in symbol.upper() or "USDVES" in symbol.upper() or "EURVES" in symbol.upper() or asset_category == "Currency":
                    high_bcv = df_hist['High'].max() if not df_hist.empty else curr_price
                    low_bcv = df_hist['Low'].min() if not df_hist.empty else curr_price

                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("Tasa Oficial BCV", f"Bs. {curr_price:,.4f}", f"{chg_pct:+.2f}%")
                    with c2: st.metric("Máximo en Periodo", f"Bs. {high_bcv:,.4f}", "Techo cambiario oficial")
                    with c3: st.metric("Mínimo en Periodo", f"Bs. {low_bcv:,.4f}", "Piso cambiario oficial")
                    with c4: st.metric("Tipo de Referencia", "Oficial / BCV", "Tasa legal de intercambio")

                    st.markdown("---")
                    html_interpretation = (
                        '<div style="background-color: #fce4ec; border-left: 5px solid #e91e63; padding: 18px 20px; border-radius: 8px; color: #1a202c; margin-bottom: 20px;">'
                        '<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #c2185b;">📝 Diagnóstico Cambiario Oficial (Banco Central):</div>'
                        '<p style="margin: 0; line-height: 1.6;">Seguimiento riguroso de la paridad oficial establecida por el ente emisor. Vital para la indexación contable, conversiones financieras corporativas y el cálculo de obligaciones fiscales locales bajo normativa venezolana.</p>'
                        '</div>'
                    )

                # =========================================================================
                # 5. FRAME ESPECIALIZADO: MERCADO FOREX GLOBAL (PARES INTERNACIONALES)
                # =========================================================================
                else:
                    high_fx = df_hist['High'].max() if not df_hist.empty else curr_price
                    low_fx = df_hist['Low'].min() if not df_hist.empty else curr_price

                    c1, c2, c3, c4 = st.columns(4)
                    with c1: st.metric("Tasa de Cambio Forex", f"{curr_price:,.4f}", f"{chg_pct:+.2f}%")
                    with c2: st.metric("Máximo del Par", f"{high_fx:,.4f}", "Resistencia en el periodo")
                    with c3: st.metric("Mínimo del Par", f"{low_fx:,.4f}", "Soporte en el periodo")
                    with c4: st.metric("Mercado Divisas", symbol, "Par internacional negociado")

                    st.markdown("---")
                    html_interpretation = (
                        '<div style="background-color: #f3e5f5; border-left: 5px solid #7b1fa2; padding: 18px 20px; border-radius: 8px; color: #1a202c; margin-bottom: 20px;">'
                        '<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #7b1fa2;">📝 Diagnóstico de Mercado Forex (Divisas Globales):</div>'
                        '<p style="margin: 0; line-height: 1.6;">Análisis de la fortaleza relativa entre economías globales. Evalúa la fluctuación de tipos de interés cruzados, políticas monetarias de bancos centrales internacionales y flujos de comercio exterior.</p>'
                        '</div>'
                    )

                st.markdown(html_interpretation, unsafe_allow_html=True)
                st.markdown("---")

                # =============================================================
                # GENERACIÓN DE ANÁLISIS TÉCNICO Y PEDAGÓGICO AVANZADO (HTML)
                # =============================================================
                if asset_category == "Equity":
                    pe_text = f"Con un P/E de {pe_ratio:.1f}x y un P/B de {pb_ratio:.2f}x, la acción cotiza con una prima exigente, reflejando altas expectativas de crecimiento futuro." if pe_ratio and pb_ratio and pe_ratio > 30 else f"P/E de {pe_ratio:.1f}x y P/B de {pb_ratio:.2f}x, sugiriendo una valoración equilibrada frente a sus fundamentales."
                    roe_text = f"Destacada eficiencia en la generación de valor con un ROE del {(roe*100):.1f}% y un margen neto del {(profit_margin*100):.1f}%, demostrando un sólido poder de fijación de precios y control de costos." if roe and profit_margin else "Rentabilidad bajo revisión por falta de datos históricos completos."
                    risk_text = f"Nivel de apalancamiento (Deuda/Capital) ubicado en un sano {debt_to_equity:.1f}%. El coeficiente Beta de {beta:.2f} indica una volatilidad superior a la media del mercado, ideal para estrategias dinámicas." if debt_to_equity is not None and beta is not None else "Perfil de riesgo moderado bajo las condiciones actuales del sector."
                    
                    potencial = ((target_price - curr_price) / curr_price) * 100 if target_price and target_price > 0 else 0.0
                    target_text = f"El consenso de analistas (Opinión: <b>{recommendation.replace('_', ' ')}</b>) proyecta un precio objetivo medio de <b>${target_price:,.2f}</b>, lo que representa un potencial de retorno estimado de <b>{potencial:+.1f}%</b> desde el precio actual." if target_price else "Sin cobertura de precio objetivo activo por el consenso."

                    html_interpretation = (
                        f'<div style="background-color: #e8f4f8; border-left: 5px solid #29b6f6; padding: 18px 20px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; color: #1a202c; margin-bottom: 20px;">'
                        f'<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #0288d1;">📝 Diagnóstico Financiero Integral y Análisis Técnico (Equity):</div>'
                        f'<ul style="margin: 0; padding-left: 20px; line-height: 1.6;">'
                        f'<li style="margin-bottom: 8px;"><b>🏢 Valuación y Múltiplos de Mercado:</b> {pe_text}</li>'
                        f'<li style="margin-bottom: 8px;"><b>📈 Rentabilidad y Calidad Operativa:</b> {roe_text}</li>'
                        f'<li style="margin-bottom: 8px;"><b>⚖️ Estructura de Capital y Riesgo Sistemático (Beta):</b> {risk_text}</li>'
                        f'<li style="margin-bottom: 0px;"><b>🎯 Perspectiva de Wall Street y Consenso:</b> {target_text}</li>'
                        f'</ul>'
                        f'</div>'
                    )

                elif asset_category == "Commodity":
                    range_comm = high_period - low_period if 'high_period' in locals() and 'low_period' in locals() else 0
                    comm_text = f"La volatilidad del periodo muestra una amplitud de ${range_comm:,.2f} entre soportes y resistencias temporales, reflejando presiones de oferta y demanda física."
                    
                    html_interpretation = (
                        f'<div style="background-color: #fff9e6; border-left: 5px solid #ffb300; padding: 18px 20px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; color: #1a202c; margin-bottom: 20px;">'
                        f'<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #f57c00;">📝 Diagnóstico Especializado de Commodities / Metales:</div>'
                        f'<ul style="margin: 0; padding-left: 20px; line-height: 1.6;">'
                        f'<li style="margin-bottom: 8px;"><b>🛡️ Cobertura y Refugio:</b> Activos tangibles utilizados tradicionalmente para mitigar los efectos de la inflación y las tensiones geopolíticas globales.</li>'
                        f'<li style="margin-bottom: 0px;"><b>📊 Comportamiento de Rango:</b> {comm_text}</li>'
                        f'</ul>'
                        f'</div>'
                    )

                elif asset_category == "Index":
                    trend_msg = "alcista / expansiva" if chg_pct >= 0 else "bajista / de contracción"
                    html_interpretation = (
                        f'<div style="background-color: #e8f8f0; border-left: 5px solid #2e7d32; padding: 18px 20px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; color: #1a202c; margin-bottom: 20px;">'
                        f'<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #2e7d32;">📝 Diagnóstico de Índice Bursátil de Referencia:</div>'
                        f'<ul style="margin: 0; padding-left: 20px; line-height: 1.6;">'
                        f'<li style="margin-bottom: 8px;"><b>🌐 Sentimiento de Mercado:</b> El índice opera bajo una tónica {trend_msg}, sirviendo como termómetro directo del apetito de riesgo institucional.</li>'
                        f'<li style="margin-bottom: 0px;"><b>📈 Diversificación Agregada:</b> Su desempeño resume la salud financiera de las principales capitalizaciones que lo integran.</li>'
                        f'</ul>'
                        f'</div>'
                    )

                elif "VES" in symbol.upper() or "USDVES" in symbol.upper() or "EURVES" in symbol.upper() or asset_category == "Currency":
                    html_interpretation = (
                        f'<div style="background-color: #fce4ec; border-left: 5px solid #e91e63; padding: 18px 20px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; color: #1a202c; margin-bottom: 20px;">'
                        f'<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #c2185b;">📝 Diagnóstico Cambiario Oficial (Banco Central):</div>'
                        f'<ul style="margin: 0; padding-left: 20px; line-height: 1.6;">'
                        f'<li style="margin-bottom: 8px;"><b>📌 Obligaciones Legales y Fiscales:</b> Tasa de referencia obligatoria para la emisión de facturación formal, cálculos impositivos y presentación de estados financieros en bolívares.</li>'
                        f'<li style="margin-bottom: 0px;"><b>🔄 Paridad Oficial:</b> Monitoreo estricto de la política cambiaria del emisor para la correcta conversión contable corporativa.</li>'
                        f'</ul>'
                        f'</div>'
                    )

                else:
                    html_interpretation = (
                        f'<div style="background-color: #f3e5f5; border-left: 5px solid #7b1fa2; padding: 18px 20px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; color: #1a202c; margin-bottom: 20px;">'
                        f'<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #7b1fa2;">📝 Diagnóstico de Mercado Forex (Divisas Globales):</div>'
                        f'<ul style="margin: 0; padding-left: 20px; line-height: 1.6;">'
                        f'<li style="margin-bottom: 8px;"><b>💱 Fortaleza Relativa:</b> Análisis cruzado de tipos de interés y flujos de capital entre economías internacionales.</li>'
                        f'<li style="margin-bottom: 0px;"><b>🌍 Dinámica Macroeconómica:</b> Sensible a publicaciones de bancos centrales, datos de empleo y balanzas comerciales.</li>'
                        f'</ul>'
                        f'</div>'
                    )

                st.markdown(html_interpretation, unsafe_allow_html=True)
                st.markdown("---")
                st.write(f"### Evolución del Precio (Velas Japonesas): **{symbol}**")

                # GRÁFICO DE VELAS CON PLOTLY
                df_hist = df_hist.reset_index()
                fig = go.Figure(
                    data=[
                        go.Candlestick(
                            x=df_hist["Date"],
                            open=df_hist["Open"],
                            high=df_hist["High"],
                            low=df_hist["Low"],
                            close=df_hist["Close"],
                            name=symbol,
                            increasing_line_color="#26a69a",
                            decreasing_line_color="#ef5350",
                        )
                    ]
                )

                fig.update_layout(
                    xaxis_rangeslider_visible=False,
                    template="plotly_dark",
                    margin=dict(l=10, r=10, t=30, b=10),
                    height=450,
                )

                st.plotly_chart(fig, use_container_width=True, key=f"candlestick_chart_{symbol}_{period}")

                col_sub1, col_sub2 = st.columns([3, 1])
                with col_sub1:
                    st.subheader("📊 Resumen de Datos Históricos")
                    st.dataframe(
                        df_hist[["Date", "Open", "High", "Low", "Close", "Volume"]].tail(10),
                        use_container_width=True,
                    )

                with col_sub2:
                    st.subheader("💾 Guardar Búsqueda")
                    st.metric(
                        "Último Precio",
                        f"${curr_price:,.2f}",
                        f"{chg_pct:+.2f}%",
                    )
                    asset_type_input = st.selectbox(
                        "Tipo de Activo",
                        ["Equity", "Commodity", "Index", "Crypto", "FX"],
                        key="select_asset_type_save",
                    )
                    if st.button(f"💾 Guardar {symbol} en TiDB", key="save_search_asset"):
                        if PortfolioController.save_market_quote(
                            symbol,
                            long_name,
                            asset_type_input,
                            curr_price,
                            chg_pct,
                        ):
                            st.success(f"✅ {symbol} ({long_name}) guardado en TiDB Cloud.")
                        else:
                            st.error("❌ Error al guardar en TiDB.")
            else:
                st.warning(f"⚠️ No se encontraron datos para el símbolo '{symbol}'. Verifique la nomenclatura.")
        except Exception as err:
            st.error(f"❌ Error al obtener los datos de mercado: {err}")

    st.markdown("---")
    # -------------------------------------------------------------------------
    # 3. HISTORIAL DE COTIZACIONES EN TiDB
    # -------------------------------------------------------------------------
    st.subheader("📋 Historial de Cotizaciones Registradas en TiDB")
    if st.button("🔄 Cargar / Refrescar Cotizaciones de la BD"):
        quotes = PortfolioController.get_market_quotes()
        if quotes:
            df_quotes = pd.DataFrame(quotes)
            st.dataframe(
                df_quotes.style.format({
                    "price": "${:,.2f}",
                    "change_percent": "{:+.2f}%",
                }),
                use_container_width=True,
            )
        else:
            st.info("ℹ️ No hay cotizaciones guardadas aún en TiDB Cloud.")