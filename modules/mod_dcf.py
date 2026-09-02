import re
import unicodedata
import pandas as pd
import streamlit as st
from sqlalchemy import text

# Importaciones del módulo controller
from dcf_controller import DCFController, get_sqlalchemy_engine
from dcf_models import DCFInputs


def show_dcf_dataframe(engine, selected_company_id):
    """Consulta las tablas 'companies' y 'dcf_analyses' vía JOIN y las despliega formateadas."""
    query = text("""
        SELECT 
            c.company_id AS `ID Empresa`,
            c.name AS `Empresa`,
            c.tax_id AS `RIF`,
            d.analysis_id AS `ID Análisis`,
            d.scenario_name AS `Escenario`,
            d.historical_revenue AS `Ingresos Históricos`,
            d.tax_rate AS `Impuestos (%)`,
            d.wacc AS `WACC (%)`,
            d.terminal_growth_rate AS `Crec. Terminal (%)`,
            d.enterprise_value AS `Enterprise Value ($)`,
            d.equity_value AS `Equity Value ($)`,
            d.created_at AS `Fecha Creación`
        FROM dcf_analyses d
        INNER JOIN companies c ON d.company_id = c.company_id
        WHERE c.company_id = :company_id;
    """)
    
    df = pd.read_sql(query, engine, params={"company_id": selected_company_id})
    
    if not df.empty:
        st.dataframe(
            df,
            column_config={
                "Ingresos Históricos": st.column_config.NumberColumn(format="$%.2f"),
                "Impuestos (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "WACC (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Crec. Terminal (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Enterprise Value ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Equity Value ($)": st.column_config.NumberColumn(format="$%.2f"),
            },
            use_container_width=True
        )
    else:
        st.info(f"No se encontraron análisis en `dcf_analyses` para el ID de Empresa: {selected_company_id}")


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
    # VARIABLES DE ESTADO
    # -------------------------------------------------------------------------
    if "df_excel_inputs" not in st.session_state:
        st.session_state.df_excel_inputs = None
    if "df_excel_projs" not in st.session_state:
        st.session_state.df_excel_projs = None

    default_company = "Empresa Ejemplo S.A."
    default_scenario = "Base 2026"

    # Pestañas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📥 1. Cargar Excel a BD", 
        "📊 2. Resultados Desde MySQL", 
        "📈 3. Gráficos & Análisis", 
        "💾 4. Base de Datos / Historial"
    ])

    # =========================================================================
    # PESTAÑA 1: CARGA DE EXCEL A BD
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

                st.session_state["company_name"] = str(inputs_dict.get("company_name", default_company))
                st.session_state["scenario_name"] = str(inputs_dict.get("scenario_name", default_scenario))

                proj_sheet = "Projections" if "Projections" in sheet_names else (sheet_names[1] if len(sheet_names) > 1 else sheet_names[0])
                df_projs = pd.read_excel(excel_file, sheet_name=proj_sheet)
                if str(df_projs.columns[0]).startswith("Unnamed"):
                    df_projs = pd.read_excel(excel_file, sheet_name=proj_sheet, header=1)

                df_projs = df_projs.dropna(how="all")
                df_projs.columns = [clean_column_name(col) for col in df_projs.columns]

                st.session_state.df_excel_inputs = df_inputs
                st.session_state.df_excel_projs = df_projs
                st.success(f"✅ Archivo procesado en memoria. Guarda los datos en MySQL para usarlos en el análisis.")

            except Exception as e:
                st.error(f"❌ Error al procesar el archivo Excel: {e}")

        if st.session_state.get("df_excel_inputs") is not None or st.session_state.get("df_excel_projs") is not None:
            st.markdown("---")
            if st.button("💾 Insertar Data Cruda de Excel en MySQL", type="primary"):
                try:
                    engine = get_sqlalchemy_engine()
                    company_name = st.session_state.get("company_name", default_company)
                    scenario_name = st.session_state.get("scenario_name", default_scenario)

                    if st.session_state.get("df_excel_inputs") is not None:
                        df_in = st.session_state.df_excel_inputs.copy()
                        param_col_in = next((c for c in df_in.columns if clean_column_name(c) in ["parametro", "parametros", "variable", "concept", "concepto", "key"]), df_in.columns[0])
                        val_col_in = next((c for c in df_in.columns if clean_column_name(c) in ["valor", "valores", "value", "monto", "monto_mensual"]), df_in.columns[1] if len(df_in.columns) > 1 else df_in.columns[0])

                        df_in_to_save = pd.DataFrame({
                            "company_name": [company_name] * len(df_in),
                            "scenario_name": [scenario_name] * len(df_in),
                            "Parametro": df_in[param_col_in].astype(str),
                            "Valor": df_in[val_col_in].astype(str)
                        })
                        df_in_to_save.to_sql("excel_inputs_raw", con=engine, if_exists="append", index=False)

                    if st.session_state.get("df_excel_projs") is not None:
                        df_proj = st.session_state.df_excel_projs.copy()
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
    # CONTROLES SIDEBAR (FILTROS DE CONSULTA A MYSQL)
    # -------------------------------------------------------------------------
    st.sidebar.header("🔍 Consultar Escenario desde MySQL")
    company_name = st.sidebar.text_input("Empresa (MySQL)", value=st.session_state.get("company_name", default_company))
    scenario_name = st.sidebar.text_input("Escenario (MySQL)", value=st.session_state.get("scenario_name", default_scenario))

    # -------------------------------------------------------------------------
    # PESTAÑA 2: RESULTADOS (100% DESDE MYSQL)
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # PESTAÑA 2: RESULTADOS (100% DESDE MYSQL CON PROTECCIÓN DIVISION BY ZERO)
    # -------------------------------------------------------------------------
    with tab2:
        st.header("📊 Resultados de Valoración (Exclusivo desde MySQL)")

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
                # Mapeo dinámico leyendo directo de la base de datos
                inputs_dict = dict(zip(
                    df_db_inputs["Parametro"].astype(str).str.strip().str.lower(), 
                    df_db_inputs["Valor"]
                ))

                db_historical_revenue = safe_float(inputs_dict.get("historical_revenue"))
                db_tax_rate = safe_float(inputs_dict.get("tax_rate"))
                db_capex = safe_float(inputs_dict.get("capex_percent"))
                db_nwc = safe_float(inputs_dict.get("nwc_percent"))
                db_da = safe_float(inputs_dict.get("da_percent"))
                
                # Cargar tasas financieras
                db_wacc = safe_float(inputs_dict.get("wacc"), default_val=0.10) # 10% por defecto si no existe
                db_g = safe_float(inputs_dict.get("terminal_growth_rate"), default_val=0.02) # 2% por defecto
                db_debt = safe_float(inputs_dict.get("net_debt"))

                # -------------------------------------------------------------
                # VALIDACIÓN CRÍTICA CONTRA DIVISION BY ZERO
                # -------------------------------------------------------------
                if db_wacc <= db_g:
                    st.error(
                        f"🚨 **Error de consistencia financiera en MySQL:**\n\n"
                        f"- **WACC:** `{db_wacc:.2%}`\n"
                        f"- **Crecimiento Terminal (g):** `{db_g:.2%}`\n\n"
                        f"El WACC debe ser estrictamente mayor que la tasa de crecimiento terminal ($\text{{WACC}} > g$). "
                        f"Si son iguales, el denominador $(\text{{WACC}} - g)$ resulta en cero o en un valor negativo inválido."
                    )
                else:
                    df_db_projs["growth_rate"] = df_db_projs["growth_rate"].apply(lambda x: safe_float(x, 0.0))
                    df_db_projs["ebit_margin"] = df_db_projs["ebit_margin"].apply(lambda x: safe_float(x, 0.0))

                    db_growth_rates = df_db_projs["growth_rate"].tolist()
                    db_ebit_margins = df_db_projs["ebit_margin"].tolist()

                    # Ejecución segura de la valoración
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
                st.warning(f"⚠️ No se encontraron registros guardados en MySQL para la empresa '{company_name}' y el escenario '{scenario_name}'. Carga el archivo en la Pestaña 1 e insértalo a la BD.")

        except Exception as db_err:
            st.error(f"❌ Error al consultar o procesar datos desde MySQL: {db_err}")

    # -------------------------------------------------------------------------
    # PESTAÑA 3: GRÁFICOS
    # -------------------------------------------------------------------------
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
            st.info("Consulta un escenario válido en MySQL para visualizar el gráfico.")

    # -------------------------------------------------------------------------
    # PESTAÑA 4: HISTORIAL Y CONSULTAS SQL
    # -------------------------------------------------------------------------
    with tab4:
        st.header("💾 Gestión de Escenarios & Consultas SQL")
        
        if st.button("🔄 Consultar Historial Controller"):
            scenarios = DCFController.get_saved_scenarios(company_name)
            if scenarios:
                st.dataframe(pd.DataFrame(scenarios), use_container_width=True)
            else:
                st.info(f"Sin registros para '{company_name}'.")

        st.markdown("---")
        st.subheader("📋 Consultar Registro Unificado (companies + dcf_analyses)")
        selected_company_id = st.number_input("ID de Empresa a consultar (`company_id`)", min_value=1, value=101, step=1)
        
        if st.button("🔍 Mostrar Tabla de Análisis Relacionados"):
            try:
                engine = get_sqlalchemy_engine()
                show_dcf_dataframe(engine, selected_company_id)
            except Exception as err_join:
                st.error(f"❌ Error al realizar la consulta JOIN: {err_join}")