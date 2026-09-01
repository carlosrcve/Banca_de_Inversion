# app.py
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import date
from dcf_controller import DCFController
from dcf_models import DCFInputs
import numpy as np
import pandas as pd
from portfolio_controller import PortfolioController
import streamlit as st
import yfinance as yf

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA Y NAVEGACIÓN
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gylfi Software - Banca de Inversión",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("🏛️ Gylfi Software")
st.sidebar.markdown("**Suite de Banca de Inversión**")

# Navegación Principal
module = st.sidebar.radio(
    "Navegación / Módulos",
    [
        "📊 Modelo DCF & M&A",
        "📈 Mercados & Clases de Activos",
        "💼 Gestión de Portafolio",
    ],
)

st.sidebar.markdown("---")

# -----------------------------------------------------------------------------
# MÓDULO 1: MODELO DCF & M&A
# -----------------------------------------------------------------------------
if module == "📊 Modelo DCF & M&A":
    st.title("📊 Modelo de Valoración por Flujo de Caja Descontado (DCF)")
    st.markdown("""
    Calcula el **Valor de la Empresa (Enterprise Value)** y el **Valor del Patrimonio (Equity Value)** 
    mediante carga de plantilla Excel o ingreso manual.
    """)

    st.sidebar.header("📥 Cargar Modelo desde Excel")
    uploaded_file = st.sidebar.file_uploader(
        "Subir archivo .xlsx / .xls", type=["xlsx", "xls"]
    )

    # Valores por defecto para entradas
    default_company = "Empresa Ejemplo S.A."
    default_scenario = "Base 2026"
    default_revenue = 1000000.0
    default_years = 5
    default_growth = [0.05] * 5
    default_ebit = [0.15] * 5
    default_tax = 0.25
    default_capex = 0.04
    default_nwc = 0.02
    default_da = 0.03
    default_wacc = 0.10
    default_g = 0.025
    default_debt = 200000.0

    # Si el usuario sube un archivo Excel
    if uploaded_file is not None:
        try:
            # Lectura de la pestaña de Parámetros/Supuestos
            df_inputs = pd.read_excel(uploaded_file, sheet_name="Inputs")
            inputs_dict = dict(zip(df_inputs["Parametro"], df_inputs["Valor"]))

            default_company = str(inputs_dict.get("company_name", default_company))
            default_scenario = str(inputs_dict.get("scenario_name", default_scenario))
            default_revenue = float(inputs_dict.get("historical_revenue", default_revenue))
            default_tax = float(inputs_dict.get("tax_rate", default_tax))
            default_capex = float(inputs_dict.get("capex_percent", default_capex))
            default_nwc = float(inputs_dict.get("nwc_percent", default_nwc))
            default_da = float(inputs_dict.get("da_percent", default_da))
            default_wacc = float(inputs_dict.get("wacc", default_wacc))
            default_g = float(inputs_dict.get("terminal_growth_rate", default_g))
            default_debt = float(inputs_dict.get("net_debt", default_debt))

            # Lectura de las Proyecciones Anuales
            df_projs = pd.read_excel(uploaded_file, sheet_name="Projections")
            default_years = len(df_projs)
            default_growth = df_projs["growth_rate"].tolist()
            default_ebit = df_projs["ebit_margin"].tolist()

            st.sidebar.success("✅ Archivo Excel cargado correctamente.")
        except Exception as e:
            st.sidebar.error(f"❌ Error al procesar Excel: {e}")

    # -------------------------------------------------------------------------
    # RENDERIZADO DE INTERFAZ EN SIDEBAR
    # -------------------------------------------------------------------------
    st.sidebar.header("📌 Parámetros Generales")
    company_name = st.sidebar.text_input("Nombre de la Empresa", value=default_company)
    scenario_name = st.sidebar.text_input("Nombre del Escenario", value=default_scenario)

    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Datos Financieros Iniciales")
    historical_revenue = st.sidebar.number_input(
        "Ingresos del Último Año ($)", min_value=0.0, value=default_revenue, step=50000.0, format="%.2f"
    )
    num_years = st.sidebar.slider("Años de Proyección", min_value=3, max_value=10, value=default_years)

    growth_rates = []
    ebit_margins = []
    for i in range(num_years):
        col1, col2 = st.sidebar.columns(2)
        g_val = (default_growth[i] * 100) if i < len(default_growth) else 5.0
        m_val = (default_ebit[i] * 100) if i < len(default_ebit) else 15.0

        g = col1.number_input(f"Año {i+1} Crec. (%)", value=float(g_val), step=0.5, key=f"g_{i}") / 100.0
        m = col2.number_input(f"Año {i+1} EBIT (%)", value=float(m_val), step=0.5, key=f"m_{i}") / 100.0
        growth_rates.append(g)
        ebit_margins.append(m)

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Supuestos Financieros & Tasa de Descuento")
    tax_rate = st.sidebar.number_input("Tasa Impuestos (%)", value=default_tax * 100, step=1.0) / 100.0
    capex_percent = st.sidebar.number_input("CapEx / Ingresos (%)", value=default_capex * 100, step=0.5) / 100.0
    nwc_percent = st.sidebar.number_input("Δ NWC / Ingresos (%)", value=default_nwc * 100, step=0.5) / 100.0
    da_percent = st.sidebar.number_input("D&A / Ingresos (%)", value=default_da * 100, step=0.5) / 100.0
    wacc = st.sidebar.number_input("WACC (%)", value=default_wacc * 100, step=0.5) / 100.0
    terminal_growth_rate = st.sidebar.number_input("Tasa g (%)", value=default_g * 100, step=0.1) / 100.0
    net_debt = st.sidebar.number_input("Deuda Neta ($)", value=default_debt, step=10000.0)

