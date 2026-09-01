from sqlalchemy import create_engine
import pandas as pd
import streamlit as st
from dcf_controller import DCFController
from dcf_models import DCFInputs

def render():
    st.title("📊 Modelo de Valoración por Flujo de Caja Descontado (DCF)")

    # -------------------------------------------------------------------------
    # ENCABEZADO Y CARGA DE EXCEL AL FRENTE (A LA DERECHA)
    # -------------------------------------------------------------------------
    col_header, col_excel = st.columns([1.2, 1])

    with col_header:
        st.markdown("""
        Esta herramienta calcula el **Valor de la Empresa (Enterprise Value)** y el **Valor del Patrimonio (Equity Value)** 
        mediante carga de plantilla Excel o ingreso manual de parámetros.
        """)

    # Variables de almacenamiento temporal en session_state para inserción masiva
    if "df_excel_inputs" not in st.session_state:
        st.session_state.df_excel_inputs = None
    if "df_excel_projs" not in st.session_state:
        st.session_state.df_excel_projs = None

    # Valores por defecto para el modelo
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

    with col_excel:
        st.subheader("📥 Cargar Modelo desde Excel")
        uploaded_file = st.file_uploader(
            "Subir archivo .xlsx / .xls",
            type=["xlsx", "xls"],
            key="excel_uploader_main",
        )

        if uploaded_file is not None:
            try:
                excel_file = pd.ExcelFile(uploaded_file)
                sheet_names = excel_file.sheet_names

                inputs_sheet = "Inputs" if "Inputs" in sheet_names else sheet_names[0]
                df_inputs = pd.read_excel(excel_file, sheet_name=inputs_sheet)
                df_inputs.columns = [str(col).strip() for col in df_inputs.columns]

                param_col, val_col = None, None
                for col in df_inputs.columns:
                    col_clean = (
                        col.lower()
                        .replace("á", "a")
                        .replace("é", "e")
                        .replace("í", "i")
                        .replace("ó", "o")
                        .replace("ú", "u")
                    )
                    if col_clean in [
                        "parametro",
                        "parametros",
                        "variable",
                        "variables",
                        "concept",
                        "concepto",
                        "key",
                    ]:
                        param_col = col
                    elif col_clean in ["valor", "valores", "value", "values", "monto"]:
                        val_col = col

                if not param_col:
                    param_col = df_inputs.columns[0]
                if not val_col:
                    val_col = (
                        df_inputs.columns[1]
                        if len(df_inputs.columns) > 1
                        else df_inputs.columns[0]
                    )

                inputs_dict = dict(
                    zip(
                        df_inputs[param_col].astype(str).str.strip(),
                        df_inputs[val_col],
                    )
                )

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

                proj_sheet = (
                    "Projections"
                    if "Projections" in sheet_names
                    else (sheet_names[1] if len(sheet_names) > 1 else sheet_names[0])
                )
                df_projs = pd.read_excel(excel_file, sheet_name=proj_sheet)
                df_projs.columns = [str(col).strip() for col in df_projs.columns]

                if (
                    "growth_rate" in df_projs.columns
                    and "ebit_margin" in df_projs.columns
                ):
                    default_years = len(df_projs)
                    default_growth = df_projs["growth_rate"].tolist()
                    default_ebit = df_projs["ebit_margin"].tolist()

                st.session_state.df_excel_inputs = df_inputs
                st.session_state.df_excel_projs = df_projs

                st.success(
                    f"✅ Archivo cargado correctamente ({inputs_sheet} / {proj_sheet})"
                )

            except Exception as e:
                st.error(f"❌ Error al procesar Excel: {e}")

        # BOTÓN PARA INSERCIÓN DIRECTA DE LA DATA DEL EXCEL A MYSQL
        if (
            st.session_state.df_excel_inputs is not None
            or st.session_state.df_excel_projs is not None
        ):
            if st.button("💾 Insertar Data de Excel en MySQL", type="primary"):
                try:
                    db_url = st.secrets["mysql"]["url"]
                    engine = create_engine(db_url)

                    if st.session_state.df_excel_inputs is not None:
                        df_inp_save = st.session_state.df_excel_inputs.copy()
                        df_inp_save["company_name"] = default_company
                        df_inp_save["scenario_name"] = default_scenario
                        df_inp_save.to_sql(
                            "excel_inputs_raw",
                            con=engine,
                            if_exists="append",
                            index=False,
                        )

                    if st.session_state.df_excel_projs is not None:
                        df_proj_save = st.session_state.df_excel_projs.copy()
                        df_proj_save["company_name"] = default_company
                        df_proj_save["scenario_name"] = default_scenario
                        df_proj_save.to_sql(
                            "excel_projections_raw",
                            con=engine,
                            if_exists="append",
                            index=False,
                        )

                    st.success(
                        "✅ ¡Toda la data del Excel fue insertada en las tablas de MySQL!"
                    )
                except Exception as err:
                    st.error(f"❌ Error en INSERT INTO MySQL: {err}")

    # -------------------------------------------------------------------------
    # CONTROLES SIDEBAR
    # -------------------------------------------------------------------------
    st.sidebar.header("📌 Parámetros Generales")
    company_name = st.sidebar.text_input("Nombre de la Empresa", value=default_company)
    scenario_name = st.sidebar.text_input("Nombre del Escenario", value=default_scenario)

    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Datos Financieros Iniciales")

    historical_revenue = st.sidebar.number_input(
        "Ingresos del Último Año ($)",
        min_value=0.0,
        value=default_revenue,
        step=50000.0,
        format="%.2f",
    )

    num_years = st.sidebar.slider(
        "Años de Proyección", min_value=3, max_value=10, value=default_years
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
        g_val = (default_growth[i] * 100) if i < len(default_growth) else 5.0
        m_val = (default_ebit[i] * 100) if i < len(default_ebit) else 15.0

        with col1:
            g = (
                col1.number_input(
                    f"Año {i+1} Crec.",
                    value=float(g_val),
                    step=0.5,
                    key=f"g_{i}",
                )
                / 100.0
            )
            growth_rates.append(g)
        with col2:
            m = (
                col2.number_input(
                    f"Año {i+1} EBIT",
                    value=float(m_val),
                    step=0.5,
                    key=f"m_{i}",
                )
                / 100.0
            )
            ebit_margins.append(m)

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Supuestos Financieros & Tasa de Descuento")

    tax_rate = (
        st.sidebar.number_input(
            "Tasa de Impuestos (%)", value=default_tax * 100, step=1.0
        )
        / 100.0
    )
    capex_percent = (
        st.sidebar.number_input(
            "CapEx / Ingresos (%)", value=default_capex * 100, step=0.5
        )
        / 100.0
    )
    nwc_percent = (
        st.sidebar.number_input(
            "Δ NWC / Ingresos (%)", value=default_nwc * 100, step=0.5
        )
        / 100.0
    )
    da_percent = (
        st.sidebar.number_input(
            "D&A / Ingresos (%)", value=default_da * 100, step=0.5
        )
        / 100.0
    )
    wacc = (
        st.sidebar.number_input(
            "WACC - Costo Promedio del Capital (%)",
            value=default_wacc * 100,
            step=0.5,
        )
        / 100.0
    )
    terminal_growth_rate = (
        st.sidebar.number_input(
            "Tasa de Crecimiento Perpetua g (%)",
            value=default_g * 100,
            step=0.1,
        )
        / 100.0
    )
    net_debt = st.sidebar.number_input(
        "Deuda Neta ($)", value=default_debt, step=10000.0
    )

    # -------------------------------------------------------------------------
    # CÁLCULO Y RESULTADOS DEL MODELO DCF
    # -------------------------------------------------------------------------
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

        # -------------------------------------------------------------------------
        # PERSISTENCIA EN BASE DE DATOS (MYSQL / TIDB)
        # -------------------------------------------------------------------------
        st.markdown("---")
        st.subheader("💾 Guardar y Consultar Valoraciones")

        col_btn, col_history = st.columns([1, 2])

        with col_btn:
            st.write("#### Guardar Escenario Actual")
            if st.button("💾 Guardar en Base de Datos", type="primary"):
                try:
                    success = DCFController.save_valuation(
                        company_name=company_name,
                        scenario_name=scenario_name,
                        inputs=current_inputs,
                        results=results,
                    )
                    if success:
                        st.success(f"✅ Escenario '{scenario_name}' guardado exitosamente.")
                    else:
                        st.error("❌ Error al guardar mediante Controller.")
                except Exception:
                    try:
                        db_url = st.secrets["mysql"]["url"]
                        engine = create_engine(db_url)
                        summary_data = {
                            "company_name": [company_name],
                            "scenario_name": [scenario_name],
                            "enterprise_value": [results.enterprise_value],
                            "equity_value": [results.equity_value],
                            "wacc": [wacc],
                            "terminal_growth_rate": [terminal_growth_rate],
                            "net_debt": [net_debt],
                        }
                        df_summary = pd.DataFrame(summary_data)
                        df_summary.to_sql(
                            "dcf_valuations",
                            con=engine,
                            if_exists="append",
                            index=False,
                        )
                        st.success(
                            f"✅ Escenario '{scenario_name}' guardado en 'dcf_valuations'."
                        )
                    except Exception as err:
                        st.error(f"❌ Error al guardar en MySQL: {err}")

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