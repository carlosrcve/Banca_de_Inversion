'''
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
    def get_market_quotes():
        """Obtiene todas las cotizaciones guardadas en la tabla market_quotes."""
        try:
            engine = get_sqlalchemy_engine()
            with engine.connect() as conn:
                query = text("""
                    SELECT symbol, asset_name, asset_type, price, change_percent, updated_at 
                    FROM market_quotes 
                    ORDER BY updated_at DESC
                """)
                result = conn.execute(query)
                rows = [dict(row._mapping) for row in result]
                return rows
        except Exception as e:
            print(f"❌ Error al consultar cotizaciones: {e}")
            return []

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
'''

# portfolio_controller.py
import os
import sys
import ssl
import pymysql
from sqlalchemy import create_engine, text

# Garantiza que el directorio raíz esté en el path de ejecución
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def get_sqlalchemy_engine():
    """Crea el motor SQLAlchemy optimizado para TiDB Cloud con SSL."""
    ssl_context = ssl.create_default_context()
    connection_url = "mysql+pymysql://4K4VAw4t4ZPFUTF.root:I1lVZQDq2d4KJbQA@gateway01.us-east-1.prod.aws.tidbcloud.com:4000/valuations_db"
    return create_engine(
        connection_url,
        connect_args={"ssl": ssl_context},
        pool_recycle=3600
    )


def get_secure_db_connection():
    """Conexión segura basada en PyMySQL con SSL para TiDB Cloud (reemplazo seguro de get_db_connection)."""
    try:
        ssl_context = ssl.create_default_context()
        connection = pymysql.connect(
            host="gateway01.us-east-1.prod.aws.tidbcloud.com",
            port=4000,
            user="4K4VAw4t4ZPFUTF.root",
            password="I1lVZQDq2d4KJbQA",
            database="valuations_db",
            ssl=ssl_context,
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"🔥 Error conectando a TiDB con SSL: {e}")
        return None


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
    def get_market_quotes():
        """Obtiene todas las cotizaciones guardadas en la tabla market_quotes."""
        try:
            engine = get_sqlalchemy_engine()
            with engine.connect() as conn:
                query = text("""
                    SELECT symbol, asset_name, asset_type, price, change_percent, updated_at 
                    FROM market_quotes 
                    ORDER BY updated_at DESC
                """)
                result = conn.execute(query)
                rows = [dict(row._mapping) for row in result]
                return rows
        except Exception as e:
            print(f"❌ Error al consultar cotizaciones: {e}")
            return []

    @staticmethod
    def create_portfolio(
        portfolio_name: str, description: str, assets: list
    ) -> tuple[bool, str | None]:
        """Crea un portafolio y sus activos usando exactamente los nombres reales de la BD."""
        import traceback
        try:
            engine = get_sqlalchemy_engine()
            with engine.begin() as conn:
                # 1. Insertar el portafolio usando la columna real 'name'
                query_portfolio = text("""
                    INSERT INTO portfolios (name, description)
                    VALUES (:name, :description)
                """)
                result = conn.execute(query_portfolio, {
                    "name": portfolio_name,
                    "description": description
                })
                portfolio_id = result.lastrowid

                # 2. Insertar los activos usando los nombres exactos del CREATE TABLE
                query_asset = text("""
                    INSERT INTO portfolio_assets 
                    (portfolio_id, ticker, asset_name, asset_class, quantity, purchase_price, acquisition_date)
                    VALUES (:portfolio_id, :ticker, :asset_name, :asset_class, :quantity, :purchase_price, :acquisition_date)
                """)
                
                for item in assets:
                    conn.execute(query_asset, {
                        "portfolio_id": portfolio_id,
                        "ticker": item.get("symbol") or item.get("ticker"),
                        "asset_name": item.get("asset_name"),
                        "asset_class": item.get("asset_type") or item.get("asset_class"),
                        "quantity": item.get("quantity"),
                        "purchase_price": item.get("purchase_price"),
                        "acquisition_date": item.get("purchase_date") or item.get("acquisition_date")
                    })
                    
            return True, None
        except Exception as e:
            traceback.print_exc()
            return False, str(e)
            
    @staticmethod
    def get_portfolios():
        """Obtiene la lista de portafolios mapeando 'name' como 'portfolio_name' para la vista de Streamlit."""
        conn = get_secure_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            # Seleccionamos 'name AS portfolio_name' para que encaje perfecto con el render de Streamlit
            query = "SELECT id, name AS portfolio_name, description, created_at FROM portfolios ORDER BY id DESC"
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

    @staticmethod
    def get_portfolio_assets(portfolio_id: int):
        """Obtiene los activos y los mapea a los nombres que espera el DataFrame de Streamlit."""
        conn = get_secure_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            # Mapeamos 'ticker AS symbol' y 'asset_class AS asset_type' para mantener compatibilidad total con el render
            query = """
                SELECT ticker AS symbol, asset_name, asset_class AS asset_type, quantity, purchase_price, acquisition_date AS purchase_date 
                FROM portfolio_assets 
                WHERE portfolio_id = %s
            """
            cursor.execute(query, (portfolio_id,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as e:
            print(f"Error al consultar activos del portafolio: {e}")
            if conn:
                conn.close()
            return []