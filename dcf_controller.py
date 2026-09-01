# dcf_controller.py
import os
from typing import Any, Dict, List, Optional
import mysql.connector
from mysql.connector import Error
from dcf_engine import DCFEngine
from dcf_models import DCFInputs, DCFResults


def get_db_connection():
    """Establece la conexión segura SSL con TiDB Cloud o MySQL.

    Prioriza la lectura desde st.secrets (Streamlit) y utiliza os.getenv como
    fallback.
    """
    try:
        try:
            import streamlit as st

            host = st.secrets.get(
                "MYSQL_HOST",
                os.getenv(
                    "MYSQL_HOST", "gateway01.us-east-1.prod.aws.tidbcloud.com"
                ),
            )
            user = st.secrets.get("MYSQL_USER", os.getenv("MYSQL_USER", "root"))
            password = st.secrets.get(
                "MYSQL_PASSWORD", os.getenv("MYSQL_PASSWORD", "")
            )
            database = st.secrets.get(
                "MYSQL_DATABASE", os.getenv("MYSQL_DATABASE", "valuations_db")
            )
            port = int(
                st.secrets.get("MYSQL_PORT", os.getenv("MYSQL_PORT", 4000))
            )
        except (ImportError, Exception):
            host = os.getenv("MYSQL_HOST", "localhost")
            user = os.getenv("MYSQL_USER", "root")
            password = os.getenv("MYSQL_PASSWORD", "")
            database = os.getenv("MYSQL_DATABASE", "valuations_db")
            port = int(os.getenv("MYSQL_PORT", 3306))

        config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "autocommit": False,
        }

        if "tidbcloud.com" in host or port == 4000:
            config["ssl_verify_cert"] = True
            config["ssl_verify_identity"] = True

        return mysql.connector.connect(**config)

    except Error as e:
        print(f"Error al conectar a TiDB Cloud / MySQL: {e}")
        return None


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
        inputs = DCFInputs(
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
                inputs.historical_revenue,
                inputs.tax_rate,
                inputs.capex_percent,
                inputs.nwc_percent,
                inputs.da_percent,
                inputs.wacc,
                inputs.terminal_growth_rate,
                inputs.net_debt,
                results.terminal_value,
                results.pv_terminal_value,
                results.enterprise_value,
                results.equity_value,
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
                    inputs.growth_rates[i],
                    inputs.ebit_margins[i],
                    results.projected_revenues[i],
                    results.projected_ebit[i],
                    results.projected_nopat[i],
                    results.free_cash_flows[i],
                    results.pv_cash_flows[i],
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