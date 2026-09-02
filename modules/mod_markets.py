import pandas as pd
import streamlit as st
import yfinance as yf
from portfolio_controller import PortfolioController


def get_ticker_snapshot(symbol: str):
    """Función auxiliar para obtener precio y cambio porcentual de forma segura."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.get("lastPrice", 0.0) or 0.0
        prev = info.get("previousClose", price) or price
        change_pct = ((price - prev) / prev * 100) if prev else 0.0
        return price, change_pct
    except Exception:
        return 0.0, 0.0


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
        "Petróleo WTI": "CL=F"
    }
    selected_metal_name = st.selectbox("Seleccione el Metal:", list(dict_metales.keys()), key="sel_metal")
    metal_ticker = dict_metales[selected_metal_name]

    m_price, m_chg = get_ticker_snapshot(metal_ticker)
    st.metric(selected_metal_name, f"${m_price:,.2f}", f"{m_chg:+.2f}%")

    if st.button(f"💾 Guardar {selected_metal_name}", key="save_metal_btn"):
        if PortfolioController.save_market_quote(metal_ticker, selected_metal_name, "Commodity", m_price, m_chg):
            st.success(f"✅ {selected_metal_name} guardado en TiDB.")
        else:
            st.error("❌ Error al guardar en TiDB.")

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
        "FTSE 100 (UK)": "^FTSE"
    }
    selected_index_name = st.selectbox("Seleccione el Índice:", list(dict_indices.keys()), key="sel_index")
    index_ticker = dict_indices[selected_index_name]

    i_price, i_chg = get_ticker_snapshot(index_ticker)
    st.metric(selected_index_name, f"{i_price:,.2f} pts", f"{i_chg:+.2f}%")

    if st.button(f"💾 Guardar {selected_index_name}", key="save_index_btn"):
        if PortfolioController.save_market_quote(index_ticker, selected_index_name, "Index", i_price, i_chg):
            st.success(f"✅ {selected_index_name} guardado en TiDB.")
        else:
            st.error("❌ Error al guardar en TiDB.")

    # -------------------------------------------------------------------------
    # 3. CATEGORÍA ACCIONES DE WALL STREET
    # -------------------------------------------------------------------------
    with col_m3:
    st.subheader("🏢 Acciones Wall Street")
    dict_acciones = {
        "Apple Inc. (AAPL)": "AAPL",
        "NVIDIA Corp. (NVDA)": "NVDA",
        "Microsoft Corp. (MSFT)": "MSFT",
        "Tesla Inc. (TSLA)": "TSLA",
        "Amazon.com (AMZN)": "AMZN",
        "Alphabet / Google (GOOGL)": "GOOGL",
        "Meta Platforms (META)": "META"
    }
    selected_stock_name = st.selectbox("Seleccione la Acción:", list(dict_acciones.keys()), key="sel_stock")
    stock_ticker = dict_acciones[selected_stock_name]

    s_price, s_chg = get_ticker_snapshot(stock_ticker)
    st.metric(selected_stock_name, f"${s_price:,.2f}", f"{s_chg:+.2f}%")

    if st.button(f"💾 Guardar {stock_ticker}", key="save_stock_btn"):
        if PortfolioController.save_market_quote(stock_ticker, selected_stock_name, "Equity", s_price, s_chg):
            st.success(f"✅ {selected_stock_name} guardado en TiDB.")
        else:
            st.error("❌ Error al guardar en TiDB.")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 2. BUSCADOR E HISTÓRICO DE ACTIVOS
    # -------------------------------------------------------------------------
    st.subheader("🔍 Buscador e Histórico de Activos Financieros")

    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        symbol = st.text_input(
            "Ingrese el Ticker o Símbolo de Mercado (ej. AAPL, NVDA, TSLA, GC=F, ^IXIC, BTC-USD):",
            value="NVDA",
        ).strip().upper()
    with col_search2:
        period = st.selectbox(
            "Rango de Tiempo",
            ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            index=3,
        )

    if symbol:
        try:
            asset = yf.Ticker(symbol)
            df_hist = asset.history(period=period)

            if not df_hist.empty:
                curr_price, chg_pct = get_ticker_snapshot(symbol)

                st.write(f"### Evolución del Precio: **{symbol}**")
                st.line_chart(df_hist["Close"])

                col_sub1, col_sub2 = st.columns([3, 1])
                with col_sub1:
                    st.subheader("📊 Resumen de Datos Históricos")
                    st.dataframe(
                        df_hist[
                            ["Open", "High", "Low", "Close", "Volume"]
                        ].tail(10),
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
                    )
                    if st.button(f"💾 Guardar {symbol} en TiDB", key="save_search_asset"):
                        if PortfolioController.save_market_quote(
                            symbol,
                            symbol,
                            asset_type_input,
                            curr_price,
                            chg_pct,
                        ):
                            st.success(f"✅ {symbol} guardado en TiDB Cloud.")
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