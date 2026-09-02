#modules/mod_dcf.py
import io
import os
import re
import unicodedata
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import pandas as pd
import streamlit as st
from sqlalchemy import text

# Importaciones del módulo controller y modelos
from dcf_controller import DCFController, get_sqlalchemy_engine
from dcf_models import DCFInputs


# =============================================================================
# FUNCIONES AUXILIARES Y DE UTILIDAD
# =============================================================================
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


def parse_num(val, default=0.0):
    """Auxiliar para parsear cadenas con %, $ o comas a valores numéricos flotantes."""
    if pd.isna(val) or val is None:
        return default
    try:
        s = str(val).replace("%", "").replace("$", "").replace(",", "").strip()
        return float(s)
    except (ValueError, TypeError):
        return default


def clean_str(val):
    """Normaliza cadenas de texto a minúsculas y sin espacios laterales."""
    return str(val).strip().lower()


def init_db_tables(cursor):
    """Crea la estructura de tablas Padre e Hijo en MySQL si no existen."""
    query_padre = """
    CREATE TABLE IF NOT EXISTS dcf_analyses (
        analysis_id INT AUTO_INCREMENT PRIMARY KEY,
        company_id INT NOT NULL DEFAULT 1,
        scenario_name VARCHAR(255) NOT NULL,
        historical_revenue DECIMAL(18,2) NOT NULL,
        tax_rate DECIMAL(10,4) NOT NULL,
        capex_percent DECIMAL(10,4) NOT NULL,
        nwc_percent DECIMAL(10,4) NOT NULL,
        da_percent DECIMAL(10,4) NOT NULL,
        wacc DECIMAL(10,4) NOT NULL,
        terminal_growth_rate DECIMAL(10,4) NOT NULL,
        net_debt DECIMAL(18,2) NOT NULL,
        terminal_value DECIMAL(18,2) NOT NULL,
        enterprise_value DECIMAL(18,2) NOT NULL,
        equity_value DECIMAL(18,2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    query_hijo = """
    CREATE TABLE IF NOT EXISTS dcf_projections (
        id INT AUTO_INCREMENT PRIMARY KEY,
        analysis_id INT NOT NULL,
        year_index INT NOT NULL,
        year_label VARCHAR(50) NOT NULL,
        growth_rate DECIMAL(10,4) NOT NULL,
        ebit_margin DECIMAL(10,4) NOT NULL,
        projected_revenue DECIMAL(18,2) NOT NULL,
        ebit DECIMAL(18,2) NOT NULL,
        nopat DECIMAL(18,2) NOT NULL,
        da DECIMAL(18,2) NOT NULL,
        capex DECIMAL(18,2) NOT NULL,
        nwc_change DECIMAL(18,2) NOT NULL,
        fcf DECIMAL(18,2) NOT NULL,
        pv_fcf DECIMAL(18,2) NOT NULL,
        FOREIGN KEY (analysis_id) REFERENCES dcf_analyses(analysis_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    cursor.execute(query_padre)
    cursor.execute(query_hijo)


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
    
    try:
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
    except Exception as e:
        st.error(f"Error al consultar la vista consolidada: {e}")


# =============================================================================
# APLICACIÓN PRINCIPAL STREAMLIT
# =============================================================================
def render():
    st.title("📊 Modelo de Valoración por Flujo de Caja Descontado (DCF)")

    # Variables de estado
    if "df_excel_inputs" not in st.session_state:
        st.session_state.df_excel_inputs = None
    if "df_excel_projs" not in st.session_state:
        st.session_state.df_excel_projs = None

    default_company = "Empresa Ejemplo S.A."
    default_scenario = "Base 2026"

    # Sidebar: Filtros globales de consulta
    st.sidebar.header("🔍 Consultar Escenario desde MySQL")
    company_name = st.sidebar.text_input("Empresa (MySQL)", value=st.session_state.get("company_name", default_company))
    scenario_name = st.sidebar.text_input("Escenario (MySQL)", value=st.session_state.get("scenario_name", default_scenario))

    # Pestañas principales
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📥 1. Cargar Excel a BD", 
        "📊 2. Resultados Desde MySQL", 
        "📈 3. Gráficos & Análisis", 
        "💾 4. 📁 Gestor Documental",
        "📌 5. Dictamen & Conclusión"
    ])

    # -------------------------------------------------------------------------
    # PESTAÑA 1: CARGA DE ARCHIVOS
    # -------------------------------------------------------------------------
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

                    # CASO 1: Archivo directo dcf_analyses
                    if "historical_revenue" in df_first_sheet.columns and "scenario_name" in df_first_sheet.columns:
                        st.info(f"📄 Archivo **{uploaded_file.name}** reconocido como estructura directa de **dcf_analyses** ({len(df_first_sheet)} registros).")
                        
                        if st.button(f"🚀 Insertar {uploaded_file.name} en `dcf_analyses`", key=f"btn_an_{uploaded_file.name}"):
                            try:
                                df_to_insert = df_first_sheet.drop(columns=["analysis_id"], errors="ignore")
                                df_to_insert.to_sql(name="dcf_analyses", con=engine, if_exists="append", index=False)
                                st.success(f"✅ Se insertaron {len(df_to_insert)} registros en la tabla `dcf_analyses`.")
                            except Exception as e:
                                st.error(f"❌ Error al insertar en dcf_analyses: {e}")

                    # CASO 2: Archivo directo dcf_projections
                    elif "year_index" in df_first_sheet.columns and ("valuation_id" in df_first_sheet.columns or "analysis_id" in df_first_sheet.columns):
                        st.info(f"📄 Archivo **{uploaded_file.name}** detectado para la tabla **dcf_projections** ({len(df_first_sheet)} filas).")
                        
                        if "valuation_id" in df_first_sheet.columns:
                            df_first_sheet = df_first_sheet.rename(columns={"valuation_id": "analysis_id"})

                        try:
                            df_parents = pd.read_sql("SELECT analysis_id, scenario_name FROM dcf_analyses ORDER BY analysis_id DESC", con=engine)
                        except Exception:
                            df_parents = pd.DataFrame()

                        if df_parents.empty:
                            st.error("❌ No hay registros en `dcf_analyses`. Debes subir primero la tabla padre.")
                        else:
                            target_analysis_id = st.selectbox(
                                "📌 Vincular estas proyecciones al Análisis ID:",
                                options=df_parents["analysis_id"].tolist(),
                                index=0,
                                format_func=lambda x: f"ID #{x} - Escenario: {df_parents[df_parents['analysis_id']==x]['scenario_name'].values[0]}"
                            )

                            df_first_sheet["analysis_id"] = target_analysis_id

                            if st.button(f"🚀 Guardar {uploaded_file.name} en `dcf_projections`", key=f"btn_direct_{uploaded_file.name}"):
                                try:
                                    df_to_insert = df_first_sheet.drop(columns=["id", "created_at"], errors="ignore")
                                    df_to_insert.to_sql(name="dcf_projections", con=engine, if_exists="append", index=False)
                                    st.success(f"✅ ¡Guardado exitoso! Se insertaron los {len(df_to_insert)} registros vinculados al `analysis_id = {target_analysis_id}`.")
                                except Exception as e:
                                    st.error(f"❌ Error al guardar en MySQL: {e}")

                    # CASO 3: Archivo modelo interno (Inputs + Projections)
                    else:
                        st.info(f"📄 Archivo **{uploaded_file.name}** procesado como Modelo Interactivo (Inputs + Projections).")
                        
                        inputs_sheet = "Inputs" if "Inputs" in sheet_names else sheet_names[0]
                        df_inputs_raw = pd.read_excel(excel_file, sheet_name=inputs_sheet)

                        if str(df_inputs_raw.columns[0]).startswith("Unnamed"):
                            df_inputs_raw = pd.read_excel(excel_file, sheet_name=inputs_sheet, header=1)

                        p_col = df_inputs_raw.columns[0]
                        v_col = df_inputs_raw.columns[1] if len(df_inputs_raw.columns) > 1 else df_inputs_raw.columns[0]

                        inputs_dict = {clean_str(row[p_col]): row[v_col] for _, row in df_inputs_raw.iterrows()}

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
    # PESTAÑA 2: RESULTADOS
    # -------------------------------------------------------------------------
    with tab2:
        st.header("📊 Resultados de Valoración (Exclusivo desde MySQL)")

        try:
            engine = get_sqlalchemy_engine()
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

                    inputs_dict = {
                        clean_column_name(k): v 
                        for k, v in zip(df_db_inputs["Parametro"], df_db_inputs["Valor"])
                    }

                    db_historical_revenue = parse_db_val(inputs_dict.get("historical_revenue"), 1000000.0)
                    db_tax_rate = parse_db_val(inputs_dict.get("tax_rate"), 0.25)
                    db_capex = parse_db_val(inputs_dict.get("capex_percent"), 0.04)
                    db_nwc = parse_db_val(inputs_dict.get("nwc_percent"), 0.02)
                    db_da = parse_db_val(inputs_dict.get("da_percent"), 0.03)
                    db_wacc = parse_db_val(inputs_dict.get("wacc"), 0.10)
                    db_g = parse_db_val(inputs_dict.get("terminal_growth_rate"), 0.025)
                    db_debt = parse_db_val(inputs_dict.get("net_debt"), 0.0)
                    db_shares = parse_db_val(inputs_dict.get("shares_outstanding"), 0.0)

                    if db_wacc > 1.0: db_wacc /= 100.0
                    if db_g > 1.0: db_g /= 100.0
                    if db_tax_rate > 1.0: db_tax_rate /= 100.0
                    if db_capex > 1.0: db_capex /= 100.0
                    if db_nwc > 1.0: db_nwc /= 100.0
                    if db_da > 1.0: db_da /= 100.0

                    db_growth_rates = [parse_db_val(x, 0.05) for x in df_db_projs["growth_rate"]]
                    db_ebit_margins = [parse_db_val(x, 0.15) for x in df_db_projs["ebit_margin"]]

                    db_growth_rates = [x / 100.0 if x > 1.0 else x for x in db_growth_rates]
                    db_ebit_margins = [x / 100.0 if x > 1.0 else x for x in db_ebit_margins]

                    # -------------------------------------------------------------------------
                    # VALIDACIÓN WACC > g
                    # -------------------------------------------------------------------------
                    if db_wacc <= db_g:
                        st.error(f"🚨 **Validación Fallida: WACC ({db_wacc:.2%}) debe ser mayor que g ({db_g:.2%}).** No es posible calcular la perpetuidad ni la Matriz de Sensibilidad hasta corregir las premisas en la base de datos.")
                    else:
                        st.success(f"✅ **Validación Exitosa:** WACC ({db_wacc:.2%}) > g ({db_g:.2%})")

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

                        pv_tv_val = results_db.pv_terminal_value
                        ev_val = results_db.enterprise_value
                        eq_val = results_db.equity_value

                        tv_pct = (pv_tv_val / ev_val * 100) if ev_val > 0 else 0
                        pv_fcf_total = sum(results_db.pv_cash_flows)
                        fcf_pct = 100 - tv_pct
                        n_years = len(results_db.pv_cash_flows)

                        html_interpretation = (
                            f'<div style="background-color: #e8f4f8; border-left: 5px solid #29b6f6; padding: 18px 20px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; color: #1a202c; margin-bottom: 20px;">'
                            f'<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #0288d1;">📝 Interpretación Financiera de los Resultados (Dinámico desde MySQL):</div>'
                            f'<ul style="margin: 0; padding-left: 20px; line-height: 1.6;">'
                            f'<li style="margin-bottom: 8px;"><b>🏢 Enterprise Value (Valor Operativo) — ${ev_val:,.2f}:</b> Es el valor total de la operación del negocio calculado en base a las premisas registradas en la base de datos.</li>'
                            f'<li style="margin-bottom: 8px;"><b>💵 Equity Value (Patrimonio) — ${eq_val:,.2f}:</b> Es el valor neto correspondiente a los accionistas. Al compararse con el Enterprise Value, refleja un ajuste por Deuda Neta de <b>${db_debt:,.2f}</b>.</li>'
                            f'<li style="margin-bottom: 0px;"><b>🌐 Valor Presente Terminal (PV TV) — ${pv_tv_val:,.2f}:</b> Es el valor actual de todos los flujos de caja a perpetuidad a partir del año {n_years + 1}. Representa el <b>{tv_pct:.2f}%</b> del valor total de la compañía, mientras que los flujos proyectados explícitos de los primeros {n_years} años aportan el <b>{fcf_pct:.2f}%</b> restante (<b>${pv_fcf_total:,.2f}</b>).</li>'
                            f'</ul>'
                            f'</div>'
                        )

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

                        # -------------------------------------------------------------------------
                        # MATRIZ DE SENSIBILIDAD (WACC vs. g)
                        # -------------------------------------------------------------------------
                        st.markdown("---")
                        st.subheader("🎯 Matriz de Sensibilidad (Valor del Patrimonio / Acción)")
                        st.caption("Evaluación de impacto sobre el Equity Value variando el WACC y la Tasa de Crecimiento Terminal ($g$):")

                        def generar_matriz_sensibilidad(fcf_proyectados, net_debt, shares_outstanding, base_wacc, base_g):
                            wacc_range = [base_wacc - 0.02, base_wacc - 0.01, base_wacc, base_wacc + 0.01, base_wacc + 0.02]
                            g_range = [base_g - 0.01, base_g - 0.005, base_g, base_g + 0.005, base_g + 0.01]
                            
                            matrix_data = []
                            for w in wacc_range:
                                row = []
                                for g in g_range:
                                    if w <= g:
                                        row.append(np.nan)
                                        continue
                                    
                                    pv_fcf = sum([fcf / ((1 + w) ** i) for i, fcf in enumerate(fcf_proyectados, 1)])
                                    tv = (fcf_proyectados[-1] * (1 + g)) / (w - g)
                                    pv_tv = tv / ((1 + w) ** len(fcf_proyectados))
                                    
                                    ev = pv_fcf + pv_tv
                                    equity_value = ev - net_debt
                                    val_final = equity_value / shares_outstanding if shares_outstanding > 0 else equity_value
                                    
                                    row.append(round(val_final, 2))
                                matrix_data.append(row)
                            
                            df_sens = pd.DataFrame(
                                matrix_data,
                                index=[f"WACC {w*100:.1f}%" for w in wacc_range],
                                columns=[f"g {g*100:.1f}%" for g in g_range]
                            )
                            return df_sens

                        df_matriz = generar_matriz_sensibilidad(
                            fcf_proyectados=results_db.free_cash_flows,
                            net_debt=db_debt,
                            shares_outstanding=db_shares,
                            base_wacc=db_wacc,
                            base_g=db_g
                        )

                        st.dataframe(
                            df_matriz.style.background_gradient(cmap="RdYlGn", axis=None).highlight_null(color="gray").format("${:,.2f}", na_rep="N/A"),
                            use_container_width=True
                        )

                else:
                    st.warning(f"⚠️ No hay datos guardados en las tablas raw para '{company_name}' / '{scenario_name}'. Ve a la Pestaña 1 e insértalos en MySQL.")

        except Exception as db_err:
            st.error(f"❌ Error al procesar datos desde MySQL: {db_err}")

    # -------------------------------------------------------------------------
    # PESTAÑA 3: GRÁFICOS
    # -------------------------------------------------------------------------
    with tab3:
        st.header("📈 Análisis Gráfico de Flujos")

        pv_flows = st.session_state.get("active_pv_cash_flows", None)
        nom_flows = st.session_state.get("active_nom_cash_flows", None)

        if pv_flows:
            # Crear DataFrame con índice numérico y string ordenable
            df_chart = pd.DataFrame(
                {
                    "Año Num": [i + 1 for i in range(len(pv_flows))],
                    "Año": [f"Año {i+1:02d}" for i in range(len(pv_flows))],
                    "PV FCF ($)": [float(val) for val in pv_flows],
                }
            )

            has_nominal = nom_flows and len(nom_flows) == len(pv_flows)
            if has_nominal:
                df_chart["FCF Nominal ($)"] = [float(val) for val in nom_flows]

            # Ordenar explícitamente por número de año
            df_chart = df_chart.sort_values("Año Num")

            # --- MÉTRICAS ---
            col_g1, col_g2 = st.columns(2)
            col_g1.metric("Total PV FCF", f"${sum(df_chart['PV FCF ($)']):,.2f}")
            col_g2.metric("Años Proyectados", f"{len(df_chart)} Años")

            st.subheader("Evolución del Valor Presente de los Flujos (PV FCF)")

            # Renderizar Gráfico
            df_plot = df_chart.set_index("Año")[
                [
                    col
                    for col in ["PV FCF ($)", "FCF Nominal ($)"]
                    if col in df_chart.columns
                ]
            ]
            st.bar_chart(df_plot)

            # --- CÁLCULO DE TENDENCIA DINÁMICA ---
            pv_inicial = df_chart["PV FCF ($)"].iloc[0]
            pv_final = df_chart["PV FCF ($)"].iloc[-1]
            diff_pct = (
                ((pv_final - pv_inicial) / abs(pv_inicial)) * 100
                if pv_inicial != 0
                else 0
            )

            # Determinar el mensaje de interpretación según la tendencia
            if diff_pct < -5:
                comportamiento = (
                    f"<b>Tendencia Decreciente:</b> El valor presente de los flujos disminuye un <b>{abs(diff_pct):.1f}%</b> "
                    f"desde el {df_chart['Año'].iloc[0]} (${pv_inicial:,.2f}) hasta el {df_chart['Año'].iloc[-1]} (${pv_final:,.2f}). "
                    f"Este comportamiento es típico en modelos DCF donde la tasa de descuento (WACC) erosiona el valor del dinero en el tiempo "
                    f"a un ritmo mayor del que crecen los flujos nominales operativos."
                )
            elif diff_pct > 5:
                comportamiento = (
                    f"<b>Tendencia Creciente:</b> El valor presente exhibe un crecimiento acumulado del <b>{diff_pct:.1f}%</b> "
                    f"a lo largo del período explicitado. Esto indica que la tasa de expansión del negocio en sus flujos operativos es "
                    f"lo suficientemente alta como para superar el efecto erosivo del descuento por tasa (WACC)."
                )
            else:
                comportamiento = (
                    f"<b>Comportamiento Plano/Estable:</b> Los flujos a valor presente se mantienen estables con una variación de solo el "
                    f"<b>{diff_pct:.1f}%</b> entre el primer y último año. Significa que el crecimiento operativo de la caja compensa casi "
                    f"de manera exacta la tasa de descuento aplicada en cada período."
                )

            # Agregar detalle de descuento si existen flujos nominales
            leyenda_comparativa = ""
            if has_nominal:
                nom_total = sum(df_chart["FCF Nominal ($)"])
                pv_total = sum(df_chart["PV FCF ($)"])
                descuento_total = nom_total - pv_total
                leyenda_comparativa = (
                    f"<li style='margin-top: 6px;'><b>Impacto de la Tasa de Descuento:</b> La suma de flujos nominales proyectados es de "
                    f"<b>${nom_total:,.2f}</b>, mientras que su valor presente se reduce a <b>${pv_total:,.2f}</b>, absorbiendo un impacto "
                    f"por riesgo/tiempo equivalente a <b>${descuento_total:,.2f}</b>.</li>"
                )

            # HTML Dinámico de Interpretación del Gráfico
            html_grafico_interpretation = (
                f'<div style="background-color: #e8f4f8; border-left: 5px solid #29b6f6; padding: 18px 20px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; color: #1a202c; margin-top: 20px; margin-bottom: 20px;">'
                f'<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #0288d1;">📊 Interpretación Dinámica del Perfil de Flujos:</div>'
                f'<ul style="margin: 0; padding-left: 20px; line-height: 1.6;">'
                f'<li style="margin-bottom: 8px;">{comportamiento}</li>'
                f"{leyenda_comparativa}"
                f'</ul>'
                f"</div>"
            )

            st.markdown(html_grafico_interpretation, unsafe_allow_html=True)

            with st.expander("🔍 Ver Tabla de Datos del Gráfico"):
                st.dataframe(
                    df_chart.style.format(
                        {
                            "PV FCF ($)": "${:,.2f}",
                            "FCF Nominal ($)": (
                                "${:,.2f}" if has_nominal else None
                            ),
                        }
                    ),
                    use_container_width=True,
                )
        else:
            st.info(
                "Consulta un escenario válido en MySQL para visualizar el gráfico."
            )

    # -------------------------------------------------------------------------
    # PESTAÑA 4: GESTOR DOCUMENTAL EN LA NUBE
    # -------------------------------------------------------------------------
    with tab4:
        st.subheader("📁 Gestor Documental en la Nube")
        st.markdown(
            "Sube y administra comprobantes, transferencias, PDFs o archivos de Office de forma organizada."
        )

        # --- LEYENDA EXPLICATIVA ---
        # Opción A: Usando HTML personalizado (siguiendo el estilo de html_interpretation)
        leyenda_archivos_html = (
            '<div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 15px 18px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; color: #856404; margin-bottom: 20px;">'
            '<div style="font-size: 1rem; font-weight: bold; margin-bottom: 6px; color: #856404;">⚠️ Nota sobre Archivos Demostrativos:</div>'
            '<div style="font-size: 0.95rem; line-height: 1.5;">'
            'Los archivos cargados previamente en esta sección corresponden a <b>datos demostrativos o de prueba</b> necesarios para el cálculo del flujo de caja de contado. '
            'Para realizar sus análisis financieros reales, <b>utilice este gestor para subir y reemplazar con sus propios archivos y datos</b>.'
            '</div>'
            '</div>'
        )
        st.markdown(leyenda_archivos_html, unsafe_allow_html=True)

        # Opción B (Alternativa rápida nativa de Streamlit):
        # st.info("ℹ️ **Archivos Demostrativos:** Los documentos presentes son de prueba para el cálculo del flujo de caja de contado. Por favor, utilice esta herramienta para subir sus propios datos financieros.")

        engine = get_sqlalchemy_engine()

        # Crear la tabla automáticamente si no existe en MySQL / TiDB
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    CREATE TABLE IF NOT EXISTS documentos_cloud (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        empresa_db VARCHAR(100) NOT NULL,
                        categoria VARCHAR(100) NOT NULL,
                        nombre_archivo VARCHAR(255) NOT NULL,
                        ruta_archivo VARCHAR(500) NOT NULL,
                        fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                )
        except Exception as e:
            st.error(f"Error al verificar la estructura de la base de datos: {e}")

        db_actual = st.session_state.get("DB_ACTUAL", company_name)
        if not db_actual or db_actual == "none":
            st.warning(
                "⚠️ Por favor, selecciona un Cliente/Empresa en la barra lateral o panel principal."
            )
        else:
            # Directorio base para almacenar los archivos por empresa
            DIRECTORIO_SUBIDAS = "documentos_clientes"
            dir_empresa = os.path.join(DIRECTORIO_SUBIDAS, str(db_actual))
            os.makedirs(dir_empresa, exist_ok=True)

            # --- FORMULARIO DE SUBIDA ---
            with st.expander("📤 Subir Nuevo Documento", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    categoria = st.selectbox(
                        "Categoría del Documento",
                        [
                            "Transferencia Bancaria",
                            "Factura PDF",
                            "Documento Legal",
                            "Excel / Reporte",
                            "Otro",
                        ],
                        key="cat_select_dcf",
                    )
                with col2:
                    archivos_subidos = st.file_uploader(
                        "Selecciona los archivos",
                        type=[
                            "pdf",
                            "docx",
                            "xlsx",
                            "xls",
                            "png",
                            "jpg",
                            "jpeg",
                            "txt",
                            "csv",
                        ],
                        accept_multiple_files=True,
                        key="doc_uploader_dcf",
                    )

                if st.button(
                    "💾 Guardar Documentos en la Nube",
                    type="primary",
                    use_container_width=True,
                    key="btn_guardar_doc_dcf",
                ):
                    if archivos_subidos:
                        try:
                            archivos_guardados = 0
                            for archivo in archivos_subidos:
                                timestamp_str = datetime.now().strftime(
                                    "%Y%m%d_%H%M%S"
                                )
                                nombre_limpio = f"{timestamp_str}_{archivo.name}"
                                ruta_completa = os.path.join(
                                    dir_empresa, nombre_limpio
                                )

                                # Guardar archivo en disco
                                with open(ruta_completa, "wb") as f:
                                    f.write(archivo.getbuffer())

                                # Insertar registro con SQLAlchemy
                                with engine.begin() as conn:
                                    conn.execute(
                                        text("""
                                        INSERT INTO documentos_cloud (empresa_db, categoria, nombre_archivo, ruta_archivo)
                                        VALUES (:empresa_db, :categoria, :nombre_archivo, :ruta_archivo)
                                    """),
                                        {
                                            "empresa_db": str(db_actual),
                                            "categoria": categoria,
                                            "nombre_archivo": archivo.name,
                                            "ruta_archivo": ruta_completa,
                                        },
                                    )
                                archivos_guardados += 1

                            st.success(
                                f"✅ ¡{archivos_guardados} archivo(s) guardado(s) correctamente!"
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al guardar los documentos: {e}")
                    else:
                        st.warning(
                            "⚠️ Debes seleccionar al menos un archivo antes de guardar."
                        )

            st.divider()

            # --- LISTADO, BÚSQUEDA, DESCARGA Y ELIMINACIÓN ---
            st.markdown("### 🗂️ Documentos Almacenados")

            try:
                # Consulta de documentos usando SQLAlchemy
                df_docs = pd.read_sql(
                    text("""
                        SELECT id, categoria, nombre_archivo, ruta_archivo, fecha_subida 
                        FROM documentos_cloud 
                        WHERE empresa_db = :empresa 
                        ORDER BY fecha_subida DESC
                    """),
                    con=engine,
                    params={"empresa": str(db_actual)},
                )

                if df_docs is not None and not df_docs.empty:
                    # Buscador rápido
                    filtro = st.text_input(
                        "🔍 Buscar documento por nombre o categoría:",
                        "",
                        key="search_docs_dcf",
                    )
                    if filtro:
                        df_docs = df_docs[
                            df_docs["nombre_archivo"].str.contains(
                                filtro, case=False, na=False
                            )
                            | df_docs["categoria"].str.contains(
                                filtro, case=False, na=False
                            )
                        ]

                    # Encabezados
                    h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns(
                        [3, 2, 2, 1, 1]
                    )
                    h_col1.markdown("**Nombre del Archivo**")
                    h_col2.markdown("**Categoría**")
                    h_col3.markdown("**Fecha**")
                    h_col4.markdown("**Descargar**")
                    h_col5.markdown("**Eliminar**")
                    st.divider()

                    # Listado de filas
                    for _, row in df_docs.iterrows():
                        cols = st.columns([3, 2, 2, 1, 1])
                        cols[0].write(f"📄 {row['nombre_archivo']}")
                        cols[1].write(f"🏷️ {row['categoria']}")
                        cols[2].write(str(row["fecha_subida"])[:10])

                        # Botón Descargar
                        if os.path.exists(row["ruta_archivo"]):
                            with open(
                                row["ruta_archivo"], "rb"
                            ) as file_to_download:
                                cols[3].download_button(
                                    label="⬇️",
                                    data=file_to_download,
                                    file_name=row["nombre_archivo"],
                                    mime="application/octet-stream",
                                    key=f"down_{row['id']}_dcf",
                                )
                        else:
                            cols[3].caption("⚠️ No hallado")

                        # Botón Eliminar
                        if cols[4].button("🗑️", key=f"del_{row['id']}_dcf"):
                            try:
                                # 1. Eliminar del disco si existe
                                if os.path.exists(row["ruta_archivo"]):
                                    os.remove(row["ruta_archivo"])

                                # 2. Eliminar registro en base de datos
                                with engine.begin() as conn:
                                    conn.execute(
                                        text(
                                            "DELETE FROM documentos_cloud WHERE id = :id"
                                        ),
                                        {"id": row["id"]},
                                    )

                                st.success(
                                    f"🗑️ Documento '{row['nombre_archivo']}' eliminado."
                                )
                                st.rerun()
                            except Exception as ex_del:
                                st.error(f"❌ Error al eliminar: {ex_del}")
                else:
                    st.info(
                        "ℹ️ No hay documentos subidos para esta empresa todavía."
                    )
            except Exception as e:
                st.error(f"Error al cargar la lista de documentos: {e}")


    # -------------------------------------------------------------------------
    # PESTAÑA 5: DICTAMEN Y CONCLUSIÓN FINANCIERA PARA INVERSIONISTAS
    # -------------------------------------------------------------------------
    with tab5:
        st.header("📌 Dictamen Técnico-Económico y Tesis de Inversión")
        st.caption("Análisis cualitativo y cuantitativo consolidado para la toma de decisiones estratégicas.")

        # 1. Obtener motor de BD
        try:
            engine = get_sqlalchemy_engine()
        except Exception as e:
            st.error(f"❌ Error al conectar a la base de datos: {e}")
            engine = None

        if engine:
            # Obtener listas disponibles si no están en variables globales
            try:
                df_companies = pd.read_sql("SELECT DISTINCT company_name FROM excel_inputs_raw", con=engine)
                list_companies = df_companies["company_name"].dropna().tolist()
            except Exception:
                list_companies = []

            if not list_companies:
                st.warning("⚠️ No se encontraron empresas registradas en la base de datos.")
            else:
                col_sel1, col_sel2 = st.columns(2)
                
                # Definir seleccionadores locales si no vienen del sidebar o estado global
                sel_company = col_sel1.selectbox("Empresa para Dictamen:", list_companies, key="tab5_company")
                
                df_scenarios = pd.read_sql(
                    text("SELECT DISTINCT scenario_name FROM excel_inputs_raw WHERE company_name = :c"),
                    con=engine, params={"c": sel_company}
                )
                list_scenarios = df_scenarios["scenario_name"].dropna().tolist()
                sel_scenario = col_sel2.selectbox("Escenario:", list_scenarios if list_scenarios else ["Base"], key="tab5_scenario")

                if st.button("🔍 Generar / Actualizar Dictamen Financiero", key="btn_gen_tab5"):
                    try:
                        # Consulta de Premisas
                        query_inputs = text("""
                            SELECT Parametro, Valor 
                            FROM excel_inputs_raw 
                            WHERE company_name = :company AND scenario_name = :scenario
                        """)
                        df_inputs = pd.read_sql(query_inputs, con=engine, params={"company": sel_company, "scenario": sel_scenario})

                        # Consulta de Flujos Descontados Proyectados
                        # ---------------------------------------------------------
                        # Consulta de Flujos Descontados Proyectados (Actualizado)
                        # ---------------------------------------------------------
                        query_projections = text("""
                            SELECT * 
                            FROM excel_projections_raw 
                            WHERE company_name = :company AND scenario_name = :scenario
                        """)
                        df_proj = pd.read_sql(query_projections, con=engine, params={"company": sel_company, "scenario": sel_scenario})

                        # Extraer la lista de flujos descontados de forma dinámica
                        pv_fcf_list = []
                        if not df_proj.empty:
                            # 1. Buscar la columna 'FCF_Descontado' (case-insensitive) o similares
                            target_col = None
                            for col in df_proj.columns:
                                if col.lower() in ["fcf_descontado", "fcf_descontados", "pv_fcf", "flujo_descontado"]:
                                    target_col = col
                                    break
                            
                            # 2. Si encuentra la columna, parsear los valores
                            if target_col:
                                pv_fcf_list = pd.to_numeric(df_proj[target_col], errors="coerce").dropna().tolist()

                        # 3. Fallback: Si la consulta no trae datos o la columna no existe, usar session_state
                        if not pv_fcf_list:
                            pv_fcf_list = st.session_state.get("active_pv_cash_flows", [0.0])

                            def parse_val(val, default=0.0):
                                if pd.isna(val) or val is None: return float(default)
                                v_str = str(val).replace("$", "").replace(",", "").strip()
                                if "%" in v_str: return float(v_str.replace("%", "")) / 100.0
                                return float(v_str)

                            wacc_val = parse_val(inputs_dict.get("wacc"), 0.10)
                            if wacc_val > 1.0: wacc_val /= 100.0
                            g_val = parse_val(inputs_dict.get("terminal_growth_rate"), 0.025)
                            if g_val > 1.0: g_val /= 100.0
                            debt_val = parse_val(inputs_dict.get("net_debt"), 0.0)

                            # Recuperar / Calcular Flujos
                            if not df_proj.empty and "FCF_Descontado" in df_proj.columns:
                                pv_fcf_list = df_proj["FCF_Descontado"].astype(float).tolist()
                            else:
                                pv_fcf_list = st.session_state.get("active_pv_cash_flows", [100000.0])

                            pv_fcf_total = sum(pv_fcf_list)
                            
                            # Estimación de Enterprise Value (EV) y Valor Terminal (TV)
                            ev_est = st.session_state.get("ev_val", pv_fcf_total * 1.5 if pv_fcf_total > 0 else 1.0)
                            tv_est = st.session_state.get("pv_tv_val", max(0.0, ev_est - pv_fcf_total))
                            tv_dependency = (tv_est / ev_est * 100) if ev_est > 0 else 0.0

                            st.markdown("---")

                            # ---------------------------------------------------------
                            # 1. TARJETAS DE VEREDICTO RÁPIDO (KPIs)
                            # ---------------------------------------------------------
                            st.subheader("1. Veredicto del Comité de Inversión")
                            
                            col_v1, col_v2, col_v3 = st.columns(3)
                            
                            if tv_dependency > 75:
                                riesgo_status = "🔴 RIESGO ALTO"
                                recom_status = "MANTENER / REVISAR"
                            elif tv_dependency > 60:
                                riesgo_status = "🟡 RIESGO MODERADO"
                                recom_status = "ATRACTIVO CON CONDICIONES"
                            else:
                                riesgo_status = "🟢 RIESGO BAJO (Caja Sólida)"
                                recom_status = "COMPRAR / INVERTIR"

                            col_v1.metric("Estatus de Recomendación", recom_status)
                            col_v2.metric("Perfil de Riesgo del FCF", riesgo_status)
                            col_v3.metric("Dependencia Valor Terminal", f"{tv_dependency:.1f}%")

                            st.markdown("---")

                            # ---------------------------------------------------------
                            # 2. CUADRO DETALLADO: 5 EJES ESTRATÉGICOS
                            # ---------------------------------------------------------
                            st.subheader("2. Matriz de Evaluación Técnico-Económica")

                            matriz_conclusion = [
                                {
                                    "Eje de Análisis": "1. Estructura de Valoración",
                                    "Diagnóstico Técnico": f"Enterprise Value soportado en una tasa WACC del {wacc_val:.2%} y Deuda Neta de ${debt_val:,.2f}.",
                                    "Implicación para el Inversionista": "El ajuste por Deuda Neta impacta directamente el Equity Value. Se debe verificar si la deuda es a tasa fija o variable."
                                },
                                {
                                    "Eje de Análisis": "2. Calidad del Flujo de Caja",
                                    "Diagnóstico Técnico": f"Los flujos explícitos aportan ${pv_fcf_total:,.2f}, mientras que el Valor Terminal representa el {tv_dependency:.1f}% del total.",
                                    "Implicación para el Inversionista": "Alta concentración en el Valor Terminal implica mayor sensibilidad a supuestos macroeconómicos de largo plazo."
                                },
                                {
                                    "Eje de Análisis": "3. Sensibilidad y Perpetuidad (g)",
                                    "Diagnóstico Técnico": f"Tasa de crecimiento perpetuo proyectada en {g_val:.2%}, comparada contra un WACC del {wacc_val:.2%}.",
                                    "Implicación para el Inversionista": f"La brecha Spread (WACC - g) es de {(wacc_val - g_val)*100:.2f} % pts. Un aumento imprevisto en la tasa de descuento afectará la valoración patrimonial."
                                },
                                {
                                    "Eje de Análisis": "4. Política de Capital y Reinversión",
                                    "Diagnóstico Técnico": "El modelo asume reinversión continua en CapEx y Trabajo Netos Operativos (NWC) para sostener la tasa g.",
                                    "Implicación para el Inversionista": "Validar si el ROIC (Retorno sobre Capital Invertido) supera el WACC para asegurar creación de valor real."
                                },
                                {
                                    "Eje de Análisis": "5. Dictamen Final de Inversión",
                                    "Diagnóstico Técnico": f"Evaluación global del escenario '{sel_scenario}' para la empresa '{sel_company}'.",
                                    "Implicación para el Inversionista": "Aprobar la inversión sujeto a auditoría de contratos de ingresos y monitoreo trimestral del Margen EBIT."
                                }
                            ]

                            df_dictamen = pd.DataFrame(matriz_conclusion)
                            st.table(df_dictamen)

                            st.markdown("---")

                            # ---------------------------------------------------------
                            # 3. NARRATIVA EJECUTIVA (REPORTE FORMAL)
                            # ---------------------------------------------------------
                            html_reporte = f"""
                            <div style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 25px; font-family: sans-serif;">
                                <h4 style="color: #1e3a8a; margin-top: 0;">📋 Informe Ejecutivo de Cierre (Due Diligence)</h4>
                                <p style="line-height: 1.6; color: #334155;">
                                    <b>Conclusión del Analista:</b> La valoración bajo el método de Flujo de Caja Descontado (DCF) para <b>{sel_company}</b> 
                                    demuestra una estructura operativa sostenible. Sin embargo, dado que el <b>{tv_dependency:.1f}%</b> del valor proviene de la perpetuidad, 
                                    la decisión de inversión debe complementarse con una auditoría continua del cumplimiento del Margen EBIT proyectado.
                                </p>
                                <h5 style="color: #1e3a8a; margin-bottom: 8px;">Recomendaciones Tácticas para los Inversionistas:</h5>
                                <ul style="line-height: 1.6; color: #334155; padding-left: 20px;">
                                    <li><b>Estrategia de Entrada:</b> Negociar un descuento sobre el Equity Value resultante si las tasas de interés presentan tendencia alcista.</li>
                                    <li><b>Cláusulas de Protección:</b> Condicionar desembolsos futuros al cumplimiento de las metas FCF en los Años 1 y 2.</li>
                                    <li><b>Monitoreo de CapEx:</b> Verificar que la ejecución de CapEx coincida con las premisas del modelo para asegurar el crecimiento proyectado.</li>
                                </ul>
                            </div>
                            """
                            st.markdown(html_reporte, unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f"❌ Error al procesar la conclusión financiera: {e}")

if __name__ == "__main__":
    render()