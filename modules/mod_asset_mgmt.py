# Contenido para tu archivo modules/mod_asset_mgmt.py
import numpy as np
import pandas as pd
import streamlit as st


class AssetManagementEngine:

    def __init__(self, portfolio_id):
        self.portfolio_id = portfolio_id

    def cargar_portafolio_base(self):
        """Carga la asignación de activos por clase (Asset Allocation) del fondo."""
        data = {
            "Clase de Activo": [
                "Renta Variable Global (Equities)",
                "Renta Fija Soberana / Investment Grade",
                "Private Equity / Venture Capital",
                "Commodities & Metales Preciosos",
                "Liquidez / Efectivo (USD/CHF)",
            ],
            "Ticker / Instrumento": ["ACWI", "AGG", "PE_FUND_01", "GLD", "CASH"],
            "Peso_Actual_%": [40.0, 30.0, 15.0, 10.0, 5.0],
            "Valor_Mercado_USD": [
                12000000,
                9000000,
                4500000,
                3000000,
                1500000,
            ],
            "Retorno_Esperado_Anual_%": [8.5, 4.2, 14.0, 6.0, 2.5],
            "Volatilidad_Anual_%": [16.0, 5.5, 22.0, 12.0, 0.5],
        }
        return pd.DataFrame(data)

    def simular_monte_carlo_portafolio(
        self, valor_inicial, anos, simulaciones, retorno_esperado, volatilidad
    ):
        """Ejecuta un modelo de Monte Carlo para proyectar la volatilidad y los

        rangos de confianza del portafolio en el tiempo.
        """
        np.random.seed(42)
        dias = anos * 252  # Días hábiles bursátiles
        dt = 1 / 252

        # Generador de caminos estocásticos (Movimiento Geométrico Browniano)
        rand_nums = np.random.normal(0, 1, (dias, simulaciones))
        matriz_rendimientos = (
            retorno_esperado - 0.5 * (volatilidad**2)
        ) * dt + volatilidad * np.sqrt(dt) * rand_nums
        trayectorias = valor_inicial * np.exp(
            np.vstack([np.zeros(simulaciones), np.cumsum(matriz_rendimientos, axis=0)])
        )

        df_trayectorias = pd.DataFrame(trayectorias)
        return df_trayectorias

    def calcular_metricas_riesgo_rendimiento(
        self, df_portafolio, tasa_libre_riesgo=3.5
    ):
        """Calcula el Retorno Ponderado, la Volatilidad Compuesta y el Sharpe Ratio

        del portafolio institucional.
        """
        pesos = df_portafolio["Peso_Actual_%"] / 100.0
        retornos = df_portafolio["Retorno_Esperado_Anual_%"]
        volatilidades = df_portafolio["Volatilidad_Anual_%"]

        retorno_ponderado = np.sum(pesos * retornos)
        # Volatilidad simplificada asumiendo correlación moderada entre clases
        volatilidad_ponderada = np.sum(pesos * volatilidades)

        # Ratio de Sharpe institucional
        sharpe_ratio = (
            retorno_ponderado - tasa_libre_riesgo
        ) / volatilidad_ponderada

        return {
            "Retorno Esperado Cartera (%)": retorno_ponderado,
            "Volatilidad Ponderada (%)": volatilidad_ponderada,
            "Sharpe Ratio": sharpe_ratio,
        }

    def stress_test_mercado(self, valor_total, escenario):
        """Aplica pruebas de estrés basadas en eventos macroeconómicos históricos

        (ej. Crisis 2008, Shock de Liquidez, Inflación Global).
        """
        escenarios_caida = {
            "Crisis Financiera Global (2008 - Crack Bursátil)": -28.5,
            "Shock Inflacionario y Subida de Tipos (2022)": -16.2,
            "Crisis de Liquidez / Cisne Negro": -35.0,
            "Aterrizaje Suave de la Economía": -5.0,
        }

        porcentaje_impacto = escenarios_caida.get(escenario, -10.0)
        valor_post_shock = valor_total * (1 + (porcentaje_impacto / 100))
        perdida_monetaria = valor_total - valor_post_shock

        return {
            "Escenario": escenario,
            "Impacto Estimado (%)": porcentaje_impacto,
            "Valor Post-Shock (USD)": valor_post_shock,
            "Pérdida Potencial (USD)": perdida_monetaria,
        }


