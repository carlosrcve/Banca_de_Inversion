# portfolio_controller.py
import os
import sys

# Garantiza que el directorio raíz esté en el path de ejecución
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dcf_controller import get_db_connection



class PortfolioController:

    @staticmethod
    def save_market_quote(
        symbol: str,
        asset_name: str,
        asset_type: str,
        price: float,
        change_percent: float,
    ) -> bool:
        """Inserta una cotización de mercado en la tabla market_quotes de TiDB Cloud."""
        conn = get_db_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO market_quotes (symbol, asset_name, asset_type, price, change_percent)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(
                query,
                (symbol, asset_name, asset_type, price, change_percent),
            )
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al guardar cotización en TiDB: {e}")
            if conn:
                conn.close()
            return False

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
                conn.rollback()
                conn.close()
            return False

    @staticmethod
    def get_portfolios():
        """Obtiene la lista de todos los portafolios guardados."""
        conn = get_db_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor(dictionary=True)
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