# modules/mod_portofolio.py
from datetime import date
import pandas as pd
import streamlit as st
import yfinance as yf
from portfolio_controller import PortfolioController

@st.cache_data(ttl=600)  # Cacheamos los precios por 10 minutos
def get_live_price(ticker: str) -> float:
    """Obtiene el precio de cierre más reciente para un ticker dado."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return 0.0
    except Exception as e:
        print(f"Error obteniendo precio para {ticker}: {e}")
        return 0.0

def render():
    st.title("💼 Módulo de Gestión de Portafolio & Persistencia")
    st.markdown("""
    Crea, administra y consulta tus carteras corporativas e inversiones registradas directamente en **TiDB Cloud / MySQL**.
    """)

    tab1, tab2 = st.tabs(["➕ Crear Portafolio", "📂 Mis Portafolios Guardados"])

    with tab1:
        st.subheader("Crear Nueva Cartera / Portafolio de Inversión")

        p_name = st.text_input("Nombre del Portafolio", value="Portafolio Crecimiento Tech 2026", key="input_p_name")
        p_desc = st.text_area("Descripción / Estrategia", value="Estrategia enfocada en tecnológicas de alta capitalización y cobertura en commodities.", key="input_p_desc")

        st.markdown("---")
        st.write("#### Agregar Activos a la Cartera")

        if "temp_assets" not in st.session_state:
            st.session_state.temp_assets = []

        with st.form("form_add_asset", clear_on_submit=True):
            col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)
            with col_a1:
                a_sym = st.text_input("Ticker", value="NVDA").upper()
            with col_a2:
                a_name = st.text_input("Nombre Activo", value="NVIDIA Corp.")
            with col_a3:
                a_type = st.selectbox("Clase de Activo", ["Equity", "Commodity", "Index", "Crypto"])
            with col_a4:
                a_qty = st.number_input("Cantidad", min_value=0.01, value=10.0, format="%.2f")
            with col_a5:
                a_price = st.number_input("Precio Compra ($)", min_value=0.01, value=125.50, format="%.2f")

            a_date = st.date_input("Fecha de Adquisición", value=date.today())

            submitted_asset = st.form_submit_button("➕ Agregar Activo a la Lista")
            if submitted_asset:
                st.session_state.temp_assets.append({
                    "symbol": a_sym,
                    "asset_name": a_name,
                    "asset_type": a_type,
                    "quantity": a_qty,
                    "purchase_price": a_price,
                    "purchase_date": str(a_date),
                })
                st.success(f"Activo '{a_sym}' agregado a la vista previa.")

        if st.session_state.temp_assets:
            st.markdown("---")
            st.write("##### 📋 Vista Previa de Activos a Guardar:")
            df_temp = pd.DataFrame(st.session_state.temp_assets)
            st.dataframe(df_temp, use_container_width=True)

            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                if st.button("🗑️ Limpiar Lista", type="secondary"):
                    st.session_state.temp_assets = []
                    st.rerun()

            if st.button("💾 Guardar Portafolio Completo en TiDB Cloud", type="primary"):
                if not p_name.strip():
                    st.warning("⚠️ Por favor, ingresa un nombre para el portafolio.")
                else:
                    success, error_msg = PortfolioController.create_portfolio(
                        p_name, p_desc, st.session_state.temp_assets
                    )
                    if success:
                        st.success(f"✅ Portafolio '{p_name}' guardado exitosamente en TiDB Cloud.")
                        st.session_state.temp_assets = []
                        st.rerun()
                    else:
                        st.error(f"❌ Error exacto de MySQL/SQLAlchemy: {error_msg}")

    with tab2:
        st.subheader("Consultar Portafolios Almacenados")
        
        try:
            portfolios = PortfolioController.get_portfolios()
            
            if portfolios:
                st.success(f"Se encontraron {len(portfolios)} portafolios en TiDB Cloud.")
                for p in portfolios:
                    p_id = p["id"] if isinstance(p, dict) else p[0]
                    p_name = p["portfolio_name"] if isinstance(p, dict) else p[1]
                    p_desc = p["description"] if isinstance(p, dict) else p[2]
                    p_date = p["created_at"] if isinstance(p, dict) else p[3]

                    with st.expander(f"📁 **{p_name}** (Creado: {p_date})"):
                        st.write(f"**Descripción:** {p_desc}")
                        st.markdown("---")
                        render_portfolio_dashboard_inner(p_id)
            else:
                st.info("No se encontraron portafolios registrados en TiDB Cloud.")
                
        except Exception as db_error:
            st.error(f"❌ Error crítico de conexión con TiDB Cloud: {db_error}")

def render_portfolio_dashboard_inner(portfolio_id: int):
    """Calcula precios en vivo con yfinance y muestra las métricas y rentabilidad."""
    
    # 🚨 PRUEBA DE FUEGO: Si ves este error rojo en la web, el archivo nuevo ya cargó.
    st.error(f"🔥 SÍ ESTOY ENTRANDO A LA NUEVA FUNCIÓN (ID: {portfolio_id})")

    assets = PortfolioController.get_portfolio_assets(portfolio_id)
    
    if not assets:
        st.warning(f"⚠️ No hay activos registrados para este portafolio (ID: {portfolio_id}).")
        return

    portfolio_data = []
    total_investment = 0.0
    total_current_value = 0.0

    for asset in assets:
        try:
            # Compatibilidad total: soporta tanto diccionarios como filas de tuplas de SQL
            if isinstance(asset, dict):
                symbol = asset.get("symbol", "NVDA")
                name = asset.get("asset_name", "N/A")
                asset_type = asset.get("asset_type", "Equity")
                quantity = float(asset.get("quantity", 0.0))
                purchase_price = float(asset.get("purchase_price", 0.0))
            else:
                symbol = asset[1] if len(asset) > 1 else "NVDA"
                name = asset[2] if len(asset) > 2 else "N/A"
                asset_type = asset[3] if len(asset) > 3 else "Equity"
                quantity = float(asset[4]) if len(asset) > 4 else 0.0
                purchase_price = float(asset[5]) if len(asset) > 5 else 0.0
            
            current_price = get_live_price(symbol)
            if current_price == 0.0:
                current_price = purchase_price  
                
            inv_cost = quantity * purchase_price
            curr_val = quantity * current_price
            pnl = curr_val - inv_cost
            pnl_pct = ((current_price - purchase_price) / purchase_price) * 100 if purchase_price > 0 else 0
            
            total_investment += inv_cost
            total_current_value += curr_val
            
            portfolio_data.append({
                "Símbolo": symbol,
                "Activo": name,
                "Tipo": asset_type,
                "Cant.": quantity,
                "Precio Compra": f"${purchase_price:,.2f}",
                "Precio Actual": f"${current_price:,.2f}",
                "Valor Total": f"${curr_val:,.2f}",
                "Ganancia/Pérdida ($)": f"${pnl:,.2f}",
                "Rentabilidad (%)": f"{pnl_pct:+.2f}%"
            })
        except Exception as e:
            st.error(f"Error procesando activo: {e}")

    if not portfolio_data:
        st.error("No se pudo construir la tabla de rentabilidad.")
        return

    df = pd.DataFrame(portfolio_data)
    
    total_pnl = total_current_value - total_investment
    total_pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0
    
    st.markdown("---")
    st.write("📊 **Análisis y Rentabilidad en Tiempo Real (Yahoo Finance)**")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Capital Invertido", f"${total_investment:,.2f}")
    col2.metric("Valor de Mercado", f"${total_current_value:,.2f}")
    col3.metric("Rendimiento Total", f"${total_pnl:,.2f}", f"{total_pnl_pct:+.2f}%")
    
    st.dataframe(df, use_container_width=True)