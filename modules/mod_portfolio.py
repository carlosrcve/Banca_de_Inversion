from datetime import date
import pandas as pd
import streamlit as st
import yfinance as yf
from portfolio_controller import PortfolioController

@st.cache_data(ttl=600)  # Cacheamos los precios por 10 minutos para no saturar las peticiones
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

        # Usamos un formulario para la entrada del activo para evitar recargas indeseadas de Streamlit
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

        # Vista previa y botón final de guardado en la base de datos
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
        if st.button("🔄 Cargar Lista de Portafolios", key="btn_load_portfolios"):
            portfolios = PortfolioController.get_portfolios()
            if portfolios:
                for p in portfolios:
                    with st.expander(f"📁 **{p['portfolio_name']}** (Creado: {p['created_at']})"):
                        st.write(f"**Descripción:** {p['description']}")
                        st.markdown("---")
                        
                        # Renderizamos el análisis en tiempo real para este portafolio
                        render_portfolio_dashboard_inner(p["id"])
            else:
                st.info("No se encontraron portafolios en TiDB Cloud.")

def render_portfolio_dashboard_inner(portfolio_id: int):
    """Función interna para calcular y mostrar métricas en tiempo real de un portafolio específico."""
    assets = PortfolioController.get_portfolio_assets(portfolio_id)
    
    if not assets:
        st.info("Este portafolio no contiene activos registrados.")
        return

    portfolio_data = []
    total_investment = 0.0
    total_current_value = 0.0

    for asset in assets:
        # Asumiendo que retorna tuplas: (symbol, asset_name, asset_type, quantity, purchase_price, purchase_date)
        symbol = asset[0]
        name = asset[1]
        asset_type = asset[2]
        quantity = float(asset[3])
        purchase_price = float(asset[4])
        
        # Obtenemos precio actual de mercado vía yfinance
        current_price = get_live_price(symbol)
        if current_price == 0.0:
            current_price = purchase_price  # Fallback si falla la API
            
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

    df = pd.DataFrame(portfolio_data)
    
    # Métricas generales del portafolio
    total_pnl = total_current_value - total_investment
    total_pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0
    
    st.write("📊 **Análisis y Rentabilidad en Tiempo Real**")
    col1, col2, col3 = st.columns(3)
    col1.metric("Capital Invertido", f"${total_investment:,.2f}")
    col2.metric("Valor de Mercado", f"${total_current_value:,.2f}")
    col3.metric("Rendimiento Total", f"${total_pnl:,.2f}", f"{total_pnl_pct:+.2f}%")
    
    # Tabla detallada con formato
    st.dataframe(df, use_container_width=True)