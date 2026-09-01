# app.py
from dcf_controller import DCFController
from dcf_models import DCFInputs
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Modelo de Valoración DCF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📊 Modelo de Valoración por Flujo de Caja Descontado (DCF)")
st.markdown("""
Esta aplicación permite calcular el **Valor de la Empresa (Enterprise Value)** y el **Valor del Patrimonio (Equity Value)** 
utilizando el método DCF, con soporte de persistencia en **TiDB Cloud / MySQL**.
""")

# -----------------------------------------------------------------------------
# 2. PANEL LATERAL (ENTRADAS DE DATOS Y CONFIGURACIÓN)
# -----------------------------------------------------------------------------
st.sidebar.header("📌 Parámetros Generales")

# Información de Empresa y Escenario
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

# Creación de pestañas o inputs dinámicos por cada año proyectado
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

# -----------------------------------------------------------------------------
# 3. EJECUCIÓN DEL CÁLCULO DCF
# -----------------------------------------------------------------------------
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

  # Reconstrucción de inputs para guardado posterior
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

  # -------------------------------------------------------------------------
  # 4. PRESENTACIÓN DE RESULTADOS
  # -------------------------------------------------------------------------
  col_res1, col_res2, col_res3 = st.columns(3)
  col_res1.metric(
      label="🏢 Enterprise Value (EV)",
      value=f"${results.enterprise_value:,.2f}",
  )
  col_res2.metric(
      label="💵 Equity Value (Patrimonio)",
      value=f"${results.equity_value:,.2f}",
  )
  col_res3.metric(
      label="🌐 Valor Terminal Presente (PV TV)",
      value=f"${results.pv_terminal_value:,.2f}",
  )

  st.markdown("---")
  st.subheader("📋 Tabla Proyectada de Flujos de Caja (FCFF)")

  # Creación de DataFrame con los detalles por año
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

  # -------------------------------------------------------------------------
  # Gráficos interactivos adaptativos con Altair
  # -------------------------------------------------------------------------
  st.subheader("📈 Evolución del Flujo de Caja Libre Proyectado")

  # DataFrame en formato largo optimizado para Altair
  df_chart = pd.DataFrame({
      "Año": years_labels * 2,
      "Monto": [float(val) for val in results.free_cash_flows]
      + [float(val) for val in results.pv_cash_flows],
      "Métrica": ["Flujo Caja Libre (FCF) ($)"] * num_years
      + ["PV FCF ($)"] * num_years,
  })

  # Construcción del gráfico de líneas con puntos y escala dinámica en eje Y
  chart = (
      alt.Chart(df_chart)
      .mark_line(point=True)
      .encode(
          x=alt.X("Año:N", sort=years_labels, title="Año de Proyección"),
          y=alt.Y("Monto:Q", scale=alt.Scale(zero=False), title="Monto ($)"),
          color=alt.Color("Métrica:N", title="Métrica"),
          tooltip=["Año", "Métrica", alt.Tooltip("Monto:Q", format="$,.2f")],
      )
      .properties(height=380)
  )

  st.altair_chart(chart, use_container_width=True)

  # -------------------------------------------------------------------------
  # 5. PERSISTENCIA EN TIDB CLOUD / MYSQL
  # -------------------------------------------------------------------------
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
            f"✅ Escenario '{scenario_name}' guardado exitosamente en TiDB"
            " Cloud."
        )
      else:
        st.error(
            "❌ Ocurrió un error al intentar guardar en la base de datos."
        )

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
        st.info(
            f"No se encontraron escenarios registrados para '{company_name}'."
        )

except Exception as e:
  st.error(f"Error en los cálculos o en la ejecución: {e}")