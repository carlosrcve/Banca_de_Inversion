# app.py
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from modules import mod_dcf, mod_markets, mod_portfolio

# Configuración inicial de la página
st.set_page_config(
    page_title="Gylfi Software - Banca de Inversión",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inicializar URL de la Base de Datos (Soporte local secrets.toml y Render Env Vars)
if "db_url" not in st.session_state:
    try:
        st.session_state.db_url = st.secrets["mysql"]["url"]
    except (KeyError, FileNotFoundError):
        st.session_state.db_url = os.environ.get("MYSQL_URL")

st.sidebar.title("🏛️ Gylfi Software")
st.sidebar.markdown("**Suite de Banca de Inversión**")

# Estado de conexión en Sidebar
if st.session_state.db_url:
    st.sidebar.caption("🟢 Conectado a TiDB Cloud")
else:
    st.sidebar.caption("🔴 DB no configurada")

# Menú de Navegación Lateral
module = st.sidebar.radio(
    "Navegación / Módulos",
    [
        "📊 Modelo DCF & M&A",
        "📈 Mercados & Clases de Activos",
        "💼 Gestión de Portafolio",
    ],
)

st.sidebar.markdown("---")

# Enrutamiento de Módulos
if module == "📊 Modelo DCF & M&A":
    mod_dcf.render()

elif module == "📈 Mercados & Clases de Activos":
    mod_markets.render()

elif module == "💼 Gestión de Portafolio":
    mod_portfolio.render()