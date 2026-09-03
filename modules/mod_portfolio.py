from datetime import date
import pandas as pd
import streamlit as st
from portfolio_controller import PortfolioController

def render():
    st.title("💼 Módulo de Gestión de Portafolio & Persistencia")
    st.markdown("""
    Crea, administra y consulta tus carteras corporativas e inversiones registradas directamente en **TiDB Cloud / MySQL**.
    """)

    tab1, tab2 = st.tabs(
        ["➕ Crear Portafolio", "📂 Mis Portafolios Guardados"]
    )

    with tab1:
        st.subheader("Crear Nueva Cartera / Portafolio de Inversión")

        p_name = st.text_input(
            "Nombre del Portafolio", value="Portafolio Crecimiento Tech 2026"
        )
        p_desc = st.text_area(
            "Descripción / Estrategia",
            value="Estrategia enfocada en tecnológicas de alta capitalización y cobertura en commodities.",
        )

        st.markdown("---")
        st.write("#### Activos del Portafolio")

        if "temp_assets" not in st.session_state:
            st.session_state.temp_assets = []

        col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)
        with col_a1:
            a_sym = st.text_input("Ticker", value="NVDA").upper()
        with col_a2:
            a_name = st.text_input("Nombre Activo", value="NVIDIA Corp.")
        with col_a3:
            a_type = st.selectbox(
                "Clase de Activo", ["Equity", "Commodity", "Index", "Crypto"]
            )
        with col_a4:
            a_qty = st.number_input("Cantidad", min_value=0.01, value=10.0)
        with col_a5:
            a_price = st.number_input(
                "Precio Compra ($)", min_value=0.01, value=125.50
            )

        a_date = st.date_input("Fecha de Adquisición", value=date.today())

        if st.button("➕ Agregar Activo a la Lista"):
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
            st.write("##### Vista Previa de Activos a Guardar:")
            df_temp = pd.DataFrame(st.session_state.temp_assets)
            st.dataframe(df_temp, use_container_width=True)

            if st.button(
                "💾 Guardar Portafolio Completo en TiDB Cloud", type="primary"
            ):
                if PortfolioController.create_portfolio(
                    p_name, p_desc, st.session_state.temp_assets
                ):
                    st.success(
                        f"✅ Portafolio '{p_name}' guardado exitosamente en TiDB Cloud."
                    )
                    st.session_state.temp_assets = []
                else:
                    st.error("❌ Ocurrió un error al guardar el portafolio.")

    with tab2:
        st.subheader("Consultar Portafolios Almacenados")
        if st.button("🔄 Cargar Lista de Portafolios"):
            portfolios = PortfolioController.get_portfolios()
            if portfolios:
                for p in portfolios:
                    with st.expander(
                        f"📁 **{p['portfolio_name']}** (Creado: {p['created_at']})"
                    ):
                        st.write(f"**Descripción:** {p['description']}")
                        assets = PortfolioController.get_portfolio_assets(
                            p["id"]
                        )
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