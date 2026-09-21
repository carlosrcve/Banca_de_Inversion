# mod_wealth.py
# Contenido mejorado para tu archivo modules/Gestión_Global_de_Patrimonio.py
import numpy as np
import pandas as pd
import streamlit as st


class GlobalWealthEngine:

  def __init__(self, client_id):
    self.client_id = client_id

  def cargar_estructura_holding(self):
    """Recupera la estructura jerárquica de holdings, trusts y operativas UHNWI."""
    data = {
        "Entidad": [
            "Holding Principal (BVI)",
            "Fideicomiso Familiar (Delaware)",
            "Empresa Operativa (LatAm)",
            "Sociedad de Inversión (Luxemburgo)",
        ],
        "Tipo": ["Holding", "Trust", "Operativa", "Patrimonial"],
        "Jurisdicción": [
            "Islas Vírgenes Británicas",
            "Estados Unidos",
            "Local",
            "Luxemburgo",
        ],
        "Participacion_%": [100.0, 100.0, 51.0, 100.0],
        "Valor_Activos_USD": [15000000, 8500000, 4200000, 6000000],
    }
    return pd.DataFrame(data)

  def calcular_impacto_fiscal_transfronterizo(
      self,
      monto_dividendo,
      tasa_retencion_origen,
      tasa_corporativa_destino,
      aplica_tratado_doble_tributacion=True,
  ):
    """Motor avanzado de ingeniería fiscal considerando exenciones por convenios

    internacionales de doble imposición (DTT) y créditos fiscales.
    """
    # Si aplica tratado, usualmente las retenciones en origen bajan por disposiciones de holding
    if aplica_tratado_doble_tributacion:
      tasa_retencion_efectiva = tasa_retencion_origen * 0.5  # Ejemplo de alivio DTT
    else:
      tasa_retencion_efectiva = tasa_retencion_origen

    retencion_origen = monto_dividendo * (tasa_retencion_efectiva / 100)
    monto_neto_remitido = monto_dividendo - retencion_origen

    # Crédito fiscal por impuestos pagados en el origen aplicado en destino
    impuesto_bruto_destino = monto_neto_remitido * (
        tasa_corporativa_destino / 100
    )
    credito_fiscal = min(
        retencion_origen, impuesto_bruto_destino
    )  # Evita doble tributación plena
    impuesto_neto_destino = max(0, impuesto_bruto_destino - credito_fiscal)

    carga_tributaria_total = retencion_origen + impuesto_neto_destino
    efectiva_total_pct = (carga_tributaria_total / monto_dividendo) * 100

    return {
        "Monto Bruto": monto_dividendo,
        "Retención Ajustada (Origen)": retencion_origen,
        "Monto Neto Remitido": monto_neto_remitido,
        "Impuesto Neto en Destino": impuesto_neto_destino,
        "Carga Fiscal Total (USD)": carga_tributaria_total,
        "Tasa Fiscal Efectiva Conjunta (%)": efectiva_total_pct,
    }

  def simular_transferencia_generacional(
      self,
      patrimonio_actual,
      tasa_crecimiento_anual,
      anos,
      tasa_impuesto_sucesoral,
      uso_fideicomiso=True,
  ):
    """Simula el traspaso patrimonial bajo esquemas fiduciarios vs liquidación

    sucesoral tradicional.
    """
    proyeccion = []
    patrimonio = patrimonio_actual

    for ano in range(1, anos + 1):
      patrimonio *= 1 + tasa_crecimiento_anual
      proyeccion.append({"Año": ano, "Patrimonio Proyectado": patrimonio})

    patrimonio_final_bruto = proyeccion[-1]["Patrimonio Proyectado"]

    if uso_fideicomiso:
      # Los trusts o holdings estructurados reducen drásticamente o diferencian el impacto sucesoral
      tasa_efectiva_sucesion = tasa_impuesto_sucesoral * 0.25
    else:
      tasa_efectiva_sucesion = tasa_impuesto_sucesoral

    patrimonio_neto_herederos = patrimonio_final_bruto * (
        1 - (tasa_efectiva_sucesion / 100)
    )

    return (
        pd.DataFrame(proyeccion),
        patrimonio_neto_herederos,
        tasa_efectiva_sucesion,
    )


def render():
  st.title("🌐 Global Wealth Management Engine")
  st.markdown(
      "Motor avanzado de inteligencia patrimonial para perfiles UHNWI,"
      " estructuras multi-divisa y simulación fiscal transfronteriza."
  )

  engine = GlobalWealthEngine(client_id="UHNWI_001")

  tab1, tab2, tab3 = st.tabs(
      ["Estructura de Holdings", "Ingeniería Fiscal", "Planificación Sucesoria"]
  )

  with tab1:
    st.subheader("Mapa Global de Activos y Holdings")
    df_holdings = engine.cargar_estructura_holding()
    st.dataframe(df_holdings, use_container_width=True)

    total_patrimonio = df_holdings["Valor_Activos_USD"].sum()
    st.metric(
        label="Patrimonio Consolidado Global (USD)",
        value=f"${total_patrimonio:,.2f}",
    )

  with tab2:
    st.subheader("Simulador de Retenciones y Dividendos Transfronterizos")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
      monto = st.number_input(
          "Dividendo Bruto (USD)", value=1000000.0, step=50000.0
      )
    with col2:
      tasa_orig = st.number_input("Tasa Retención Origen (%)", value=15.0, step=0.5)
    with col3:
      tasa_dest = st.number_input(
          "Tasa Impuesto Destino (%)", value=20.0, step=0.5
      )
    with col4:
      aplica_dtt = st.checkbox(
          "Aplicar Tratado de Doble Tributación (DTT)", value=True
      )

    if st.button("Calcular Ingeniería Fiscal"):
      resultado = engine.calcular_impacto_fiscal_transfronterizo(
          monto, tasa_orig, tasa_dest, aplica_dtt
      )
      st.json(resultado)

  with tab3:
    st.subheader("Simulación de Transferencia Generacional y Trusts")
    col_a, col_b = st.columns(2)
    with col_a:
      pat_inicial = st.number_input(
          "Patrimonio Base (USD)", value=30000000.0, step=1000000.0
      )
      crecimiento = (
          st.slider("Tasa de Rendimiento Anual Esperada (%)", 1.0, 15.0, 6.0)
          / 100
      )
    with col_b:
      anos = st.slider("Horizonte Temporal (Años)", 5, 30, 15)
      imp_sucesion = st.slider(
          "Tasa Nominal de Impuestos de Sucesión (%)", 0.0, 50.0, 25.0
      )

    uso_trust = st.toggle(
        "Proteger mediante Estructura Fiduciaria / Holding Avanzado (Trust)",
        value=True,
    )

    if st.button("Simular Escenario Sucesorio"):
      df_proyeccion, neto_herederos, tasa_aplicada = (
          engine.simular_transferencia_generacional(
              pat_inicial, crecimiento, anos, imp_sucesion, uso_trust
          )
      )
      st.line_chart(df_proyeccion.set_index("Año"))
      st.success(
          f"Patrimonio Neto Estimado para Herederos tras {anos} años (Tasa"
          f" impositiva aplicada: {tasa_aplicada:.2f}%):"
          f" ${neto_herederos:,.2f}"
      )


if __name__ == "__main__":
  render()