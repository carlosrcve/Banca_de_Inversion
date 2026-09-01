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

st.sidebar.title("🏛️ Gylfi Software")
st.sidebar.markdown("**Suite de Banca de Inversión**")

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