# -----------------------------------------------------------------------------
# MÓDULO 2: MERCADOS & CLASES DE ACTIVOS
# -----------------------------------------------------------------------------
elif module == "📈 Mercados & Clases de Activos":
    st.title("📈 Análisis de Mercados & Clases de Activos Globales")
    st.markdown("""
    Consulta cotizaciones e históricos en tiempo real de **Acciones, Commodities (Oro) e Índices Tecnológicos**, 
    con opción de registrar el *snapshot* actual en la base de datos **TiDB Cloud**.
    """)

    col_m1, col_m2, col_m3 = st.columns(3)

    # Accesos rápidos para activos clave
    with col_m1:
        st.subheader("🟡 Oro (Gold Spot)")
        gold_ticker = yf.Ticker("GC=F")
        gold_info = gold_ticker.fast_info
        gold_price = gold_info.get("lastPrice", 0.0)
        gold_prev = gold_info.get("previousClose", gold_price)
        gold_chg = (
            ((gold_price - gold_prev) / gold_prev * 100) if gold_prev else 0.0
        )
        st.metric(
            "Precio Futuros Oro ($/oz)",
            f"${gold_price:,.2f}",
            f"{gold_chg:+.2f}%",
        )
        if st.button("💾 Guardar Oro en TiDB", key="save_gold"):
            if PortfolioController.save_market_quote(
                "GC=F", "Gold Futures", "Commodity", gold_price, gold_chg
            ):
                st.success("✅ Cotización del Oro guardada en TiDB.")
            else:
                st.error("❌ Error al guardar en TiDB.")

    with col_m2:
        st.subheader("💻 Nasdaq 100 Index")
        nasdaq_ticker = yf.Ticker("^IXIC")
        nasdaq_info = nasdaq_ticker.fast_info
        nasdaq_price = nasdaq_info.get("lastPrice", 0.0)
        nasdaq_prev = nasdaq_info.get("previousClose", nasdaq_price)
        nasdaq_chg = (
            ((nasdaq_price - nasdaq_prev) / nasdaq_prev * 100)
            if nasdaq_prev
            else 0.0
        )
        st.metric(
            "S&P / Nasdaq Composite",
            f"{nasdaq_price:,.2f} pts",
            f"{nasdaq_chg:+.2f}%",
        )
        if st.button("💾 Guardar Nasdaq en TiDB", key="save_nasdaq"):
            if PortfolioController.save_market_quote(
                "^IXIC", "Nasdaq Composite", "Index", nasdaq_price, nasdaq_chg
            ):
                st.success("✅ Cotización de Nasdaq guardada en TiDB.")
            else:
                st.error("❌ Error al guardar en TiDB.")

    with col_m3:
        st.subheader("🍎 Apple Inc. (AAPL)")
        aapl_ticker = yf.Ticker("AAPL")
        aapl_info = aapl_ticker.fast_info
        aapl_price = aapl_info.get("lastPrice", 0.0)
        aapl_prev = aapl_info.get("previousClose", aapl_price)
        aapl_chg = (
            ((aapl_price - aapl_prev) / aapl_prev * 100) if aapl_prev else 0.0
        )
        st.metric("Acción AAPL ($)", f"${aapl_price:,.2f}", f"{aapl_chg:+.2f}%")
        if st.button("💾 Guardar AAPL en TiDB", key="save_aapl"):
            if PortfolioController.save_market_quote(
                "AAPL", "Apple Inc.", "Equity", aapl_price, aapl_chg
            ):
                st.success("✅ Cotización de AAPL guardada en TiDB.")
            else:
                st.error("❌ Error al guardar en TiDB.")

    st.markdown("---")
    st.subheader("🔍 Buscador e Histórico de Activos Financieros")

    symbol = st.text_input(
        "Ingrese el Ticker o Símbolo de Mercado (ej. AAPL, NVDA, TSLA, GC=F,"
        " ^IXIC, BTC-USD):",
        value="NVDA",
    ).upper()
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
                info = asset.fast_info
                curr_price = info.get("lastPrice", 0.0)
                prev_price = info.get("previousClose", curr_price)
                chg_pct = (
                    ((curr_price - prev_price) / prev_price * 100)
                    if prev_price
                    else 0.0
                )

                st.write(f"### Evolución del Precio: **{symbol}**")
                st.line_chart(df_hist["Close"])

                col_sub1, col_sub2 = st.columns([3, 1])
                with col_sub1:
                    st.subheader("📊 Resumen de Datos Históricos")
                    st.dataframe(
                        df_hist[["Open", "High", "Low", "Close", "Volume"]].tail(
                            10
                        ),
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
                    if st.button(f"💾 Guardar {symbol} en TiDB"):
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
                st.warning(
                    f"No se encontraron datos para el símbolo '{symbol}'."
                )
        except Exception as err:
            st.error(f"Error al obtener los datos de mercado: {err}")

    st.markdown("---")
    st.subheader("📋 Historial de Cotizaciones Registradas en TiDB")
    if st.button("🔄 Cargar Cotizaciones de la Base de Datos"):
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
            st.info("No hay cotizaciones guardadas aún en TiDB Cloud.")

# -----------------------------------------------------------------------------
# MÓDULO 3: GESTIÓN DE PORTAFOLIO
# -----------------------------------------------------------------------------
elif module == "💼 Gestión de Portafolio":
    st.title("💼 Módulo de Gestión de Portafolio & Persistencia")
    st.markdown("""
    Crea, administra y consulta tus carteras corporativas e inversiones registradas directamente en **TiDB Cloud / MySQL**.
    """)

    tab1, tab2 = st.tabs(
        ["➕ Crear Portafolio", "📂 Mis Portafolios Guardados"]
    )

    with tab1:
        st.subheader("Crear Nueva Carteria / Portafolio de Inversión")

        p_name = st.text_input(
            "Nombre del Portafolio", value="Portafolio Crecimiento Tech 2026"
        )
        p_desc = st.text_area(
            "Descripción / Estrategia",
            value="Estrategia enfocada en tecnológicas de alta capitalización y cobertura en commodities.",
        )

        st.markdown("---")
        st.write("#### Activos del Portafolio")

        # Inicialización de la sesión para agregar dinámicamente posiciones
        if "temp_assets" not in st.session_state:
            st.session_state.temp_assets = []

        col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)
        with col_a1:
            a_sym = st.text_input("Ticker", value="NVDA").upper()
        with col_a2:
            a_name = st.text_input("Nombre Activo", value="NVIDIA Corp.")
        with col_a3:
            a_type = st.selectbox(
                "Clase de Activo", ["Equity", "Commodity", "Index", "Crypto"]
            )
        with col_a4:
            a_qty = st.number_input("Cantidad", min_value=0.01, value=10.0)
        with col_a5:
            a_price = st.number_input(
                "Precio Compra ($)", min_value=0.01, value=125.50
            )

        a_date = st.date_input("Fecha de Adquisición", value=date.today())

        if st.button("➕ Agregar Activo a la Lista"):
            st.session_state.temp_assets.append({
                "symbol": a_sym,
                "asset_name": a_name,
                "asset_type": a_type,
                "quantity": a_qty,
                "purchase_price": a_price,
                "purchase_date": str(a_date),
            })
            st.success(f"Activo '{a_sym}' agregado a la vista previa.")

        if st.session_state.temp_assets:
            st.write("##### Vista Previa de Activos a Guardar:")
            df_temp = pd.DataFrame(st.session_state.temp_assets)
            st.dataframe(df_temp, use_container_width=True)

            if st.button(
                "💾 Guardar Portafolio Completo en TiDB Cloud", type="primary"
            ):
                if PortfolioController.create_portfolio(
                    p_name, p_desc, st.session_state.temp_assets
                ):
                    st.success(
                        f"✅ Portafolio '{p_name}' guardado exitosamente en TiDB Cloud."
                    )
                    st.session_state.temp_assets = []
                else:
                    st.error("❌ Ocurrió un error al guardar el portafolio.")

    with tab2:
        st.subheader("Consultar Portafolios Almacenados")
        if st.button("🔄 Cargar Lista de Portafolios"):
            portfolios = PortfolioController.get_portfolios()
            if portfolios:
                for p in portfolios:
                    with st.expander(
                        f"📁 **{p['portfolio_name']}** (Creado: {p['created_at']})"
                    ):
                        st.write(f"**Descripción:** {p['description']}")
                        assets = PortfolioController.get_portfolio_assets(
                            p["id"]
                        )
                        if assets:
                            df_assets = pd.DataFrame(assets)
                            st.dataframe(
                                df_assets.style.format({
                                    "quantity": "{:,.2f}",
                                    "purchase_price": "${:,.2f}",
                                }),
                                use_container_width=True,
                            )
                        else:
                            st.info("Este portafolio no contiene activos.")
            else:
                st.info("No se encontraron portafolios en TiDB Cloud.")