# portfolio_controller.py
import os
import sys
import ssl
from sqlalchemy import create_engine, text

# Garantiza que el directorio raíz esté en el path de ejecución
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dcf_controller import get_db_connection


def get_sqlalchemy_engine():
    """Crea el motor SQLAlchemy optimizado para TiDB Cloud con SSL."""
    ssl_context = ssl.create_default_context()
    connection_url = "mysql+pymysql://4K4VAw4t4ZPFUTF.root:I1lVZQDq2d4KJbQA@gateway01.us-east-1.prod.aws.tidbcloud.com:4000/valuations_db"
    return create_engine(
        connection_url,
        connect_args={"ssl": ssl_context},
        pool_recycle=3600
    )


class PortfolioController:

    @staticmethod
    def save_market_quote(symbol, asset_name, asset_type, price, change_percent):
        """Guarda una cotización usando SQLAlchemy autónomo."""
        try:
            engine = get_sqlalchemy_engine()
            with engine.begin() as conn:
                query = text("""
                    INSERT INTO market_quotes (symbol, asset_name, asset_type, price, change_percent)
                    VALUES (:symbol, :asset_name, :asset_type, :price, :change_percent)
                """)
                conn.execute(query, {
                    "symbol": symbol,
                    "asset_name": asset_name,
                    "asset_type": asset_type,
                    "price": price,
                    "change_percent": change_percent
                })
            return True, ""
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Error al guardar cotización: {e}")
            return False, error_msg

    @staticmethod
    def create_portfolio(
        portfolio_name: str, description: str, assets: list
    ) -> bool:
        """Crea un nuevo portafolio e inserta sus activos dentro de una transacción."""
        conn = get_db_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            query_portfolio = """
                INSERT INTO portfolios (portfolio_name, description)
                VALUES (%s, %s)
            """
            cursor.execute(query_portfolio, (portfolio_name, description))
            portfolio_id = cursor.lastrowid

            query_asset = """
                INSERT INTO portfolio_assets (portfolio_id, symbol, asset_name, asset_type, quantity, purchase_price, purchase_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            for item in assets:
                cursor.execute(
                    query_asset,
                    (
                        portfolio_id,
                        item["symbol"],
                        item["asset_name"],
                        item["asset_type"],
                        item["quantity"],
                        item["purchase_price"],
                        item["purchase_date"],
                    ),
                )

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al crear el portafolio en TiDB: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
                conn.close()
            return False

    @staticmethod
    def get_portfolios():
        """Obtiene la lista de todos los portafolios guardados."""
        conn = get_db_connection()
        if not conn:
            return []

        try:
            try:
                cursor = conn.cursor(dictionary=True)
            except (TypeError, AttributeError):
                import pymysql

                cursor = conn.cursor(pymysql.cursors.DictCursor)

            query = "SELECT id, portfolio_name, description, created_at FROM portfolios ORDER BY id DESC"
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as e:
            print(f"Error al consultar portafolios: {e}")
            if conn:
                conn.close()
            return []