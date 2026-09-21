# app.py
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import modules.mod_dcf as mod_dcf
import modules.mod_dealroom as mod_dealroom
import modules.mod_markets as mod_markets
import modules.mod_portfolio as mod_portfolio
import modules.mod_wealth as mod_wealth

# Configuración inicial de la página
st.set_page_config(
    page_title="Gylfi Software - Banca de Inversión",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Cadena de conexión por defecto a TiDB Cloud
DEFAULT_DB_URL = "mysql+pymysql://4K4VAw4t4ZPFUTF.root:I1lVZQDq2d4KJbQA@gateway01.us-east-1.prod.aws.tidbcloud.com:4000/valuations_db"

# Intentar obtener URL desde secrets, variables de entorno o fallback a TiDB Cloud directamente
try:
    st.session_state.db_url = st.secrets["mysql"]["url"]
except Exception:
    st.session_state.db_url = os.environ.get("MYSQL_URL", DEFAULT_DB_URL)

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
        "🌐 Gestión Global de Patrimonio",
        "🏛️ M&A & Deal Room",
        "📈 Asset Management & Fondos",
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

elif module == "🌐 Gestión Global de Patrimonio":
    mod_wealth.render()

elif module == "🏛️ M&A & Deal Room":
    mod_dealroom.render()
