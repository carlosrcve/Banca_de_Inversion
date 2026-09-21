# mod_dealroom.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def render():
    st.title("🏛️ M&A & Deal Room")
    st.markdown("Plataforma corporativa para transacciones de M&A, Virtual Data Room (VDR), Modelado DCF y Sindicación de Capital.")

    # Pestañas principales del módulo
    tab1, tab2, tab3 = st.tabs([
        "🔐 Virtual Data Room (VDR)", 
        "📊 Modelado Financiero & DCF", 
        "🤝 Sindicación de Capital"
    ])

    # ==========================================
    # PESTAÑA 1: VIRTUAL DATA ROOM (VDR)
    # ==========================================
    with tab1:
        st.subheader("Virtual Data Room Seguro (VDR)")
        st.markdown("Repositorio cifrado con bitácoras de auditoría para debida diligencia (*Due Diligence*).")

        col_vdr1, col_vdr2 = st.columns([2, 1])

        with col_vdr1:
            st.markdown("### 📁 Repositorio de Transacción")
            
            # Simulador de archivos en el Data Room
            vdr_files = pd.DataFrame([
                {"Carpeta": "01. Estados Financieros Audita2", "Archivo": "Balance_General_2025_Auditado.pdf", "Clasificación": "Confidencial", "Fecha Carga": "2026-08-15", "Descargas": 14},
                {"Carpeta": "01. Estados Financieros Audita2", "Archivo": "Flujo_Caja_Proyectado_5Y.xlsx", "Clasificación": "Strictly Confidential", "Fecha Carga": "2026-09-01", "Descargas": 22},
                {"Carpeta": "02. Legal y Corporativo", "Archivo": "Estatutos_Sociales_Aktivos.pdf", "Clasificación": "Restringido", "Fecha Carga": "2026-07-10", "Descargas": 8},
                {"Carpeta": "03. Impuestos y Fiscal", "Archivo": "Declaraciones_ISLR_IVA_2024_2025.pdf", "Clasificación": "Confidencial", "Fecha Carga": "2026-08-20", "Descargas": 11},
                {"Carpeta": "04. Operaciones y Contratos", "Archivo": "Contratos_Clientes_Clave_2026.pdf", "Clasificación": "Data Room Restringido", "Fecha Carga": "2026-09-05", "Descargas": 5}
            ])
            
            st.dataframe(vdr_files, use_container_width=True)

            selected_file = st.selectbox("Seleccionar documento para auditar / descargar vista previa:", vdr_files["Archivo"].tolist())
            if st.button("📥 Solicitar Acceso / Descarga Segura"):
                st.success(f"Acceso concedido y registrado en la bitácora para: **{selected_file}** [IP: 192.168.1.50 - Hash: SHA256-9f8e7]")

        with col_vdr2:
            st.markdown("### 📋 Bitácora de Auditoría")
            audit_log = pd.DataFrame([
                {"Inversor / Fondo": "BlackRock PE", "Acción": "Descarga Excel DCF", "Timestamp": "2026-09-20 18:42"},
                {"Inversor / Fondo": "Vanguard Growth", "Acción": "Visualizó Balance", "Timestamp": "2026-09-20 17:15"},
                {"Inversor / Fondo": "Angel Syndicate A", "Acción": "Acceso VDR Concedido", "Timestamp": "2026-09-19 11:30"}
            ])
            st.dataframe(audit_log, use_container_width=True)
            st.info("🔐 Todo el tráfico y visualización de documentos se encuentra bajo cifrado de extremo a extremo y marca de agua dinámica.")

    # ==========================================
    # PESTAÑA 2: MODELADO FINANCIERO Y DCF
    # ==========================================
    with tab2:
        st.subheader("Valoración por Flujo de Caja Descontado (DCF) & M&A")
        st.markdown("Herramienta analítica para proyectar flujos y determinar el Valor Presente Neto (VPN / NPV) corporativo.")

        col_dcf1, col_dcf2 = st.columns(2)

        with col_dcf1:
            st.markdown("#### ⚙️ Supuestos del Modelo")
            rev_base = st.number_input("Ingresos Base Año 0 ($)", value=10000000.0, step=500000.0)
            growth_rate = st.slider("Tasa de Crecimiento Anual Estimada (%)", 0.0, 30.0, 10.0) / 100.0
            ebitda_margin = st.slider("Margen EBITDA Promedio (%)", 10.0, 60.0, 30.0) / 100.0
            tax_rate = st.slider("Tasa impositiva (ISLR) (%)", 0.0, 50.0, 34.0) / 100.0
            wacc = st.slider("WACC (Tasa de Descuento) (%)", 5.0, 25.0, 12.0) / 100.0
            terminal_growth = st.slider("Tasa de Crecimiento Terminal (g) (%)", 0.0, 5.0, 2.0) / 100.0

        with col_dcf2:
            st.markdown("#### 📈 Proyección a 5 Años")
            years = [f"Año {i}" for i in range(1, 6)]
            revenues = [rev_base * ((1 + growth_rate) ** i) for i in range(1, 6)]
            ebitdas = [rev * ebitda_margin for rev in revenues]
            nopat = [ebit * (1 - tax_rate) for ebit in ebitdas]
            
            # Cálculo de descuento de flujos
            discount_factors = [1 / ((1 + wacc) ** i) for i in range(1, 6)]
            pv_fcf = [nopat[i] * discount_factors[i] for i in range(5)]
            
            sum_pv_fcf = sum(pv_fcf)
            terminal_value = (nopat[-1] * (1 + terminal_growth)) / (wacc - terminal_growth)
            pv_terminal_value = terminal_value * discount_factors[-1]
            enterprise_value = sum_pv_fcf + pv_terminal_value

            dcf_summary = pd.DataFrame({
                "Métrica": ["VPN Flujos Explicitos", "Valor Terminal (PV)", "Enterprise Value (EV) Estimado"],
                "Valor ($)": [f"${sum_pv_fcf:,.2f}", f"${pv_terminal_value:,.2f}", f"${enterprise_value:,.2f}"]
            })
            st.dataframe(dcf_summary, use_container_width=True)
            
            st.metric("Enterprise Value (EV) Total", f"${enterprise_value:,.2f}", delta="Valuación Central M&A")

        # Gráfico de Proyecciones
        chart_df = pd.DataFrame({
            "Año": years,
            "Ingresos": revenues,
            "EBITDA": ebitdas,
            "NOPAT": nopat
        })
        fig = px.bar(chart_df, x="Año", y=["Ingresos", "EBITDA", "NOPAT"], barmode="group", title="Proyección Financiera Plurianual (USD)")
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # PESTAÑA 3: SINDICACIÓN DE CAPITAL
    # ==========================================
    with tab3:
        st.subheader("Panel de Sindicación de Capital (Deal Tranches)")
        st.markdown("Coordinación de inversores ángeles, fondos de Private Equity y socios estratégicos en el deal corporativo.")

        col_sind1, col_sind2 = st.columns(2)

        with col_sind1:
            st.markdown("#### 💰 Configuración del Tranche")
            target_raise = st.number_input("Meta de Levantamiento de Capital ($)", value=5000000.0, step=500000.0)
            valuation_cap = st.number_input("Valuación Pre-Money ($)", value=20000000.0, step=1000000.0)
            
            st.markdown("#### Registrar Participante en el Sindicato")
            investor_name = st.text_input("Nombre del Fondo / Inversor", "Alpha Centauri Capital PE")
            investor_type = st.selectbox("Tipo de Inversor", ["Private Equity", "Venture Capital", "Family Office", "Inversor Ángel"])
            ticket_size = st.number_input("Monto Comprometido ($)", value=1500000.0, step=100000.0)
            
            if "syndicate_investors" not in st.session_state:
                st.session_state.syndicate_investors = [
                    {"Inversor": "Gylfi Holdings Corp", "Tipo": "Socio Estratégico", "Monto ($)": 2000000.0, "Stake (%)": 40.0},
                    {"Inversor": "Andes Venture Fund", "Tipo": "Venture Capital", "Monto ($)": 1500000.0, "Stake (%)": 30.0}
                ]

            if st.button("➕ Agregar Inversor al Sindicato"):
                stake_pct = (ticket_size / target_raise) * 100
                st.session_state.syndicate_investors.append({
                    "Inversor": investor_name,
                    "Tipo": investor_type,
                    "Monto ($)": ticket_size,
                    "Stake (%)": round(stake_pct, 2)
                })
                st.success(f"Inversor {investor_name} agregado exitosamente.")

        with col_sind2:
            st.markdown("#### 📊 Cap Table del Sindicato")
            syndicate_df = pd.DataFrame(st.session_state.syndicate_investors)
            st.dataframe(syndicate_df, use_container_width=True)

            total_committed = syndicate_df["Monto ($)"].sum()
            progress = min(total_committed / target_raise, 1.0)
            
            st.metric("Total Comprometido", f"${total_committed:,.2f}", f"{progress*100:.1f}% de la Meta")
            st.progress(progress)

            if total_committed >= target_raise:
                st.success("🎉 ¡Meta de sindicación alcanzada! El Deal Room está listo para proceder con el cierre notariado.")
            else:
                st.warning(f"Faltan ${target_raise - total_committed:,.2f} para completar el tranche de inversión.")