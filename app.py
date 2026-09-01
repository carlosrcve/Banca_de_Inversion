# app.py
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
from dcf_controller import DCFController
from dcf_models import DCFInputs

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
    Esta herramienta calcula el **Valor de la Empresa (Enterprise Value)** y el **Valor del Patrimonio (Equity Value)** 
    con persistencia de escenarios en **TiDB Cloud / MySQL**.
    """)

    st.sidebar.header("📌 Parámetros Generales")
    company_name = st.sidebar.text_input(
        "Nombre de la Empresa", value="Empresa Ejemplo S.A."
    )
    scenario_name = st.sidebar.text_input("Nombre del Escenario", value="Base 2026")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Datos Financieros Iniciales")

    historical_revenue = st.sidebar.number_input(
        "Ingresos del Último Año ($)",
        min_value=0.0,
        value=1000000.0,
        step=50000.0,
        format="%.2f",
    )

    num_years = st.sidebar.slider(
        "Años de Proyección", min_value=3, max_value=10, value=5
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Proyecciones Detalladas por Año")

    growth_rates = []
    ebit_margins = []

    cols_years = st.sidebar.columns(2)
    with cols_years[0]:
        st.caption("Crecimiento (%)")
    with cols_years[1]:
        st.caption("Margen EBIT (%)")

    for i in range(num_years):
        col1, col2 = st.sidebar.columns(2)
        with col1:
            g = (
                col1.number_input(
                    f"Año {i+1} Crec.", value=5.0, step=0.5, key=f"g_{i}"
                )
                / 100.0
            )
            growth_rates.append(g)
        with col2:
            m = (
                col2.number_input(
                    f"Año {i+1} EBIT", value=15.0, step=0.5, key=f"m_{i}"
                )
                / 100.0
            )
            ebit_margins.append(m)

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Supuestos Financieros & Tasa de Descuento")

    tax_rate = (
        st.sidebar.number_input("Tasa de Impuestos (%)", value=25.0, step=1.0)
        / 100.0
    )
    capex_percent = (
        st.sidebar.number_input("CapEx / Ingresos (%)", value=4.0, step=0.5) / 100.0
    )
    nwc_percent = (
        st.sidebar.number_input("Δ NWC / Ingresos (%)", value=2.0, step=0.5) / 100.0
    )
    da_percent = (
        st.sidebar.number_input("D&A / Ingresos (%)", value=3.0, step=0.5) / 100.0
    )
    wacc = (
        st.sidebar.number_input(
            "WACC - Costo Promedio del Capital (%)", value=10.0, step=0.5
        )
        / 100.0
    )
    terminal_growth_rate = (
        st.sidebar.number_input(
            "Tasa de Crecimiento Perpetua g (%)", value=2.5, step=0.1
        )
        / 100.0
    )
    net_debt = st.sidebar.number_input(
        "Deuda Neta ($)", value=200000.0, step=10000.0
    )

    try:
        results = DCFController.run_valuation(
            historical_revenue=historical_revenue,
            growth_rates=growth_rates,
            ebit_margins=ebit_margins,
            tax_rate=tax_rate,
            capex_percent=capex_percent,
            nwc_percent=nwc_percent,
            da_percent=da_percent,
            wacc=wacc,
            terminal_growth_rate=terminal_growth_rate,
            net_debt=net_debt,
        )

        current_inputs = DCFInputs(
            historical_revenue=historical_revenue,
            growth_rates=growth_rates,
            ebit_margins=ebit_margins,
            tax_rate=tax_rate,
            capex_percent=capex_percent,
            nwc_percent=nwc_percent,
            da_percent=da_percent,
            wacc=wacc,
            terminal_growth_rate=terminal_growth_rate,
            net_debt=net_debt,
        )

        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("🏢 Enterprise Value (EV)", f"${results.enterprise_value:,.2f}")
        col_res2.metric("💵 Equity Value (Patrimonio)", f"${results.equity_value:,.2f}")
        col_res3.metric("🌐 Valor Presente TV", f"${results.pv_terminal_value:,.2f}")

        st.markdown("---")
        st.subheader("📋 Tabla Proyectada de Flujos de Caja (FCFF)")

        years_labels = [f"Año {i+1}" for i in range(num_years)]
        df_projections = pd.DataFrame({
            "Año": years_labels,
            "Tasa Crec. (%)": [g * 100 for g in growth_rates],
            "Margen EBIT (%)": [m * 100 for m in ebit_margins],
            "Ingresos Proyectados ($)": results.projected_revenues,
            "EBIT ($)": results.projected_ebit,
            "NOPAT ($)": results.projected_nopat,
            "Flujo Caja Libre (FCF) ($)": results.free_cash_flows,
            "PV FCF ($)": results.pv_cash_flows,
        })

        st.dataframe(
            df_projections.style.format({
                "Tasa Crec. (%)": "{:.2f}%",
                "Margen EBIT (%)": "{:.2f}%",
                "Ingresos Proyectados ($)": "${:,.2f}",
                "EBIT ($)": "${:,.2f}",
                "NOPAT ($)": "${:,.2f}",
                "Flujo Caja Libre (FCF) ($)": "${:,.2f}",
                "PV FCF ($)": "${:,.2f}",
            }),
            use_container_width=True,
        )

        st.subheader("Valor Presente de Flujos Proyectados")
        df_chart = pd.DataFrame({
            "Año": years_labels,
            "PV FCF": [float(val) for val in results.pv_cash_flows],
        }).set_index("Año")

        st.bar_chart(df_chart)

        st.markdown("---")
        st.subheader("💾 Guardar y Consultar Valoraciones")

        col_btn, col_history = st.columns([1, 2])

        with col_btn:
            st.write("#### Guardar Escenario Actual")
            if st.button("💾 Guardar en Base de Datos", type="primary"):
                success = DCFController.save_valuation(
                    company_name=company_name,
                    scenario_name=scenario_name,
                    inputs=current_inputs,
                    results=results,
                )
                if success:
                    st.success(
                        f"✅ Escenario '{scenario_name}' guardado exitosamente en TiDB Cloud."
                    )
                else:
                    st.error("❌ Ocurrió un error al intentar guardar en la base de datos.")

        with col_history:
            st.write("#### Escenarios Guardados de la Empresa")
            if st.button("🔄 Consultar Historial"):
                scenarios = DCFController.get_saved_scenarios(company_name)
                if scenarios:
                    df_scenarios = pd.DataFrame(scenarios)
                    st.dataframe(
                        df_scenarios.style.format({
                            "enterprise_value": "${:,.2f}",
                            "equity_value": "${:,.2f}",
                        }),
                        use_container_width=True,
                    )
                else:
                    st.info(f"No se encontraron escenarios registrados para '{company_name}'.")

    except Exception as e:
        st.error(f"Error en los cálculos o en la ejecución: {e}")

# -----------------------------------------------------------------------------
# MÓDULO 2: MERCADOS & CLASES DE ACTIVOS
# -----------------------------------------------------------------------------
elif module == "📈 Mercados & Clases de Activos":
    st.title("📈 Análisis de Mercados & Clases de Activos Globales")
    st.markdown("""
    Consulta cotizaciones e históricos en tiempo real de **Acciones, Commodities (Oro) e Índices Tecnológicos**.
    """)

    col_m1, col_m2, col_m3 = st.columns(3)

    # Accesos rápidos para activos clave
    with col_m1:
        st.subheader("🟡 Oro (Gold Spot)")
        gold_ticker = yf.Ticker("GC=F")
        gold_info = gold_ticker.fast_info
        gold_price = gold_info.get("lastPrice", 0.0)
        gold_prev = gold_info.get("previousClose", gold_price)
        gold_chg = ((gold_price - gold_prev) / gold_prev * 100) if gold_prev else 0.0
        st.metric("Precio Futuros Oro ($/oz)", f"${gold_price:,.2f}", f"{gold_chg:+.2f}%")

    with col_m2:
        st.subheader("💻 Nasdaq 100 Index")
        nasdaq_ticker = yf.Ticker("^IXIC")
        nasdaq_info = nasdaq_ticker.fast_info
        nasdaq_price = nasdaq_info.get("lastPrice", 0.0)
        nasdaq_prev = nasdaq_info.get("previousClose", nasdaq_price)
        nasdaq_chg = ((nasdaq_price - nasdaq_prev) / nasdaq_prev * 100) if nasdaq_prev else 0.0
        st.metric("S&P / Nasdaq Composite", f"{nasdaq_price:,.2f} pts", f"{nasdaq_chg:+.2f}%")

    with col_m3:
        st.subheader("🍎 Apple Inc. (AAPL)")
        aapl_ticker = yf.Ticker("AAPL")
        aapl_info = aapl_ticker.fast_info
        aapl_price = aapl_info.get("lastPrice", 0.0)
        aapl_prev = aapl_info.get("previousClose", aapl_price)
        aapl_chg = ((aapl_price - aapl_prev) / aapl_prev * 100) if aapl_prev else 0.0
        st.metric("Acción AAPL ($)", f"${aapl_price:,.2f}", f"{aapl_chg:+.2f}%")

    st.markdown("---")
    st.subheader("🔍 Buscador e Histórico de Activos Financieros")

    symbol = st.text_input("Ingrese el Ticker o Símbolo de Mercado (ej. AAPL, NVDA, TSLA, GC=F, ^IXIC, BTC-USD):", value="NVDA").upper()
    period = st.selectbox("Rango de Tiempo", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3)

    if symbol:
        try:
            asset = yf.Ticker(symbol)
            df_hist = asset.history(period=period)

            if not df_hist.empty:
                st.write(f"### Evolución del Precio: **{symbol}**")
                st.line_chart(df_hist["Close"])

                st.subheader("📊 Resumen de Datos Históricos")
                st.dataframe(df_hist[["Open", "High", "Low", "Close", "Volume"]].tail(10), use_container_width=True)
            else:
                st.warning(f"No se encontraron datos para el símbolo '{symbol}'.")
        except Exception as err:
            st.error(f"Error al obtener los datos de mercado: {err}")

# -----------------------------------------------------------------------------
# MÓDULO 3: GESTIÓN DE PORTAFOLIO
# -----------------------------------------------------------------------------
elif module == "💼 Gestión de Portafolio":
    st.title("💼 Módulo de Gestión de Portafolio & Optimización")
    st.markdown("""
    Próximamente: Asignación eficiente de capital, frontera eficiente de Markowitz y cálculo del Ratio de Sharpe para carteras corporativas.
    """)
    st.info("💡 Este módulo permitirá construir y simular portafolios de inversión conectados a TiDB Cloud.")