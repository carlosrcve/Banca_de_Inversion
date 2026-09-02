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

    # Función auxiliar para parsear cadenas de texto o números a flotantes
    def parse_num(val, default=0.0):
        if pd.isna(val):
            return default
        try:
            s = str(val).replace("%", "").replace("$", "").replace(",", "").strip()
            return float(s)
        except:
            return default

    def clean_str(val):
        return str(val).strip().lower()

    with tab1:
        st.header("📥 Cargar Modelo DCF a MySQL")

        uploaded_files = st.file_uploader(
            "Subir archivos Excel (.xlsx / .xls)", 
            type=["xlsx", "xls"], 
            accept_multiple_files=True,
            key="dcf_excel_uploader"
        )

        if uploaded_files:
            engine = get_sqlalchemy_engine()

            for uploaded_file in uploaded_files:
                try:
                    excel_file = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_file.sheet_names
                    df_first_sheet = pd.read_excel(excel_file, sheet_name=0)
                    df_first_sheet.columns = df_first_sheet.columns.astype(str).str.strip()

                    # =========================================================================
                    # CASO 1: ARCHIVO DIRECTO DE `dcf_analyses.xlsx`
                    # =========================================================================
                    if "historical_revenue" in df_first_sheet.columns and "scenario_name" in df_first_sheet.columns:
                        st.info(f"📄 Archivo **{uploaded_file.name}** reconocido como estructura directa de **dcf_analyses** ({len(df_first_sheet)} registros).")
                        
                        if st.button(f"🚀 Insertar {uploaded_file.name} en `dcf_analyses`", key=f"btn_an_{uploaded_file.name}"):
                            try:
                                df_to_insert = df_first_sheet.drop(columns=["analysis_id"], errors="ignore")
                                df_to_insert.to_sql(name="dcf_analyses", con=engine, if_exists="append", index=False)
                                st.success(f"✅ Se insertaron {len(df_to_insert)} registros en la tabla `dcf_analyses`.")
                            except Exception as e:
                                st.error(f"❌ Error al insertar en dcf_analyses: {e}")

                    # =========================================================================
                    # CASO 2: ARCHIVO DIRECTO DE `dcf_projections.xlsx`
                    # =========================================================================
                    elif "year_index" in df_first_sheet.columns and ("valuation_id" in df_first_sheet.columns or "analysis_id" in df_first_sheet.columns):
                        st.info(f"📄 Archivo **{uploaded_file.name}** detectado para la tabla **dcf_projections** ({len(df_first_sheet)} filas).")
                        
                        # 1. Normalizar el nombre de la columna a 'analysis_id'
                        if "valuation_id" in df_first_sheet.columns:
                            df_first_sheet = df_first_sheet.rename(columns={"valuation_id": "analysis_id"})

                        # 2. Consultar los IDs existentes en dcf_analyses (ordenados del más reciente al más antiguo)
                        try:
                            df_parents = pd.read_sql("SELECT analysis_id, scenario_name FROM dcf_analyses ORDER BY analysis_id DESC", con=engine)
                        except Exception as e:
                            df_parents = pd.DataFrame()

                        if df_parents.empty:
                            st.error("❌ No hay registros en `dcf_analyses`. Debes subir primero la tabla padre.")
                        else:
                            # Preselecciona automáticamente el ÚLTIMO ID creado en la primera tabla
                            latest_id = int(df_parents.iloc[0]["analysis_id"])

                            target_analysis_id = st.selectbox(
                                "📌 Vincular estas proyecciones al Análisis ID:",
                                options=df_parents["analysis_id"].tolist(),
                                index=0,  # Toma automáticamente el primero de la lista (el más reciente)
                                format_func=lambda x: f"ID #{x} - Escenario: {df_parents[df_parents['analysis_id']==x]['scenario_name'].values[0]}"
                            )

                            # Sobrescribir el '1' del Excel con el ID real registrado en MySQL
                            df_first_sheet["analysis_id"] = target_analysis_id

                            # 3. Inserción directa en MySQL
                            if st.button(f"🚀 Guardar {uploaded_file.name} en `dcf_projections`", key=f"btn_direct_{uploaded_file.name}"):
                                try:
                                    # Omitir columnas autogeneradas (PK y timestamp)
                                    df_to_insert = df_first_sheet.drop(columns=["id", "created_at"], errors="ignore")
                                    
                                    df_to_insert.to_sql(
                                        name="dcf_projections", 
                                        con=engine, 
                                        if_exists="append", 
                                        index=False
                                    )
                                    st.success(f"✅ ¡Guardado exitoso! Se insertaron los {len(df_to_insert)} registros en `dcf_projections` vinculados al `analysis_id = {target_analysis_id}`.")
                                except Exception as e:
                                    st.error(f"❌ Error al guardar en MySQL: {e}")

                    # =========================================================================
                    # CASO 3: ARCHIVO MODELO INTERNO (HOJAS "Inputs" Y "Projections")
                    # =========================================================================
                    else:
                        st.info(f"📄 Archivo **{uploaded_file.name}** procesado como Modelo Interactivo (Inputs + Projections).")
                        
                        inputs_sheet = "Inputs" if "Inputs" in sheet_names else sheet_names[0]
                        df_inputs_raw = pd.read_excel(excel_file, sheet_name=inputs_sheet)

                        if str(df_inputs_raw.columns[0]).startswith("Unnamed"):
                            df_inputs_raw = pd.read_excel(excel_file, sheet_name=inputs_sheet, header=1)

                        p_col = df_inputs_raw.columns[0]
                        v_col = df_inputs_raw.columns[1] if len(df_inputs_raw.columns) > 1 else df_inputs_raw.columns[0]

                        inputs_dict = {clean_str(row[p_col]): row[v_col] for _, row in df_inputs_raw.iterrows()}

                        # Función auxiliar para convertir porcentajes de manera consistente
                        def to_dec(val):
                            v = parse_num(val)
                            return v / 100.0 if v > 1.0 else v

                        comp_id = int(parse_num(inputs_dict.get("company_id", inputs_dict.get("id_empresa", 1))))
                        scen_name = str(inputs_dict.get("scenario_name", inputs_dict.get("escenario", "Base")))
                        hist_rev = parse_num(inputs_dict.get("historical_revenue", inputs_dict.get("ingresos_historicos", 0)))
                        tax_rate = to_dec(inputs_dict.get("tax_rate", inputs_dict.get("tasa_impuesto", 0)))
                        capex_pct = to_dec(inputs_dict.get("capex_percent", inputs_dict.get("capex_pct", 0)))
                        nwc_pct = to_dec(inputs_dict.get("nwc_percent", inputs_dict.get("nwc_pct", 0)))
                        da_pct = to_dec(inputs_dict.get("da_percent", inputs_dict.get("da_pct", 0)))
                        wacc_dec = to_dec(inputs_dict.get("wacc", 0))
                        g_term_dec = to_dec(inputs_dict.get("terminal_growth_rate", inputs_dict.get("crecimiento_terminal", 0)))
                        net_debt = parse_num(inputs_dict.get("net_debt", inputs_dict.get("deuda_neta", 0)))

                        proj_sheet = "Projections" if "Projections" in sheet_names else (sheet_names[1] if len(sheet_names) > 1 else sheet_names[0])
                        df_projs = pd.read_excel(excel_file, sheet_name=proj_sheet).dropna(how="all")

                        if str(df_projs.columns[0]).startswith("Unnamed"):
                            df_projs = pd.read_excel(excel_file, sheet_name=proj_sheet, header=1)

                        # Cálculo en un solo paso y almacenamiento en memoria
                        calculated_projections = []
                        curr_rev = hist_rev
                        prev_rev = hist_rev
                        sum_pv_fcf = 0.0

                        for idx, row in df_projs.iterrows():
                            year_index = idx + 1
                            year_label = str(row.get("year_label", f"Año {year_index}"))
                            g_rate = to_dec(row.get("growth_rate", 0))
                            ebit_m = to_dec(row.get("ebit_margin", 0))

                            p_rev = curr_rev * (1 + g_rate)
                            ebit = p_rev * ebit_m
                            nopat = ebit * (1 - tax_rate)
                            da = p_rev * da_pct
                            capex = p_rev * capex_pct
                            nwc_change = (p_rev - prev_rev) * nwc_pct
                            
                            fcf = nopat + da - capex - nwc_change
                            pv_fcf = fcf / ((1 + wacc_dec) ** year_index)
                            sum_pv_fcf += pv_fcf

                            calculated_projections.append({
                                "year_index": year_index,
                                "year_label": year_label,
                                "growth_rate": g_rate,
                                "ebit_margin": ebit_m,
                                "projected_revenue": p_rev,
                                "ebit": ebit,
                                "nopat": nopat,
                                "da": da,
                                "capex": capex,
                                "nwc_change": nwc_change,
                                "fcf": fcf,
                                "pv_fcf": pv_fcf
                            })

                            prev_rev = p_rev
                            curr_rev = p_rev

                        # Métricas terminales
                        n_years = len(calculated_projections)
                        last_fcf = calculated_projections[-1]["fcf"] if n_years > 0 else 0.0
                        
                        terminal_value = (last_fcf * (1 + g_term_dec)) / (wacc_dec - g_term_dec) if wacc_dec > g_term_dec else 0.0
                        pv_terminal_value = terminal_value / ((1 + wacc_dec) ** n_years) if n_years > 0 else 0.0
                        enterprise_value = sum_pv_fcf + pv_terminal_value
                        equity_value = enterprise_value - net_debt

                        st.success(f"📋 Modelo interpretado. Company ID: **{comp_id}** | Escenario: **{scen_name}** | Años: **{n_years}**")

                        if st.button(f"🚀 Guardar {uploaded_file.name} en MySQL", key=f"btn_gen_{uploaded_file.name}"):
                            try:
                                with engine.begin() as conn:
                                    res_an = conn.execute(text("""
                                        INSERT INTO dcf_analyses (
                                            company_id, scenario_name, historical_revenue, tax_rate, 
                                            capex_percent, nwc_percent, da_percent, wacc, 
                                            terminal_growth_rate, net_debt, terminal_value, enterprise_value, equity_value
                                        ) VALUES (
                                            :company_id, :scenario_name, :historical_revenue, :tax_rate, 
                                            :capex_percent, :nwc_percent, :da_percent, :wacc, 
                                            :terminal_growth_rate, :net_debt, :terminal_value, :enterprise_value, :equity_value
                                        )
                                    """), {
                                        "company_id": comp_id, "scenario_name": scen_name, "historical_revenue": hist_rev,
                                        "tax_rate": tax_rate, "capex_percent": capex_pct, "nwc_percent": nwc_pct,
                                        "da_percent": da_pct, "wacc": wacc_dec, "terminal_growth_rate": g_term_dec,
                                        "net_debt": net_debt, "terminal_value": terminal_value,
                                        "enterprise_value": enterprise_value, "equity_value": equity_value
                                    })
                                    
                                    analysis_id = res_an.lastrowid

                                    for proj in calculated_projections:
                                        proj["analysis_id"] = analysis_id
                                        conn.execute(text("""
                                            INSERT INTO dcf_projections (
                                                analysis_id, year_index, year_label, growth_rate, ebit_margin,
                                                projected_revenue, ebit, nopat, da, capex, nwc_change, fcf, pv_fcf
                                            ) VALUES (
                                                :analysis_id, :year_index, :year_label, :growth_rate, :ebit_margin,
                                                :projected_revenue, :ebit, :nopat, :da, :capex, :nwc_change, :fcf, :pv_fcf
                                            )
                                        """), proj)

                                st.success(f"✅ ¡Análisis ID **#{analysis_id}** y **{n_years}** proyecciones guardados con éxito!")
                            except Exception as e:
                                st.error(f"❌ Error al procesar la inserción en MySQL: {e}")

                except Exception as e:
                    st.error(f"❌ Error al leer el archivo **{uploaded_file.name}**: {e}")

    # -------------------------------------------------------------------------
    # CONTROLES SIDEBAR (FILTROS DE CONSULTA A MYSQL)
    # -------------------------------------------------------------------------
    st.sidebar.header("🔍 Consultar Escenario desde MySQL")
    company_name = st.sidebar.text_input("Empresa (MySQL)", value=st.session_state.get("company_name", default_company))
    scenario_name = st.sidebar.text_input("Escenario (MySQL)", value=st.session_state.get("scenario_name", default_scenario))
    # -------------------------------------------------------------------------
    # PESTAÑA 2: RESULTADOS (100% DESDE MYSQL CON PARSER ROBUSTO)
    # -------------------------------------------------------------------------
    with tab2:
        st.header("📊 Resultados de Valoración (Exclusivo desde MySQL)")

        try:
            engine = get_sqlalchemy_engine()

            # 1. Verificación directa de registros en dcf_analyses
            df_analyses_check = pd.read_sql("SELECT analysis_id FROM dcf_analyses LIMIT 1", con=engine)

            if df_analyses_check.empty:
                st.warning("⚠️ No hay análisis registrados en MySQL (`dcf_analyses` está vacía). Por favor carga un archivo en la Pestaña 1.")
            else:
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
                    # Función para limpiar cualquier string con %, $ o comas guardado en MySQL
                    def parse_db_val(val, default=0.0):
                        if pd.isna(val) or val is None:
                            return float(default)
                        val_str = str(val).strip().replace("$", "").replace(",", "")
                        if "%" in val_str:
                            try:
                                return float(val_str.replace("%", "").strip()) / 100.0
                            except ValueError:
                                return float(default)
                        try:
                            return float(val_str)
                        except ValueError:
                            return float(default)

                    # Mapeo normalizando nombres de parámetros (snake_case)
                    inputs_dict = {
                        clean_column_name(k): v 
                        for k, v in zip(df_db_inputs["Parametro"], df_db_inputs["Valor"])
                    }

                    # Lectura de parámetros desde la BD con fallbacks financieros válidos
                    db_historical_revenue = parse_db_val(inputs_dict.get("historical_revenue"), 1000000.0)
                    db_tax_rate = parse_db_val(inputs_dict.get("tax_rate"), 0.25)
                    db_capex = parse_db_val(inputs_dict.get("capex_percent"), 0.04)
                    db_nwc = parse_db_val(inputs_dict.get("nwc_percent"), 0.02)
                    db_da = parse_db_val(inputs_dict.get("da_percent"), 0.03)
                    
                    db_wacc = parse_db_val(inputs_dict.get("wacc"), 0.10)
                    db_g = parse_db_val(inputs_dict.get("terminal_growth_rate"), 0.025)
                    db_debt = parse_db_val(inputs_dict.get("net_debt"), 0.0)

                    # Ajustar decimales si fueron guardados como enteros (ej. 10 en vez de 0.10)
                    if db_wacc > 1.0: db_wacc /= 100.0
                    if db_g > 1.0: db_g /= 100.0
                    if db_tax_rate > 1.0: db_tax_rate /= 100.0
                    if db_capex > 1.0: db_capex /= 100.0
                    if db_nwc > 1.0: db_nwc /= 100.0
                    if db_da > 1.0: db_da /= 100.0

                    # Procesar tasas de proyecciones
                    db_growth_rates = [parse_db_val(x, 0.05) for x in df_db_projs["growth_rate"]]
                    db_ebit_margins = [parse_db_val(x, 0.15) for x in df_db_projs["ebit_margin"]]

                    db_growth_rates = [x / 100.0 if x > 1.0 else x for x in db_growth_rates]
                    db_ebit_margins = [x / 100.0 if x > 1.0 else x for x in db_ebit_margins]

                    # Validación contra división por cero
                    if db_wacc <= db_g:
                        st.error(f"🚨 **WACC ({db_wacc:.2%}) debe ser mayor que g ({db_g:.2%}).** Revisa la base de datos.")
                    else:
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

                        # --- CÁLCULO DINÁMICO DE PORCENTAJES Y SUMATORIAS ---
                        import textwrap

                        # --- CÁLCULO DINÁMICO DE PORCENTAJES Y SUMATORIAS ---
                        pv_tv_val = results_db.pv_terminal_value
                        ev_val = results_db.enterprise_value
                        eq_val = results_db.equity_value

                        tv_pct = (pv_tv_val / ev_val * 100) if ev_val > 0 else 0
                        pv_fcf_total = sum(results_db.pv_cash_flows)
                        fcf_pct = 100 - tv_pct
                        n_years = len(results_db.pv_cash_flows)

                        # --- INTERPRETACIÓN Y EXPLICACIÓN CON ESTILO HTML/CSS ---
                        html_interpretation = textwrap.dedent(f"""
                            <div style="
                                background-color: #e8f4f8; 
                                border-left: 5px solid #29b6f6; 
                                padding: 18px 20px; 
                                border-radius: 8px; 
                                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                color: #1a202c; 
                                margin-bottom: 20px;">
                                
                                <div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #0288d1;">
                                    📝 Interpretación Financiera de los Resultados (Dinámico desde MySQL):
                                </div>
                                
                                <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                                    <li style="margin-bottom: 8px;">
                                        <b>🏢 Enterprise Value (Valor Operativo) — ${ev_val:,.2f}:</b> 
                                        Es el valor total de la operación del negocio calculado en base a las premisas registradas en la base de datos.
                                    </li>
                                    <li style="margin-bottom: 8px;">
                                        <b>💵 Equity Value (Patrimonio) — ${eq_val:,.2f}:</b> 
                                        Es el valor neto correspondiente a los accionistas. Al compararse con el Enterprise Value, refleja un ajuste por Deuda Neta de <b>${db_debt:,.2f}</b>.
                                    </li>
                                    <li style="margin-bottom: 0px;">
                                        <b>🌐 Valor Presente Terminal (PV TV) — ${pv_tv_val:,.2f}:</b> 
                                        Es el valor actual de todos los flujos de caja a perpetuidad a partir del año {n_years + 1}. 
                                        Representa el <b>{tv_pct:.2f}%</b> del valor total de la compañía, mientras que los flujos proyectados explícitos de los primeros {n_years} años aportan el <b>{fcf_pct:.2f}%</b> restante (<b>${pv_fcf_total:,.2f}</b>).
                                    </li>
                                </ul>
                            </div>
                        """)

                        st.markdown(html_interpretation, unsafe_allow_html=True)

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
                    st.warning(f"⚠️ No hay datos guardados en las tablas raw para '{company_name}' / '{scenario_name}'. Ve a la Pestaña 1 e insértalos en MySQL.")

        except Exception as db_err:
            st.error(f"❌ Error al procesar datos desde MySQL: {db_err}")

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