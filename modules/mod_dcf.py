#mod_dcf.py
import re
import unicodedata
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

# Importaciones del módulo controller
from dcf_controller import DCFController, get_sqlalchemy_engine
from dcf_models import DCFInputs


def clean_column_name(col_name: str) -> str:
    """Limpia acentos, caracteres especiales y espacios para nombres SQL válidos."""
    col = str(col_name).strip()
    col = unicodedata.normalize("NFKD", col).encode("ASCII", "ignore").decode("utf-8")
    col = re.sub(r"[^a-zA-Z0-9]+", "_", col)
    col = re.sub(r"_+", "_", col).strip("_").lower()
    return col if col else "columna_sin_nombre"


def render():
    st.title("📊 Modelo de Valoración por Flujo de Caja Descontado (DCF)")

    # -------------------------------------------------------------------------
    # VARIABLES DE ESTADO Y VALORES POR DEFECTO
    # -------------------------------------------------------------------------
    if "df_excel_inputs" not in st.session_state:
        st.session_state.df_excel_inputs = None
    if "df_excel_projs" not in st.session_state:
        st.session_state.df_excel_projs = None

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

    # Pestañas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📥 1. Cargar Excel", 
        "📊 2. Resultados & FCFF", 
        "📈 3. Gráficos & Análisis", 
        "💾 4. Base de Datos / Historial"
    ])

    # =========================================================================
    # PESTAÑA 1: CARGA DE EXCEL
    # =========================================================================
    with tab1:
        st.header("📥 Cargar Modelo desde Excel")
        uploaded_file = st.file_uploader("Subir archivo .xlsx / .xls", type=["xlsx", "xls"], key="excel_uploader_main")

        if uploaded_file is not None:
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                sheet_names = excel_file.sheet_names
                inputs_sheet = "Inputs" if "Inputs" in sheet_names else sheet_names[0]

                df_inputs = pd.read_excel(excel_file, sheet_name=inputs_sheet)
                if str(df_inputs.columns[0]).startswith("Unnamed"):
                    df_inputs = pd.read_excel(excel_file, sheet_name=inputs_sheet, header=1)

                df_inputs = df_inputs.dropna(how="all")

                param_col = next((c for c in df_inputs.columns if clean_column_name(c) in ["parametro", "parametros", "variable", "concept", "concepto", "key"]), df_inputs.columns[0])
                val_col = next((c for c in df_inputs.columns if clean_column_name(c) in ["valor", "valores", "value", "monto", "monto_mensual"]), df_inputs.columns[1] if len(df_inputs.columns) > 1 else df_inputs.columns[0])

                inputs_dict = dict(zip(df_inputs[param_col].astype(str).str.strip(), df_inputs[val_col]))

                # Guardar en session_state
                st.session_state["company_name"] = str(inputs_dict.get("company_name", default_company))
                st.session_state["scenario_name"] = str(inputs_dict.get("scenario_name", default_scenario))
                st.session_state["historical_revenue"] = float(inputs_dict.get("historical_revenue", default_revenue))
                st.session_state["tax_rate"] = float(inputs_dict.get("tax_rate", default_tax))
                st.session_state["capex_percent"] = float(inputs_dict.get("capex_percent", default_capex))
                st.session_state["nwc_percent"] = float(inputs_dict.get("nwc_percent", default_nwc))
                st.session_state["da_percent"] = float(inputs_dict.get("da_percent", default_da))
                st.session_state["wacc"] = float(inputs_dict.get("wacc", default_wacc))
                st.session_state["terminal_growth_rate"] = float(inputs_dict.get("terminal_growth_rate", default_g))
                st.session_state["net_debt"] = float(inputs_dict.get("net_debt", default_debt))

                proj_sheet = "Projections" if "Projections" in sheet_names else (sheet_names[1] if len(sheet_names) > 1 else sheet_names[0])
                df_projs = pd.read_excel(excel_file, sheet_name=proj_sheet)
                if str(df_projs.columns[0]).startswith("Unnamed"):
                    df_projs = pd.read_excel(excel_file, sheet_name=proj_sheet, header=1)

                df_projs = df_projs.dropna(how="all")
                df_projs.columns = [clean_column_name(col) for col in df_projs.columns]

                if "growth_rate" in df_projs.columns and "ebit_margin" in df_projs.columns:
                    st.session_state["proj_years"] = len(df_projs)
                    st.session_state["growth_rates"] = [float(x) for x in df_projs["growth_rate"].tolist()]
                    st.session_state["ebit_margins"] = [float(x) for x in df_projs["ebit_margin"].tolist()]

                st.session_state.df_excel_inputs = df_inputs
                st.session_state.df_excel_projs = df_projs
                st.success(f"✅ Archivo cargado correctamente ({inputs_sheet} / {proj_sheet})")

            except Exception as e:
                st.error(f"❌ Error al procesar Excel: {e}")

        if st.session_state.get("df_excel_inputs") is not None or st.session_state.get("df_excel_projs") is not None:
            st.markdown("---")
            # En Tab 1: Al hacer click en "Insertar Data Cruda de Excel en MySQL"
            if st.button("💾 Insertar Data Cruda de Excel en MySQL", type="primary"):
                try:
                    engine = get_sqlalchemy_engine()

                    if st.session_state.df_excel_projs is not None:
                        df_proj = st.session_state.df_excel_projs.copy()
                        
                        # Normalizar columnas del DataFrame subido antes de guardar
                        # Asumiendo que las dos primeras columnas del Excel son Tasa Crecimiento y Margen EBIT
                        df_proj.columns = [str(c).strip().lower() for c in df_proj.columns]
                        
                        # Mapear explícitamente a las columnas esperadas por la DB
                        df_to_save = pd.DataFrame()
                        df_to_save["company_name"] = [company_name] * len(df_proj)
                        df_to_save["scenario_name"] = [scenario_name] * len(df_proj)
                        df_to_save["year"] = range(1, len(df_proj) + 1)
                        
                        # Asignar valores buscando por posición o nombre
                        col_g = next((c for c in df_proj.columns if "growth" in c or "crec" in c), df_proj.columns[0])
                        col_m = next((c for c in df_proj.columns if "ebit" in c or "marg" in c), df_proj.columns[1] if len(df_proj.columns) > 1 else df_proj.columns[0])
                        
                        df_to_save["growth_rate"] = df_proj[col_g]
                        df_to_save["ebit_margin"] = df_proj[col_m]

                        # Reemplazar los datos viejos de ese escenario para limpiar la estructura errónea
                        df_to_save.to_sql("excel_projections_raw", con=engine, if_exists="append", index=False)
                        st.success("✅ ¡Proyecciones guardadas con la estructura correcta en MySQL!")

                except Exception as err:
                    st.error(f"❌ Error al guardar en MySQL: {err}")

    # -------------------------------------------------------------------------
    # CONTROLES SIDEBAR
    # -------------------------------------------------------------------------
    st.sidebar.header("📌 Parámetros Generales")
    company_name = st.sidebar.text_input("Nombre de la Empresa", value=st.session_state.get("company_name", default_company))
    scenario_name = st.sidebar.text_input("Nombre del Escenario", value=st.session_state.get("scenario_name", default_scenario))

    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Datos Financieros Iniciales")
    historical_revenue = st.sidebar.number_input("Ingresos del Último Año ($)", min_value=0.0, value=st.session_state.get("historical_revenue", default_revenue), step=50000.0, format="%.2f")
    num_years = st.sidebar.slider("Años de Proyección", min_value=3, max_value=10, value=st.session_state.get("proj_years", default_years))

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Proyecciones Detalladas por Año")

    growth_rates, ebit_margins = [], []
    saved_growth = st.session_state.get("growth_rates", default_growth)
    saved_ebit = st.session_state.get("ebit_margins", default_ebit)

    for i in range(num_years):
        col1, col2 = st.sidebar.columns(2)
        g_val = (saved_growth[i] * 100) if i < len(saved_growth) else 5.0
        m_val = (saved_ebit[i] * 100) if i < len(saved_ebit) else 15.0

        with col1:
            g = col1.number_input(f"Año {i+1} Crec.", value=float(g_val), step=0.5, key=f"g_{i}") / 100.0
            growth_rates.append(g)
        with col2:
            m = col2.number_input(f"Año {i+1} EBIT", value=float(m_val), step=0.5, key=f"m_{i}") / 100.0
            ebit_margins.append(m)

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Supuestos Financieros & Tasa de Descuento")
    tax_rate = st.sidebar.number_input("Tasa de Impuestos (%)", value=st.session_state.get("tax_rate", default_tax) * 100, step=1.0) / 100.0
    capex_percent = st.sidebar.number_input("CapEx / Ingresos (%)", value=st.session_state.get("capex_percent", default_capex) * 100, step=0.5) / 100.0
    nwc_percent = st.sidebar.number_input("Δ NWC / Ingresos (%)", value=st.session_state.get("nwc_percent", default_nwc) * 100, step=0.5) / 100.0
    da_percent = st.sidebar.number_input("D&A / Ingresos (%)", value=st.session_state.get("da_percent", default_da) * 100, step=0.5) / 100.0
    wacc = st.sidebar.number_input("WACC (%)", value=st.session_state.get("wacc", default_wacc) * 100, step=0.5) / 100.0
    terminal_growth_rate = st.sidebar.number_input("Tasa g (%)", value=st.session_state.get("terminal_growth_rate", default_g) * 100, step=0.1) / 100.0
    net_debt = st.sidebar.number_input("Deuda Neta ($)", value=st.session_state.get("net_debt", default_debt), step=10000.0)

    # -------------------------------------------------------------------------
    # EJECUCIÓN Y TABLAS
    # -------------------------------------------------------------------------
    try:
        current_inputs = DCFInputs(
            historical_revenue=historical_revenue, growth_rates=growth_rates, ebit_margins=ebit_margins,
            tax_rate=tax_rate, capex_percent=capex_percent, nwc_percent=nwc_percent, da_percent=da_percent,
            wacc=wacc, terminal_growth_rate=terminal_growth_rate, net_debt=net_debt
        )

        results = DCFController.run_valuation(
            historical_revenue=historical_revenue, growth_rates=growth_rates, ebit_margins=ebit_margins,
            tax_rate=tax_rate, capex_percent=capex_percent, nwc_percent=nwc_percent, da_percent=da_percent,
            wacc=wacc, terminal_growth_rate=terminal_growth_rate, net_debt=net_debt
        )

        # TAB 2
        with tab2:
            st.header("📊 Resultados de Valoración (Leídos desde MySQL)")

            try:
                engine = get_sqlalchemy_engine()

                # 1. Consultar Inputs exactamente como los definiste en tu CREATE TABLE
                query_inputs = """
                    SELECT Parametro, Valor 
                    FROM excel_inputs_raw 
                    WHERE company_name = %s AND scenario_name = %s
                    ORDER BY id ASC
                """
                df_db_inputs = pd.read_sql(query_inputs, con=engine, params=(company_name, scenario_name))

                # 2. Consultar Proyecciones
                query_projs = """
                    SELECT year, growth_rate, ebit_margin 
                    FROM excel_projections_raw 
                    WHERE company_name = %s AND scenario_name = %s
                    ORDER BY year ASC
                """
                df_db_projs = pd.read_sql(query_projs, con=engine, params=(company_name, scenario_name))

                if not df_db_inputs.empty and not df_db_projs.empty:
                    # Diccionario de Inputs
                    inputs_dict = dict(zip(
                        df_db_inputs["Parametro"].astype(str).str.strip().str.lower(), 
                        df_db_inputs["Valor"]
                    ))

                    db_historical_revenue = float(inputs_dict.get("historical_revenue", historical_revenue))
                    db_tax_rate = float(inputs_dict.get("tax_rate", tax_rate))
                    db_capex = float(inputs_dict.get("capex_percent", capex_percent))
                    db_nwc = float(inputs_dict.get("nwc_percent", nwc_percent))
                    db_da = float(inputs_dict.get("da_percent", da_percent))
                    db_wacc = float(inputs_dict.get("wacc", wacc))
                    db_g = float(inputs_dict.get("terminal_growth_rate", terminal_growth_rate))
                    db_debt = float(inputs_dict.get("net_debt", net_debt))

                    db_growth_rates = [float(x) for x in df_db_projs["growth_rate"].tolist()]
                    db_ebit_margins = [float(x) for x in df_db_projs["ebit_margin"].tolist()]

                    # Ejecutar modelo DCF
                    results_db = DCFController.run_valuation(
                        historical_revenue=db_historical_revenue,
                        growth_rates=db_growth_rates,
                        ebit_margins=db_ebit_margins,
                        tax_rate=db_tax_rate,
                        capex_percent=db_capex,
                        nwc_percent=db_nwc,
                        da_percent=db_da,
                        wacc=db_wacc,
                        terminal_growth_rate=db_g,
                        net_debt=db_debt
                    )

                    # Desplegar métricas
                    col_res1, col_res2, col_res3 = st.columns(3)
                    col_res1.metric("🏢 Enterprise Value (EV)", f"${results_db.enterprise_value:,.2f}")
                    col_res2.metric("💵 Equity Value (Patrimonio)", f"${results_db.equity_value:,.2f}")
                    col_res3.metric("🌐 Valor Presente TV", f"${results_db.pv_terminal_value:,.2f}")

                    st.markdown("---")

                    # Tabla FCFF
                    df_projections = pd.DataFrame({
                        "Año": [f"Año {i+1}" for i in range(len(db_growth_rates))],
                        "Tasa Crec. (%)": [g * 100 for g in db_growth_rates],
                        "Margen EBIT (%)": [m * 100 for m in db_ebit_margins],
                        "Ingresos Proyectados ($)": results_db.projected_revenues,
                        "EBIT ($)": results_db.projected_ebit,
                        "NOPAT ($)": results_db.projected_nopat,
                        "Flujo Caja Libre (FCF) ($)": results_db.free_cash_flows,
                        "PV FCF ($)": results_db.pv_cash_flows,
                    })

                    st.dataframe(df_projections.style.format({
                        "Tasa Crec. (%)": "{:.2f}%", "Margen EBIT (%)": "{:.2f}%",
                        "Ingresos Proyectados ($)": "${:,.2f}", "EBIT ($)": "${:,.2f}",
                        "NOPAT ($)": "${:,.2f}", "Flujo Caja Libre (FCF) ($)": "${:,.2f}", "PV FCF ($)": "${:,.2f}"
                    }), use_container_width=True)

                    st.session_state["active_pv_cash_flows"] = results_db.pv_cash_flows

                else:
                    st.warning(f"⚠️ No hay registros en MySQL para '{company_name}' / '{scenario_name}'.")

            except Exception as db_err:
                st.error(f"❌ Error al consultar MySQL: {db_err}")


        # =========================================================================
        # PESTAÑA 3: GRÁFICOS (DINÁMICOS SEGÚN MYSQL)
        # =========================================================================
        with tab3:
            st.header("📈 Análisis Gráfico (Basado en la DB)")
            
            pv_flows = st.session_state.get("active_pv_cash_flows", None)
            if pv_flows:
                df_chart = pd.DataFrame({
                    "Año": [f"Año {i+1}" for i in range(len(pv_flows))],
                    "PV FCF ($)": [float(val) for val in pv_flows],
                }).set_index("Año")
                
                st.bar_chart(df_chart)
            else:
                st.info("Carga o consulta un escenario en la Pestaña 2 para visualizar el gráfico.")

        # TAB 4
        with tab4:
            st.header("💾 Gestión de Escenarios")
            col_btn, col_history = st.columns([1, 2])
            
            with col_btn:
                if st.button("💾 Guardar en Base de Datos", type="primary"):
                    try:
                        success = DCFController.save_valuation(company_name=company_name, scenario_name=scenario_name, inputs=current_inputs, results=results)
                        if success:
                            st.success(f"✅ Escenario '{scenario_name}' guardado.")
                    except Exception:
                        try:
                            engine = get_sqlalchemy_engine()
                            df_summary = pd.DataFrame([{
                                "company_name": company_name, "scenario_name": scenario_name,
                                "enterprise_value": results.enterprise_value, "equity_value": results.equity_value,
                                "wacc": wacc, "terminal_growth_rate": terminal_growth_rate, "net_debt": net_debt
                            }])
                            df_summary.to_sql("dcf_valuations", con=engine, if_exists="append", index=False)
                            st.success(f"✅ Guardado en 'dcf_valuations'.")
                        except Exception as err:
                            st.error(f"❌ Error en MySQL: {err}")

            with col_history:
                if st.button("🔄 Consultar Historial"):
                    scenarios = DCFController.get_saved_scenarios(company_name)
                    if scenarios:
                        st.dataframe(pd.DataFrame(scenarios), use_container_width=True)
                    else:
                        st.info(f"Sin registros para '{company_name}'.")

    except Exception as e:
        st.error(f"Error en la ejecución del modelo: {e}")