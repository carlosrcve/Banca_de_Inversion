# portfolio_controller.py
# portfolio_controller.py
import os
import sys

# Garantiza que el directorio raíz esté en el path de ejecución
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dcf_controller import get_db_connection


class PortfolioController:

    @staticmethod
    def save_market_quote(symbol, asset_name, asset_type, price, change_percent):
        """Guarda una cotización usando SQLAlchemy de forma idéntica al resto de la app."""
        try:
            engine = get_sqlalchemy_engine()  # Usa el mismo motor configurado en tu app
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
            # 1. Insertar el portafolio
            query_portfolio = """
                INSERT INTO portfolios (portfolio_name, description)
                VALUES (%s, %s)
            """
            cursor.execute(query_portfolio, (portfolio_name, description))
            portfolio_id = cursor.lastrowid

            # 2. Insertar cada activo vinculado al portfolio_id
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