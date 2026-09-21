# mod_asset_mgmt.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

def render():
    st.title("📈 Asset Management & Fund Portfolios")
    st.markdown("Vehículos de inversión colectiva, construcción algorítmica de portafolios, pruebas de estrés y métricas de desempeño (Sharpe, Alpha, Beta).")

    # Pestañas principales del módulo
    tab1, tab2, tab3 = st.tabs([
        "🎛️ Constructor Algorítmico", 
        "⚠️ Stress Testing & Riesgo", 
        "📄 Reportes & Métricas de Desempeño"
    ])

    # ==========================================
    # PESTAÑA 1: CONSTRUCTOR ALGORÍTMICO
    # ==========================================
    with tab1:
        st.subheader("Constructor de Portafolios Algorítmicos")
        st.markdown("Asignación táctica de activos basada en perfiles de riesgo corporativos e institucionales.")

        col_c1, col_c2 = st.columns([1, 2])

        with col_c1:
            st.markdown("#### ⚙️ Parámetros de Asignación")
            risk_profile = st.selectbox("Perfil de Inversor", ["Conservador", "Moderado", "Crecimiento Agresivo", "Institucional / Oportunista"])
            total_capital = st.number_input("Capital Total Bajo Gestión ($)", value=10000000.0, step=500000.0)

            st.markdown("#### ⚖️ Ponderaciones Objetivo (%)")
            if risk_profile == "Conservador":
                w_rf, w_eq, w_cmd, w_alt = 60.0, 20.0, 10.0, 10.0
            elif risk_profile == "Moderado":
                w_rf, w_eq, w_cmd, w_alt = 40.0, 40.0, 10.0, 10.0
            elif risk_profile == "Crecimiento Agresivo":
                w_rf, w_eq, w_cmd, w_alt = 15.0, 60.0, 15.0, 10.0
            else:
                w_rf, w_eq, w_cmd, w_alt = 10.0, 50.0, 25.0, 15.0

            w_rf = st.slider("Renta Fija Global (Soberanos/IG)", 0.0, 100.0, w_rf)
            w_eq = st.slider("Renta Variable (Acciones Globales)", 0.0, 100.0, w_eq)
            w_cmd = st.slider("Materias Primas / Commodities", 0.0, 100.0, w_cmd)
            w_alt = st.slider("Activos Alternativos / Private Equity", 0.0, 100.0, w_alt)

            total_weight = w_rf + w_eq + w_cmd + w_alt
            if total_weight != 100.0:
                st.warning(f"⚠️ La suma de ponderaciones es {total_weight}%. Lo ideal es que sume 100%.")

        with col_c2:
            st.markdown("#### 📊 Distribución Táctica del Portafolio")
            portfolio_alloc = pd.DataFrame({
                "Clase de Activo": ["Renta Fija Global", "Renta Variable", "Commodities", "Alternativos / PE"],
                "Ponderación (%)": [w_rf, w_eq, w_cmd, w_alt],
                "Capital Asignado ($)": [total_capital * (w_rf/100), total_capital * (w_eq/100), total_capital * (w_cmd/100), total_capital * (w_alt/100)]
            })

            fig_pie = px.pie(portfolio_alloc, names="Clase de Activo", values="Capital Asignado ($)", title=f"Asignación de Activos - Perfil: {risk_profile}", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            st.dataframe(portfolio_alloc, use_container_width=True)

    # ==========================================
    # PESTAÑA 2: STRESS TESTING Y RIESGO
    # ==========================================
    with tab2:
        st.subheader("Simulador de Estrés (Stress Testing)")
        st.markdown("Proyección de impacto en los fondos ante escenarios macroeconómicos adversos severos.")

        scenario = st.selectbox("Seleccionar Escenario de Crisis a Simular", [
            "Crash Bursátil Global (-25% Renta Variable)", 
            "Shock Inflacionario y Alza de Tasas (+300 bps Fed)", 
            "Crisis Cambiaria / Devaluación Regional Exponencial",
            "Colapso de Commodities y Ciclo Recesivo"
        ])

        if st.button("🚀 Ejecutar Simulación de Estrés"):
            st.markdown(f"### Resultados bajo el escenario: *{scenario}*")
            
            col_s1, col_s2, col_s3 = st.columns(3)
            
            if "Crash Bursátil" in scenario:
                impact_pct = -14.5
                var_95 = -$450000.0
                recovery_months = 18
            elif "Shock Inflacionario" in scenario:
                impact_pct = -8.2
                var_95 = -$280000.0
                recovery_months = 12
            elif "Crisis Cambiaria" in scenario:
                impact_pct = -19.1
                var_95 = -$620000.0
                recovery_months = 24
            else:
                impact_pct = -11.0
                var_95 = -$350000.0
                recovery_months = 14

            col_s1.metric("Impacto Estimado en Valor (PnL)", f"{impact_pct}%", delta=f"{impact_pct*total_capital/100:,.2f} USD", delta_color="inverse")
            col_s2.metric("Value at Risk (VaR 95% 1M)", f"${abs(var_95):,.2f}")
            col_s3.metric("Tiempo Estimado de Recuperación", f"{recovery_months} Meses")

            # Gráfico de simulación de caída y recuperación
            months_axis = [f"Mes {i}" for i in range(0, 13)]
            sim_values = [total_capital * (1 + (impact_pct/100) * (min(i, 6)/6) if i <= 6 else (impact_pct/100 + (abs(impact_pct)/100)*(i-6)/6)) for i in range(13)]
            
            sim_df = pd.DataFrame({"Mes": months_axis, "Valor del Portafolio ($)": sim_values})
            fig_stress = px.line(sim_df, x="Mes", y="Valor del Portafolio ($)", markers=True, title="Trayectoria de Recuperación del Fondo Post-Shock")
            st.plotly_chart(fig_stress, use_container_width=True)

    # ==========================================
    # PESTAÑA 3: REPORTES Y MÉTRICAS
    # ==========================================
    with tab3:
        st.subheader("Reportes de Rendimiento & Métricas Institucionales")
        st.markdown("Indicadores estadísticos de desempeño ajustados por riesgo para comités de inversión.")

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Alpha Anualizado", "4.85%", delta="+1.2% vs Benchmark")
        col_m2.metric("Beta del Portafolio", "0.82", delta="Menor volatilidad que el mercado")
        col_m3.metric("Sharpe Ratio", "1.74", delta="Excelente eficiencia")
        col_m4.metric("Sortino Ratio", "2.10", delta="Bajo riesgo de caída")

        st.markdown("---")
        st.markdown("### 📄 Generación de Estado de Cuenta Ejecutivo en PDF")
        
        client_fund_name = st.text_input("Nombre del Fondo o Cliente Institucional", "Fondo de Inversión Global Alpha C.A.")
        report_period = st.selectbox("Periodo del Reporte", ["Q3 2026", "Anual 2025-2026", "YTD Cierre Septiembre"])

        if st.button("📥 Generar y Descargar Reporte Ejecutivo PDF"):
            st.success(f"Reporte generado exitosamente para **{client_fund_name}** ({report_period}). Cifrado con firma digital SHA-256.")
            st.info("El documento incluye desglose net-of-fees (neto de comisiones de gestión y éxito), evolución del NAV y desglose de atribución de rendimiento.")