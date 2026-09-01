import pandas as pd
import streamlit as st
import yfinance as yf
from portfolio_controller import PortfolioController

def render():
    st.title("📈 Análisis de Mercados & Clases de Activos Globales")
    st.markdown("""
    Consulta cotizaciones e históricos en tiempo real de **Acciones, Commodities (Oro) e Índices Tecnológicos**, 
    con opción de registrar el *snapshot* actual en la base de datos **TiDB Cloud**.
    """)

    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        st.subheader("🟡 Oro (Gold Spot)")
        gold_ticker = yf.Ticker("GC=F")
        gold_info = gold_ticker.fast_info
        gold_price = gold_info.get("lastPrice", 0.0)
        gold_prev = gold_info.get("previousClose", gold_price)
        gold_chg = (
            ((gold_price - gold_prev) / gold_prev * 100) if gold_prev else 0.0
        )
        st.metric(
            "Precio Futuros Oro ($/oz)",
            f"${gold_price:,.2f}",
            f"{gold_chg:+.2f}%",
        )
        if st.button("💾 Guardar Oro en TiDB", key="save_gold"):
            if PortfolioController.save_market_quote(
                "GC=F", "Gold Futures", "Commodity", gold_price, gold_chg
            ):
                st.success("✅ Cotización del Oro guardada en TiDB.")
            else:
                st.error("❌ Error al guardar en TiDB.")

    with col_m2:
        st.subheader("💻 Nasdaq 100 Index")
        nasdaq_ticker = yf.Ticker("^IXIC")
        nasdaq_info = nasdaq_ticker.fast_info
        nasdaq_price = nasdaq_info.get("lastPrice", 0.0)
        nasdaq_prev = nasdaq_info.get("previousClose", nasdaq_price)
        nasdaq_chg = (
            ((nasdaq_price - nasdaq_prev) / nasdaq_prev * 100)
            if nasdaq_prev
            else 0.0
        )
        st.metric(
            "S&P / Nasdaq Composite",
            f"{nasdaq_price:,.2f} pts",
            f"{nasdaq_chg:+.2f}%",
        )
        if st.button("💾 Guardar Nasdaq en TiDB", key="save_nasdaq"):
            if PortfolioController.save_market_quote(
                "^IXIC", "Nasdaq Composite", "Index", nasdaq_price, nasdaq_chg
            ):
                st.success("✅ Cotización de Nasdaq guardada en TiDB.")
            else:
                st.error("❌ Error al guardar en TiDB.")

    with col_m3:
        st.subheader("🍎 Apple Inc. (AAPL)")
        aapl_ticker = yf.Ticker("AAPL")
        aapl_info = aapl_ticker.fast_info
        aapl_price = aapl_info.get("lastPrice", 0.0)
        aapl_prev = aapl_info.get("previousClose", aapl_price)
        aapl_chg = (
            ((aapl_price - aapl_prev) / aapl_prev * 100) if aapl_prev else 0.0
        )
        st.metric("Acción AAPL ($)", f"${aapl_price:,.2f}", f"{aapl_chg:+.2f}%")
        if st.button("💾 Guardar AAPL en TiDB", key="save_aapl"):
            if PortfolioController.save_market_quote(
                "AAPL", "Apple Inc.", "Equity", aapl_price, aapl_chg
            ):
                st.success("✅ Cotización de AAPL guardada en TiDB.")
            else:
                st.error("❌ Error al guardar en TiDB.")

    st.markdown("---")
    st.subheader("🔍 Buscador e Histórico de Activos Financieros")

    symbol = st.text_input(
        "Ingrese el Ticker o Símbolo de Mercado (ej. AAPL, NVDA, TSLA, GC=F,"
        " ^IXIC, BTC-USD):",
        value="NVDA",
    ).upper()
    period = st.selectbox(
        "Rango de Tiempo",
        ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
        index=3,
    )

    if symbol:
        try:
            asset = yf.Ticker(symbol)
            df_hist = asset.history(period=period)

            if not df_hist.empty:
                info = asset.fast_info
                curr_price = info.get("lastPrice", 0.0)
                prev_price = info.get("previousClose", curr_price)
                chg_pct = (
                    ((curr_price - prev_price) / prev_price * 100)
                    if prev_price
                    else 0.0
                )

                st.write(f"### Evolución del Precio: **{symbol}**")
                st.line_chart(df_hist["Close"])

                col_sub1, col_sub2 = st.columns([3, 1])
                with col_sub1:
                    st.subheader("📊 Resumen de Datos Históricos")
                    st.dataframe(
                        df_hist[
                            ["Open", "High", "Low", "Close", "Volume"]
                        ].tail(10),
                        use_container_width=True,
                    )

                with col_sub2:
                    st.subheader("💾 Guardar Búsqueda")
                    st.metric(
                        "Último Precio",
                        f"${curr_price:,.2f}",
                        f"{chg_pct:+.2f}%",
                    )
                    asset_type_input = st.selectbox(
                        "Tipo de Activo",
                        ["Equity", "Commodity", "Index", "Crypto", "FX"],
                    )
                    if st.button(f"💾 Guardar {symbol} en TiDB"):
                        if PortfolioController.save_market_quote(
                            symbol,
                            symbol,
                            asset_type_input,
                            curr_price,
                            chg_pct,
                        ):
                            st.success(f"✅ {symbol} guardado en TiDB Cloud.")
                        else:
                            st.error("❌ Error al guardar en TiDB.")
            else:
                st.warning(
                    f"No se encontraron datos para el símbolo '{symbol}'."
                )
        except Exception as err:
            st.error(f"Error al obtener los datos de mercado: {err}")

    st.markdown("---")
    st.subheader("📋 Historial de Cotizaciones Registradas en TiDB")
    if st.button("🔄 Cargar Cotizaciones de la Base de Datos"):
        quotes = PortfolioController.get_market_quotes()
        if quotes:
            df_quotes = pd.DataFrame(quotes)
            st.dataframe(
                df_quotes.style.format({
                    "price": "${:,.2f}",
                    "change_percent": "{:+.2f}%",
                }),
                use_container_width=True,
            )
        else:
            st.info("No hay cotizaciones guardadas aún en TiDB Cloud.")