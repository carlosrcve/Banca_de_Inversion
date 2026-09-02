# dcf_controller.py
import os
from typing import Any, Dict, List, Optional
import mysql.connector
from mysql.connector import Error
from sqlalchemy import create_engine

from dcf_engine import DCFEngine
from dcf_models import DCFInputs, DCFResults


def get_db_credentials() -> dict:
    """Extrae las credenciales probando st.secrets y fallbacks de variables de entorno."""
    credentials = {
        "host": os.getenv("MYSQL_HOST", "gateway01.us-east-1.prod.aws.tidbcloud.com"),
        "user": os.getenv("MYSQL_USER", ""),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "valuations_db"),
        "port": int(os.getenv("MYSQL_PORT", 4000)),
    }

    try:
        import streamlit as st

        if "mysql" in st.secrets:
            sec = st.secrets["mysql"]
            credentials["host"] = sec.get("host", credentials["host"])
            credentials["user"] = sec.get("user", credentials["user"])
            credentials["password"] = sec.get("password", credentials["password"])
            credentials["database"] = sec.get("database", credentials["database"])
            credentials["port"] = int(sec.get("port", credentials["port"]))
        else:
            credentials["host"] = st.secrets.get("MYSQL_HOST", credentials["host"])
            credentials["user"] = st.secrets.get("MYSQL_USER", credentials["user"])
            credentials["password"] = st.secrets.get("MYSQL_PASSWORD", credentials["password"])
            credentials["database"] = st.secrets.get("MYSQL_DATABASE", credentials["database"])
            credentials["port"] = int(st.secrets.get("MYSQL_PORT", credentials["port"]))

    except Exception:
        pass

    return credentials


def get_db_connection():
    """Establece conexión nativa con TiDB Cloud usando credenciales fijas y SSL."""
    try:
        # Contexto SSL obligatorio para TiDB Cloud
        ssl_context = ssl.create_default_context()
        
        connection = pymysql.connect(
            host="gateway01.us-east-1.prod.aws.tidbcloud.com",
            port=4000,
            user="4K4VAw4t4ZPFUTF.root",
            password="I1lVZQDq2d4KJbQA",
            database="valuations_db",
            ssl=ssl_context,
            connect_timeout=15
        )
        return connection
    except Exception as e:
        print(f"🔥 ERROR REAL DE CONEXIÓN EN dcf_controller.py: {repr(e)}")
        return None


def get_sqlalchemy_engine():
    """Genera el Engine de SQLAlchemy para Pandas."""
    creds = get_db_credentials()
    db_url = f"mysql+pymysql://{creds['user']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}"
    return create_engine(db_url)


def _to_decimal(val: float) -> float:
    """Asegura que las tasas de % estén expresadas en rango 0.0 - 1.0 (ej. 15 -> 0.15)."""
    val = float(val)
    return val / 100.0 if abs(val) > 1.0 else val


class DCFController:
    """Controlador central para los cálculos DCF y su persistencia en BD."""

    @staticmethod
    def run_valuation(
        historical_revenue: float,
        growth_rates: List[float],
        ebit_margins: List[float],
        tax_rate: float,
        capex_percent: float,
        nwc_percent: float,
        da_percent: float,
        wacc: float,
        terminal_growth_rate: float,
        net_debt: float,
    ) -> DCFResults:
        
        # Sanitizar valores % para evitar errores de escala (15.0 -> 0.15)
        clean_growth = [_to_decimal(g) for g in growth_rates]
        clean_ebit = [_to_decimal(m) for m in ebit_margins]

        inputs = DCFInputs(
            historical_revenue=float(historical_revenue),
            growth_rates=clean_growth,
            ebit_margins=clean_ebit,
            tax_rate=_to_decimal(tax_rate),
            capex_percent=_to_decimal(capex_percent),
            nwc_percent=_to_decimal(nwc_percent),
            da_percent=_to_decimal(da_percent),
            wacc=_to_decimal(wacc),
            terminal_growth_rate=_to_decimal(terminal_growth_rate),
            net_debt=float(net_debt),
        )
        return DCFEngine.calculate(inputs)

    @classmethod
    def save_valuation(
        cls,
        company_name: str,
        scenario_name: str,
        inputs: DCFInputs,
        results: DCFResults,
    ) -> bool:
        conn = get_db_connection()
        if not conn:
            return False

        cursor = conn.cursor()
        try:
            query_company = """
                INSERT INTO companies (name) 
                VALUES (%s) 
                ON DUPLICATE KEY UPDATE company_id=LAST_INSERT_ID(company_id);
            """
            cursor.execute(query_company, (company_name,))
            company_id = cursor.lastrowid

            query_analysis = """
                INSERT INTO dcf_analyses (
                    company_id, scenario_name, historical_revenue, tax_rate,
                    capex_percent, nwc_percent, da_percent, wacc,
                    terminal_growth_rate, net_debt, terminal_value,
                    pv_terminal_value, enterprise_value, equity_value
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            analysis_data = (
                company_id,
                scenario_name,
                float(inputs.historical_revenue),
                float(inputs.tax_rate),
                float(inputs.capex_percent),
                float(inputs.nwc_percent),
                float(inputs.da_percent),
                float(inputs.wacc),
                float(inputs.terminal_growth_rate),
                float(inputs.net_debt),
                float(results.terminal_value),
                float(results.pv_terminal_value),
                float(results.enterprise_value),
                float(results.equity_value),
            )
            cursor.execute(query_analysis, analysis_data)
            analysis_id = cursor.lastrowid

            query_yearly = """
                INSERT INTO dcf_yearly_projections (
                    analysis_id, year_number, growth_rate, ebit_margin,
                    projected_revenue, projected_ebit, projected_nopat,
                    free_cash_flow, pv_cash_flow
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """

            yearly_records = []
            for i in range(len(inputs.growth_rates)):
                record = (
                    analysis_id,
                    i + 1,
                    float(inputs.growth_rates[i]),
                    float(inputs.ebit_margins[i]),
                    float(results.projected_revenues[i]),
                    float(results.projected_ebit[i]),
                    float(results.projected_nopat[i]),
                    float(results.free_cash_flows[i]),
                    float(results.pv_cash_flows[i]),
                )
                yearly_records.append(record)

            cursor.executemany(query_yearly, yearly_records)
            conn.commit()
            return True

        except Error as e:
            conn.rollback()
            print(f"Error al guardar la valoración: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @classmethod
    def get_saved_scenarios(cls, company_name: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        if not conn:
            return []

        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT a.analysis_id, a.scenario_name, a.enterprise_value, a.equity_value, a.created_at
                FROM dcf_analyses a
                JOIN companies c ON a.company_id = c.company_id
                WHERE c.name = %s
                ORDER BY a.created_at DESC;
            """
            cursor.execute(query, (company_name,))
            return cursor.fetchall()
        except Error as e:
            print(f"Error al consultar escenarios: {e}")
            return []
        finally:
            cursor.close()
            conn.close()


def calculate_dcf(
    revenue: float,
    growth_rates: List[float],
    ebit_margins: List[float],
    tax_rate: float,
    capex_pct: float,
    nwc_pct: float,
    da_pct: float,
    wacc: float,
    g: float,
    net_debt: float,
) -> DCFResults:
    return DCFController.run_valuation(
        historical_revenue=revenue,
        growth_rates=growth_rates,
        ebit_margins=ebit_margins,
        tax_rate=tax_rate,
        capex_percent=capex_pct,
        nwc_percent=nwc_pct,
        da_percent=da_pct,
        wacc=wacc,
        terminal_growth_rate=g,
        net_debt=net_debt,
    )