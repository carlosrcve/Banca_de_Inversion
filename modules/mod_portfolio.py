from datetime import date
import pandas as pd
import streamlit as st
from portfolio_controller import PortfolioController

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
                        assets = PortfolioController.get_portfolio_assets(p["id"])
                        if assets:
                            df_assets = pd.DataFrame(assets)
                            st.dataframe(
                                df_assets.style.format({
                                    "quantity": "{:,.2f}",
                                    "purchase_price": "${:,.2f}",
                                }),
                                use_container_width=True,
                            )
                        else:
                            st.info("Este portafolio no contiene activos.")
            else:
                st.info("No se encontraron portafolios en TiDB Cloud.")