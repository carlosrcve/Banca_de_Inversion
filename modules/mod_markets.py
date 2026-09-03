import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from portfolio_controller import PortfolioController
import plotly.graph_objects as go

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
    st.markdown("""
    Consulta cotizaciones e históricos en tiempo real de **Acciones, Commodities (Oro) e Índices Tecnológicos**, 
    con opción de registrar el *snapshot* actual en la base de datos **TiDB Cloud**.
    """)



    col_m1, col_m2, col_m3 = st.columns(3)

    # -------------------------------------------------------------------------
    # 1. CATEGORÍA COMMODITIES / METALES
    # -------------------------------------------------------------------------
    with col_m1:
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

        m_price, m_chg = get_ticker_snapshot(metal_ticker)
        st.metric(selected_metal_name, f"${m_price:,.2f}", f"{m_chg:+.2f}%")

        if st.button(f"💾 Guardar {selected_metal_name}", key="save_metal_btn"):
            success, err_msg = PortfolioController.save_market_quote(
                metal_ticker, selected_metal_name, "Commodity", m_price, m_chg
            )
            if success:
                st.success(f"✅ {selected_metal_name} guardado en TiDB.")
            else:
                st.error(f"❌ Error al guardar: {err_msg}")

    # -------------------------------------------------------------------------
    # 2. CATEGORÍA ÍNDICES GLOBALES / MERCADOS
    # -------------------------------------------------------------------------
    with col_m2:
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

        i_price, i_chg = get_ticker_snapshot(index_ticker)
        st.metric(selected_index_name, f"{i_price:,.2f} pts", f"{i_chg:+.2f}%")

        if st.button(f"💾 Guardar {selected_index_name}", key="save_index_btn"):
            if PortfolioController.save_market_quote(
                index_ticker, selected_index_name, "Index", i_price, i_chg
            ):
                st.success(f"✅ {selected_index_name} guardado en TiDB.")
            else:
                st.error("❌ Error al guardar en TiDB.")

    # -------------------------------------------------------------------------
    # 3. CATEGORÍA ACCIONES DE WALL STREET (DINÁMICO CON S&P 500)
    # -------------------------------------------------------------------------
    with col_m3:
        st.subheader("🏢 Acciones Wall Street")
        
        # Cargar diccionario de acciones
        dict_acciones = load_sp500_tickers()
        
        selected_stock_label = st.selectbox(
            f"Seleccione entre {len(dict_acciones)} Acciones:",
            options=list(dict_acciones.keys()),
            key="sel_stock"
        )
        stock_ticker = dict_acciones[selected_stock_label]

        s_price, s_chg = get_ticker_snapshot(stock_ticker)
        st.metric(selected_stock_label.split(" - ")[0], f"${s_price:,.2f}", f"{s_chg:+.2f}%")

        if st.button(f"💾 Guardar {stock_ticker}", key="save_stock_btn"):
            if PortfolioController.save_market_quote(
                stock_ticker, selected_stock_label, "Equity", s_price, s_chg
            ):
                st.success(f"✅ {stock_ticker} guardado en TiDB Cloud.")
            else:
                st.error("❌ Error al guardar en TiDB Cloud.")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 2. BUSCADOR INTELIGENTE E INTELIGENCIA FINANCIERA DE ACTIVOS
    # -------------------------------------------------------------------------
    st.subheader("🔍 Buscador & Asesor Inteligente de Activos")

    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        symbol = st.text_input(
            "Ingrese el Ticker (ej. AAPL, NVDA, TSLA, MSFT, AMZN):",
            value="AAPL",
            key="input_search_symbol",
        ).strip().upper()
    with col_search2:
        period = st.selectbox(
            "Rango de Tiempo Gráfico",
            ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            index=3,
            key="select_search_period",
        )

    if symbol:
        try:
            asset = yf.Ticker(symbol)
            df_hist = asset.history(period=period)

            if not df_hist.empty:
                curr_price, chg_pct = get_ticker_snapshot(symbol)
                
                # Obtener metadatos financieros avanzados para el análisis dinámico
                info = getattr(asset, "info", {})
                long_name = info.get("longName", symbol)
                sector = info.get("sector", "N/A")
                currency = info.get("currency", "USD")
                pe_ratio = info.get("trailingPE", None)
                forward_pe = info.get("forwardPE", None)
                target_price = info.get("targetMeanPrice", None)
                recommendation = info.get("recommendationKey", "N/A").upper()
                profit_margins = info.get("profitMargins", None)
                roe = info.get("returnOnEquity", None)
                w52_high = info.get("fiftyTwoWeekHigh", None)
                w52_low = info.get("fiftyTwoWeekLow", None)

                # =================================================================
                # PANEL DE INTELIGENCIA Y VALORACIÓN (EL PLUS DEL SISTEMA)
                # =================================================================
                st.markdown(f"### 💡 Diagnóstico Financiero Inteligente: **{long_name} ({symbol})**")
                
                # Tarjetas métricas ejecutivas
                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                with col_i1:
                    st.metric("Precio Actual", f"${curr_price:,.2f} {currency}", f"{chg_pct:+.2f}%")
                with col_i2:
                    pe_str = f"{pe_ratio:.1f}x" if pe_ratio else "N/A"
                    st.metric("P/E Ratio (Valuración)", pe_str, "Histórico del Mercado")
                with col_i3:
                    roe_str = f"{roe*100:.1f}%" if roe else "N/A"
                    st.metric("ROE (Rentabilidad)", roe_str, "Eficiencia del Capital")
                with col_i4:
                    rec_display = recommendation.replace("_", " ") if recommendation else "NEUTRAL"
                    st.metric("Opinión de Wall Street", rec_display, "Consenso Analistas")

                # Criterios y Diagnóstico Automático (Conduciendo al inversionista)
                st.markdown("#### 🧠 Veredicto Automático del Sistema")
                
                # Reglas lógicas simples para guiar al usuario
                mensajes_analisis = []
                
                if w52_high and w52_low:
                    if curr_price >= (w52_high * 0.90):
                        mensajes_analisis.append(f"⚠️ **Precio cercano a máximos de 52 semanas (${w52_high:,.2f}):** El activo muestra mucha fortaleza, pero evalúe si está pagando una prima alta.")
                    elif curr_price <= (w52_low * 1.10):
                        mensajes_analisis.append(f"💰 **Precio cercano a mínimos de 52 semanas (${w52_low:,.2f}):** Podría representar una oportunidad de valor, siempre que los fundamentales de la empresa sigan sólidos.")
                
                if pe_ratio:
                    if pe_ratio > 35:
                        mensajes_analisis.append(f"📈 **Valuración alta (P/E {pe_ratio:.1f}):** Los inversionistas están esperando un crecimiento agresivo de ganancias en el futuro. Valide si el negocio justifica este múltiplo.")
                    elif pe_ratio < 15:
                        mensajes_analisis.append(f"📉 **Valuración atractiva (P/E {pe_ratio:.1f}):** El mercado cotiza este activo a un múltiplo moderado en relación con sus beneficios.")
                
                if target_price and target_price > 0:
                    potencial = ((target_price - curr_price) / curr_price) * 100
                    mensajes_analisis.append(f"🎯 **Precio Objetivo del Consenso:** Los analistas sitúan un valor medio de **${target_price:,.2f}** (un potencial estimado de **{potencial:+.1f}%**).")

                if not mensajes_analisis:
                    mensajes_analisis.append("ℹ️ Activo cotizando bajo condiciones normales de mercado. Monitoree tendencias sectoriales.")

                for msg in mensajes_analisis:
                    st.info(msg)

                st.markdown("---")

                # =================================================================
                # GRÁFICO TÉCNICO DE VELAS JAPONESAS
                # =================================================================
                st.write(f"### 📈 Evolución Histórica de Velas Japonesas: **{symbol}**")
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
                    st.subheader("📊 Historial Reciente de Precios")
                    st.dataframe(
                        df_hist[["Date", "Open", "High", "Low", "Close", "Volume"]].tail(10),
                        use_container_width=True,
                    )

                with col_sub2:
                    st.subheader("💾 Guardar en TiDB")
                    st.metric(
                        "Precio de Registro",
                        f"${curr_price:,.2f}",
                        f"{chg_pct:+.2f}%",
                    )
                    asset_type_input = st.selectbox(
                        "Tipo de Activo",
                        ["Equity", "Commodity", "Index", "Crypto", "FX"],
                        key="select_asset_type_save",
                    )
                    if st.button(f"💾 Guardar {symbol} en TiDB", key="save_search_asset"):
                        success, err_msg = PortfolioController.save_market_quote(
                            symbol,
                            long_name,
                            asset_type_input,
                            curr_price,
                            chg_pct,
                        )
                        if success:
                            st.success(f"✅ {symbol} ({long_name}) guardado con éxito en TiDB Cloud.")
                        else:
                            st.error(f"❌ Error al guardar: {err_msg}")
            else:
                st.warning(f"⚠️ No se encontraron datos históricos para '{symbol}'. Verifique la nomenclatura.")
        except Exception as err:
            st.error(f"❌ Error al procesar la información de mercado: {err}")

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