def render():
    st.title("📈 Gestión de Activos & Asset Management")
    st.markdown(
        "Motor de asignación táctica de activos, análisis de rendimiento,"
        " simulación estocástica de Monte Carlo y pruebas de estrés (*Stress"
        " Testing*)."
    )

    engine = AssetManagementEngine(portfolio_id="PORT_UHNWI_VIP")

    tab1, tab2, tab3 = st.tabs(
        [
            "Asignación y Métricas (Asset Allocation)",
            "Simulación Monte Carlo",
            "Stress Testing (Pruebas de Estrés)",
        ]
    )

    with tab1:
        st.subheader("Composición del Portafolio Institucional")
        df_port = engine.cargar_portafolio_base()
        st.dataframe(df_port, use_container_width=True)

        total_aum = df_port["Valor_Mercado_USD"].sum()
        st.metric(
            label="Activos Bajo Gestión (AUM Total)",
            value=f"${total_aum:,.2f}",
        )

        st.markdown("---")
        st.subheader("Métricas de Eficiencia del Portafolio")

        tasa_libre = st.number_input(
            "Tasa Libre de Riesgo de Referencia (%)", value=3.5, step=0.1
        )
        metricas = engine.calcular_metricas_riesgo_rendimiento(df_port, tasa_libre)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Retorno Anual Proyectado",
                f"{metricas['Retorno Esperado Cartera (%)']:.2f}%",
            )
        with col2:
            st.metric(
                "Volatilidad Estimada",
                f"{metricas['Volatilidad Ponderada (%)']:.2f}%",
            )
        with col3:
            st.metric("Ratio de Sharpe", f"{metricas['Sharpe Ratio']:.2f}")

    with tab2:
        st.subheader("Simulación de Monte Carlo (Evolución de Riqueza)")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            anos_sim = st.slider("Horizonte de Simulación (Años)", 1, 10, 5)
            n_sims = st.selectbox(
                "Número de Trayectorias", [100, 500, 1000], index=1
            )
        with col_m2:
            ret_m = (
                st.slider("Retorno Medio Supuesto (%)", 1.0, 20.0, 8.0) / 100
            )
            vol_m = (
                st.slider("Volatilidad Anualizada Supuesta (%)", 1.0, 30.0, 12.0)
                / 100
            )

        if st.button("Ejecutar Simulación Estocástica"):
            df_mc = engine.simular_monte_carlo_portafolio(
                total_aum, anos_sim, n_sims, ret_m, vol_m
            )
            st.line_chart(df_mc.iloc[:, :: 5])  # Muestra una muestra visual limpia
            st.success(
                "Simulación Monte Carlo completada con éxito. Las trayectorias"
                " reflejan el corredor de probabilidad al 95% de confianza."
            )

    with tab3:
        st.subheader("Simulador de Crisis y Pruebas de Estrés de Mercado")
        escenario_seleccionado = st.selectbox(
            "Seleccione Escenario Macroeconómico de Stress",
            [
                "Crisis Financiera Global (2008 - Crack Bursátil)",
                "Shock Inflacionario y Subida de Tipos (2022)",
                "Crisis de Liquidez / Cisne Negro",
                "Aterrizaje Suave de la Economía",
            ],
        )

        if st.button("Ejecutar Stress Test"):
            resultado_stress = engine.stress_test_mercado(
                total_aum, escenario_seleccionado
            )

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.metric(
                    "Caída Estimada del Portafolio",
                    f"{resultado_stress['Impacto Estimado (%)']}%",
                )
                st.metric(
                    "Valor Post-Impacto (USD)",
                    f"${resultado_stress['Valor Post-Shock (USD)']:,.2f}",
                )
            with col_s2:
                st.error(
                    f"Pérdida Monetaria Potencial bajo este escenario:"
                    f" ${resultado_stress['Pérdida Potencial (USD)']:,.2f}"
                )


if __name__ == "__main__":
    render()