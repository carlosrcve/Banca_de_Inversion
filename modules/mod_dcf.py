import re
import unicodedata
import pandas as pd
import streamlit as st
from sqlalchemy import text

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


def safe_float(val, default_val=0.0):
    """Convierte un valor a float de manera segura sin lanzar excepciones."""
    if val is None or pd.isna(val):
        return float(default_val)
    try:
        return float(val)
    except (ValueError, TypeError):
        return float(default_val)


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

                # Detectar columnas clave
                param_col = next((c for c in df_inputs.columns if clean_column_name(c) in ["parametro", "parametros", "variable", "concept", "concepto", "key"]), df_inputs.columns[0])
                val_col = next((c for c in df_inputs.columns if clean_column_name(c) in ["valor", "valores", "value", "monto", "monto_mensual"]), df_inputs.columns[1] if len(df_inputs.columns) > 1 else df_inputs.columns[0])

                inputs_dict = dict(zip(df_inputs[param_col].astype(str).str.strip(), df_inputs[val_col]))

                # Cargar variables a session_state
                st.session_state["company_name"] = str(inputs_dict.get("company_name", default_company))
                st.session_state["scenario_name"] = str(inputs_dict.get("scenario_name", default_scenario))
                st.session_state["historical_revenue"] = safe_float(inputs_dict.get("historical_revenue"), default_revenue)
                st.session_state["tax_rate"] = safe_float(inputs_dict.get("tax_rate"), default_tax)
                st.session_state["capex_percent"] = safe_float(inputs_dict.get("capex_percent"), default_capex)
                st.session_state["nwc_percent"] = safe_float(inputs_dict.get("nwc_percent"), default_nwc)
                st.session_state["da_percent"] = safe_float(inputs_dict.get("da_percent"), default_da)
                st.session_state["wacc"] = safe_float(inputs_dict.get("wacc"), default_wacc)
                st.session_state["terminal_growth_rate"] = safe_float(inputs_dict.get("terminal_growth_rate"), default_g)
                st.session_state["net_debt"] = safe_float(inputs_dict.get("net_debt"), default_debt)

                proj_sheet = "Projections" if "Projections" in sheet_names else (sheet_names[1] if len(sheet_names) > 1 else sheet_names[0])
                df_projs = pd.read_excel(excel_file, sheet_name=proj_sheet)
                if str(df_projs.columns[0]).startswith("Unnamed"):
                    df_projs = pd.read_excel(excel_file, sheet_name=proj_sheet, header=1)

                df_projs = df_projs.dropna(how="all")
                df_projs.columns = [clean_column_name(col) for col in df_projs.columns]

                if "growth_rate" in df_projs.columns and "ebit_margin" in df_projs.columns:
                    st.session_state["proj_years"] = len(df_projs)
                    st.session_state["growth_rates"] = [safe_float(x, 0.05) for x in df_projs["growth_rate"].tolist()]
                    st.session_state["ebit_margins"] = [safe_float(x, 0.15) for x in df_projs["ebit_margin"].tolist()]

                st.session_state.df_excel_inputs = df_inputs
                st.session_state.df_excel_projs = df_projs
                st.success(f"✅ Archivo procesado correctamente ({inputs_sheet} / {proj_sheet})")

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo Excel: {e}")

        # Sección para persistir en MySQL los datos crudos del Excel
        if st.session_state.get("df_excel_inputs") is not None or st.session_state.get("df_excel_projs") is not None:
            st.markdown("---")
            if st.button("💾 Insertar Data Cruda de Excel en MySQL", type="primary"):
                try:
                    engine = get_sqlalchemy_engine()
                    company_name = st.session_state.get("company_name", default_company)
                    scenario_name = st.session_state.get("scenario_name", default_scenario)

                    # 1. Guardar INPUTS en MySQL
                    if st.session_state.get("df_excel_inputs") is not None:
                        df_in = st.session_state.df_excel_inputs.copy()

                        if "company_name" in df_in.columns and "Parametro" in df_in.columns:
                            df_in_to_save = df_in
                        else:
                            param_col_in = next((c for c in df_in.columns if clean_column_name(c) in ["parametro", "parametros", "variable", "concept", "concepto", "key"]), df_in.columns[0])
                            val_col_in = next((c for c in df_in.columns if clean_column_name(c) in ["valor", "valores", "value", "monto", "monto_mensual"]), df_in.columns[1] if len(df_in.columns) > 1 else df_in.columns[0])

                            df_in_to_save = pd.DataFrame({
                                "company_name": [company_name] * len(df_in),
                                "scenario_name": [scenario_name] * len(df_in),
                                "Parametro": df_in[param_col_in].astype(str),
                                "Valor": df_in[val_col_in].astype(str)
                            })

                        df_in_to_save.to_sql("excel_inputs_raw", con=engine, if_exists="append", index=False)

                    # 2. Guardar PROYECCIONES en MySQL
                    if st.session_state.get("df_excel_projs") is not None:
                        df_proj = st.session_state.df_excel_projs.copy()

                        if "company_name" in df_proj.columns and "year" in df_proj.columns:
                            df_to_save = df_proj
                        else:
                            col_g = next((c for c in df_proj.columns if "growth" in c or "crec" in c), df_proj.columns[0])
                            col_m = next((c for c in df_proj.columns if "ebit" in c or "marg" in c), df_proj.columns[1] if len(df_proj.columns) > 1 else df_proj.columns[0])

                            df_to_save = pd.DataFrame({
                                "company_name": [company_name] * len(df_proj),
                                "scenario_name": [scenario_name] * len(df_proj),
                                "year": list(range(1, len(df_proj) + 1)),
                                "growth_rate": pd.to_numeric(df_proj[col_g], errors="coerce").fillna(0.05),
                                "ebit_margin": pd.to_numeric(df_proj[col_m], errors="coerce").fillna(0.15)
                            })

                        df_to_save.to_sql("excel_projections_raw", con=engine, if_exists="append", index=False)

                    st.success("✅ ¡Inputs y Proyecciones guardados exitosamente en MySQL!")

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
            g = col1.number_input(f"Año {i+1} Crec. (%)", value=float(g_val), step=0.5, key=f"g_{i}") / 100.0
            growth_rates.append(g)
        with col2:
            m = col2.number_input(f"Año {i+1} EBIT (%)", value=float(m_val), step=0.5, key=f"m_{i}") / 100.0
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

        # TAB 2: RESULTADOS
        with tab2:
            st.header("📊 Resultados de Valoración (Leídos desde MySQL)")

            try:
                engine = get_sqlalchemy_engine()

                query_inputs = text("""
                    SELECT Parametro, Valor 
                    FROM excel_inputs_raw 
                    WHERE company_name = :company AND scenario_name = :scenario
                    ORDER BY id ASC
                """)

                query_projs = text("""
                    SELECT year, growth_rate, ebit_margin 
                    FROM excel_projections_raw 
                    WHERE company_name = :company AND scenario_name = :scenario
                    ORDER BY year ASC
                """)

                df_db_inputs = pd.read_sql(query_inputs, con=engine, params={"company": company_name, "scenario": scenario_name})
                df_db_projs = pd.read_sql(query_projs, con=engine, params={"company": company_name, "scenario": scenario_name})

                if not df_db_inputs.empty and not df_db_projs.empty:
                    inputs_dict = dict(zip(
                        df_db_inputs["Parametro"].astype(str).str.strip().str.lower(), 
                        df_db_inputs["Valor"]
                    ))

                    db_historical_revenue = safe_float(inputs_dict.get("historical_revenue"), historical_revenue)
                    db_tax_rate = safe_float(inputs_dict.get("tax_rate"), tax_rate)
                    db_capex = safe_float(inputs_dict.get("capex_percent"), capex_percent)
                    db_nwc = safe_float(inputs_dict.get("nwc_percent"), nwc_percent)
                    db_da = safe_float(inputs_dict.get("da_percent"), da_percent)
                    db_wacc = safe_float(inputs_dict.get("wacc"), wacc)
                    db_g = safe_float(inputs_dict.get("terminal_growth_rate"), terminal_growth_rate)
                    db_debt = safe_float(inputs_dict.get("net_debt"), net_debt)

                    df_db_projs["growth_rate"] = df_db_projs["growth_rate"].apply(lambda x: safe_float(x, 0.05))
                    df_db_projs["ebit_margin"] = df_db_projs["ebit_margin"].apply(lambda x: safe_float(x, 0.15))

                    db_growth_rates = df_db_projs["growth_rate"].tolist()
                    db_ebit_margins = df_db_projs["ebit_margin"].tolist()

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

                    col_res1, col_res2, col_res3 = st.columns(3)
                    col_res1.metric("🏢 Enterprise Value (EV)", f"${results_db.enterprise_value:,.2f}")
                    col_res2.metric("💵 Equity Value (Patrimonio)", f"${results_db.equity_value:,.2f}")
                    col_res3.metric("🌐 Valor Presente TV", f"${results_db.pv_terminal_value:,.2f}")

                    st.markdown("---")

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
                    st.warning(f"⚠️ No hay registros en MySQL para '{company_name}' / '{scenario_name}'. Se muestran los cálculos locales:")

                    col_res1, col_res2, col_res3 = st.columns(3)
                    col_res1.metric("🏢 Enterprise Value (EV)", f"${results.enterprise_value:,.2f}")
                    col_res2.metric("💵 Equity Value (Patrimonio)", f"${results.equity_value:,.2f}")
                    col_res3.metric("🌐 Valor Presente TV", f"${results.pv_terminal_value:,.2f}")

                    st.session_state["active_pv_cash_flows"] = results.pv_cash_flows

            except Exception as db_err:
                st.error(f"❌ Error al consultar MySQL: {db_err}")

        # TAB 3: GRÁFICOS
        with tab3:
            st.header("📈 Análisis Gráfico")
            pv_flows = st.session_state.get("active_pv_cash_flows", None)
            if pv_flows:
                df_chart = pd.DataFrame({
                    "Año": [f"Año {i+1}" for i in range(len(pv_flows))],
                    "PV FCF ($)": [float(val) for val in pv_flows],
                }).set_index("Año")

                st.bar_chart(df_chart)
            else:
                st.info("Carga o consulta un escenario para visualizar el gráfico.")

        # TAB 4: HISTORIAL Y GUARDADO
        with tab4:
            st.header("💾 Gestión de Escenarios")
            col_btn, col_history = st.columns([1, 2])

            with col_btn:
                if st.button("💾 Guardar en Base de Datos", type="primary"):
                    try:
                        success = DCFController.save_valuation(company_name=company_name, scenario_name=scenario_name, inputs=current_inputs, results=results)
                        if success:
                            st.success(f"✅ Escenario '{scenario_name}' guardado correctamente.")
                    except Exception:
                        try:
                            engine = get_sqlalchemy_engine()
                            df_summary = pd.DataFrame([{
                                "company_name": company_name, 
                                "scenario_name": scenario_name,
                                "enterprise_value": results.enterprise_value, 
                                "equity_value": results.equity_value,
                                "wacc": wacc, 
                                "terminal_growth_rate": terminal_growth_rate, 
                                "net_debt": net_debt
                            }])
                            df_summary.to_sql("dcf_valuations", con=engine, if_exists="append", index=False)
                            st.success("✅ Guardado alternativo en 'dcf_valuations' realizado.")
                        except Exception as err:
                            st.error(f"❌ Error al guardar en MySQL: {err}")

            with col_history:
                if st.button("🔄 Consultar Historial"):
                    scenarios = DCFController.get_saved_scenarios(company_name)
                    if scenarios:
                        st.dataframe(pd.DataFrame(scenarios), use_container_width=True)
                    else:
                        st.info(f"Sin registros para '{company_name}'.")

    except Exception as e:
        st.error(f"❌ Error durante la ejecución del modelo DCF: {e}")