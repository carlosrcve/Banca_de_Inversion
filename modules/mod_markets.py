import pandas as pd
import streamlit as st
import yfinance as yf
from portfolio_controller import PortfolioController


def get_ticker_snapshot(symbol: str):
    """Función auxiliar para obtener precio y cambio porcentual de forma segura."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.get("lastPrice", 0.0) or 0.0
        prev = info.get("previousClose", price) or price
        change_pct = ((price - prev) / prev * 100) if prev else 0.0
        return price, change_pct
    except Exception:
        return 0.0, 0.0


def render():
    st.title("📈 Análisis de Mercados & Clases de Activos Globales")
    st.markdown("""
    Consulta cotizaciones e históricos en tiempo real de **Acciones, Commodities (Oro) e Índices Tecnológicos**, 
    con opción de registrar el *snapshot* actual en la base de datos **TiDB Cloud**.
    """)

    col_m1, col_m2, col_m3 = st.columns(3)

    # -------------------------------------------------------------------------
    # 1. TARJETAS MÉTRICAS PRINCIPALES
    # -------------------------------------------------------------------------
    with col_m1:
        st.subheader("🟡 Oro (Gold Spot)")
        gold_price, gold_chg = get_ticker_snapshot("GC=F")
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
        st.subheader("💻 Nasdaq Composite")
        nasdaq_price, nasdaq_chg = get_ticker_snapshot("^IXIC")
        st.metric(
            "Nasdaq Composite Index",
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
        aapl_price, aapl_chg = get_ticker_snapshot("AAPL")
        st.metric("Acción AAPL ($)", f"${aapl_price:,.2f}", f"{aapl_chg:+.2f}%")
        if st.button("💾 Guardar AAPL en TiDB", key="save_aapl"):
            if PortfolioController.save_market_quote(
                "AAPL", "Apple Inc.", "Equity", aapl_price, aapl_chg
            ):
                st.success("✅ Cotización de AAPL guardada en TiDB.")
            else:
                st.error("❌ Error al guardar en TiDB.")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 2. BUSCADOR E HISTÓRICO DE ACTIVOS
    # -------------------------------------------------------------------------
    st.subheader("🔍 Buscador e Histórico de Activos Financieros")

    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        symbol = st.text_input(
            "Ingrese el Ticker o Símbolo de Mercado (ej. AAPL, NVDA, TSLA, GC=F, ^IXIC, BTC-USD):",
            value="NVDA",
        ).strip().upper()
    with col_search2:
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
                curr_price, chg_pct = get_ticker_snapshot(symbol)

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
                    if st.button(f"💾 Guardar {symbol} en TiDB", key="save_search_asset"):
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
                st.warning(f"⚠️ No se encontraron datos para el símbolo '{symbol}'. Verifique la nomenclatura.")
        except Exception as err:
            st.error(f"❌ Error al obtener los datos de mercado: {err}")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 3. HISTORIAL DE COTIZACIONES EN TiDB
    # -------------------------------------------------------------------------
    st.subheader("📋 Historial de Cotizaciones Registradas en TiDB")
    if st.button("🔄 Cargar / Refrescar Cotizaciones de la BD"):
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
            st.info("ℹ️ No hay cotizaciones guardadas aún en TiDB Cloud.")