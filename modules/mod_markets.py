import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from portfolio_controller import PortfolioController

# -------------------------------------------------------------------------
# FUNCIÓN EN CACHÉ PARA CARGAR LAS ACCIONES DEL S&P 500 DINÁMICAMENTE
# -------------------------------------------------------------------------
@st.cache_data(ttl=86400)
def load_sp500_tickers():
    """Descarga la lista actualizada del S&P 500 desde Wikipedia."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df_sp500 = tables[0]

        dict_sp500 = {}
        for _, row in df_sp500.iterrows():
            symbol = str(row["Symbol"]).replace(".", "-")
            name = row["Security"]
            dict_sp500[f"{symbol} - {name}"] = symbol

        return dict_sp500
    except Exception:
        return {
            "AAPL - Apple Inc.": "AAPL",
            "NVDA - NVIDIA Corp.": "NVDA",
            "MSFT - Microsoft Corp.": "MSFT",
            "AMZN - Amazon.com Inc.": "AMZN",
            "GOOGL - Alphabet Inc.": "GOOGL",
            "META - Meta Platforms": "META",
            "TSLA - Tesla Inc.": "TSLA",
            "BRK-B - Berkshire Hathaway": "BRK-B",
            "JPM - JPMorgan Chase & Co.": "JPM",
            "V - Visa Inc.": "V",
        }

# -------------------------------------------------------------------------
# FUNCIÓN PARA OBTENER COTIZACIONES (SIN CACHÉ PARA EVITAR RETARDO EN REFRESCO)
# -------------------------------------------------------------------------
def get_ticker_snapshot(symbol: str):
    """Obtiene de forma segura y directa el precio actual y variación del ticker."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.get("lastPrice", 0.0) or 0.0
        prev = info.get("previousClose", price) or price
        change_pct = ((price - prev) / prev * 100) if prev else 0.0
        return float(price), float(change_pct)
    except Exception:
        return 0.0, 0.0

# -------------------------------------------------------------------------
# FUNCIÓN RENDER PRINCIPAL
# -------------------------------------------------------------------------
def render():
    st.title("📈 Análisis de Mercados & Clases de Activos Globales")
    
    st.markdown("""
        <style>
        .scrollable-container {
            display: flex;
            flex-direction: row;
            overflow-x: auto;
            gap: 15px;
            padding-bottom: 15px;
            width: 100%;
        }
        .scrollable-container > div {
            min-width: 250px;
            flex: 1;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="scrollable-container">', unsafe_allow_html=True)
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

    # 1. COMMODITIES
    with col_m1:
        st.markdown("### 🪙 Commodities")
        dict_metales = {
            "Oro (Gold Spot)": "GC=F",
            "Plata (Silver)": "SI=F",
            "Cobre (Copper)": "HG=F",
            "Platino (Platinum)": "PL=F",
            "Petróleo WTI": "CL=F",
        }
        selected_metal_name = st.selectbox("Seleccione:", list(dict_metales.keys()), key="sel_metal")
        metal_ticker = dict_metales[selected_metal_name]

        m_price, m_chg = get_ticker_snapshot(metal_ticker)
        st.metric(selected_metal_name, f"${m_price:,.2f}", f"{m_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_metal_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(
                metal_ticker, selected_metal_name, "Commodity", m_price, m_chg
            )
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    # 2. ÍNDICES
    with col_m2:
        st.markdown("### 📊 Índices")
        dict_indices = {
            "Nasdaq Composite": "^IXIC",
            "S&P 500": "^GSPC",
            "Dow Jones Industrial": "^DJI",
            "Russell 2000": "^RUT",
            "FTSE 100 (UK)": "^FTSE",
        }
        selected_index_name = st.selectbox("Seleccione:", list(dict_indices.keys()), key="sel_index")
        index_ticker = dict_indices[selected_index_name]

        i_price, i_chg = get_ticker_snapshot(index_ticker)
        st.metric(selected_index_name, f"{i_price:,.2f} pts", f"{i_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_index_btn", use_container_width=True):
            if PortfolioController.save_market_quote(index_ticker, selected_index_name, "Index", i_price, i_chg):
                st.success("✅ Guardado.")
            else:
                st.error("❌ Error al guardar.")

    # 3. ACCIONES
    with col_m3:
        st.markdown("### 🏢 Acciones")
        dict_acciones = load_sp500_tickers()
        selected_stock_label = st.selectbox("Seleccione:", options=list(dict_acciones.keys()), key="sel_stock")
        stock_ticker = dict_acciones[selected_stock_label]

        s_price, s_chg = get_ticker_snapshot(stock_ticker)
        st.metric(selected_stock_label.split(" - ")[0], f"${s_price:,.2f}", f"{s_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_stock_btn", use_container_width=True):
            if PortfolioController.save_market_quote(stock_ticker, selected_stock_label, "Equity", s_price, s_chg):
                st.success("✅ Guardado.")
            else:
                st.error("❌ Error al guardar.")

    # 4. DIVISAS BCV
    with col_m4:
        st.markdown("### 🇻🇪 Divisas BCV")
        dict_divisas = {
            "Dólar Oficial (BCV)": "USDVES=X",
            "Euro Oficial (BCV)": "EURVES=X",
        }
        selected_divisa_name = st.selectbox("Seleccione:", list(dict_divisas.keys()), key="sel_divisa")
        divisa_ticker = dict_divisas[selected_divisa_name]

        d_price, d_chg = get_ticker_snapshot(divisa_ticker)
        price_str = f"Bs. {d_price:,.2f}" if d_price and d_price > 0 else "Bs. S/D"
        st.metric(selected_divisa_name, price_str, f"{d_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_divisa_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(divisa_ticker, selected_divisa_name, "Currency", d_price, d_chg)
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    # 5. FOREX
    with col_m5:
        st.markdown("### 💱 Forex Majors")
        dict_forex = {
            "Euro / Dólar (EUR/USD)": "EURUSD=X",
            "Libra / Dólar (GBP/USD)": "GBPUSD=X",
            "Dólar / Yen (USD/JPY)": "USDJPY=X",
            "Dólar / Canadiense (USD/CAD)": "USDCAD=X",
            "Dólar / Sueca (USD/SEK)": "USDSEK=X",
        }
        selected_forex_name = st.selectbox("Seleccione:", list(dict_forex.keys()), key="sel_forex")
        forex_ticker = dict_forex[selected_forex_name]

        f_price, f_chg = get_ticker_snapshot(forex_ticker)
        price_forex_str = f"{f_price:,.4f}" if f_price and f_price > 0 else "S/D"
        st.metric(selected_forex_name, price_forex_str, f"{f_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_forex_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(forex_ticker, selected_forex_name, "Forex", f_price, f_chg)
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")

    # -------------------------------------------------------------------------
    # 2. BUSCADOR & ASESOR INTELIGENTE (BAJO DEMANDA CON BOTÓN DE REFRESCO)
    # -------------------------------------------------------------------------
    st.subheader("🔍 Buscador & Asesor Inteligente de Activos")

    col_search1, col_search2, col_search3 = st.columns([2.5, 1, 1])
    with col_search1:
        symbol = st.text_input("Ticker o Símbolo (ej. AAPL, NVDA, GC=F, ^IXIC):", value="NVDA", key="input_search_symbol").strip().upper()
    with col_search2:
        period = st.selectbox("Rango de Tiempo", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=3, key="select_search_period")
    with col_search3:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh_btn = st.button("🔄 Consultar / Actualizar", use_container_width=True)

    if symbol:
        try:
            asset = yf.Ticker(symbol)
            df_hist = asset.history(period=period)

            if not df_hist.empty:
                curr_price, chg_pct = get_ticker_snapshot(symbol)
                info = getattr(asset, "info", {})
                long_name = info.get("longName", symbol)
                currency = info.get("currency", "USD")
                pe_ratio = info.get("trailingPE", None)
                recommendation = info.get("recommendationKey", "N/A").upper()
                roe = info.get("returnOnEquity", None)
                market_cap = info.get("marketCap", None)
                shares_out = info.get("sharesOutstanding", None)
                eps = info.get("trailingEps", None)
                dividend_rate = info.get("dividendRate", None)
                dividend_yield = info.get("dividendYield", None)
                profit_margin = info.get("profitMargins", None)
                debt_to_equity = info.get("debtToEquity", None)
                pb_ratio = info.get("priceToBook", None)
                beta = info.get("beta", None)

                # Ingresos trimestrales seguros
                q_rev_str, q_net_str = "N/A", "N/A"
                try:
                    qf = asset.quarterly_financials
                    if qf is not None and not qf.empty:
                        rev_rows = [r for r in qf.index if "Revenue" in str(r)]
                        net_rows = [r for r in qf.index if "Net Income" in str(r)]
                        if rev_rows and pd.notnull(qf.loc[rev_rows[0]].iloc[0]):
                            q_rev_str = f"${qf.loc[rev_rows[0]].iloc[0]:,.0f}"
                        if net_rows and pd.notnull(qf.loc[net_rows[0]].iloc[0]):
                            q_net_str = f"${qf.loc[net_rows[0]].iloc[0]:,.0f}"
                except Exception:
                    pass

                st.markdown(f"### 💡 Diagnóstico Financiero: **{long_name} ({symbol})**")
                
                # Fila 1
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Precio Actual", f"${curr_price:,.2f} {currency}", f"{chg_pct:+.2f}%")
                c2.metric("P/E Ratio", f"{pe_ratio:.1f}x" if pe_ratio else "N/A", "Valuación")
                c3.metric("ROE", f"{roe*100:.1f}%" if roe else "N/A", "Eficiencia")
                c4.metric("Opinión Wall Street", recommendation.replace("_", " "), "Consenso")

                # Fila 2
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Cap. Bursátil", f"${market_cap:,.0f}" if market_cap else "N/A", "Valor de mercado")
                c2.metric("Acciones Circulación", f"{shares_out:,.0f}" if shares_out else "N/A", "Títulos")
                c3.metric("Ingresos Trimestrales", q_rev_str, "Reporte Q")
                c4.metric("Ganancias Trimestrales", q_net_str, "Utilidad Neta Q")

                # Fila 3
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("EPS", f"${eps:,.2f}" if eps is not None else "N/A", "Por Acción")
                c2.metric("Dividendo Anual", f"${dividend_rate:,.2f}" if dividend_rate is not None else "$0.00", "Pago")
                c3.metric("Dividend Yield", f"{dividend_yield*100:.2f}%" if dividend_yield is not None else "0.00%", "Yield")
                tot_divs = (dividend_rate * shares_out) if (dividend_rate and shares_out) else None
                c4.metric("Total Dividendos", f"${tot_divs:,.0f}" if tot_divs else "N/A", "Global")

                # Fila 4
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Margen Neto", f"{profit_margin*100:.1f}%" if profit_margin is not None else "N/A", "Eficiencia")
                c2.metric("Deuda / Capital", f"{debt_to_equity:.1f}%" if debt_to_equity is not None else "N/A", "Apalancamiento")
                c3.metric("Precio / Libros", f"{pb_ratio:.2f}x" if pb_ratio is not None else "N/A", "Patrimonio")
                c4.metric("Beta", f"{beta:.2f}" if beta is not None else "N/A", "Volatilidad")

                st.markdown("---")

                # Gráfico interactivo limpio y responsivo
                df_hist = df_hist.reset_index()
                fig = go.Figure(data=[go.Candlestick(
                    x=df_hist["Date"], open=df_hist["Open"], high=df_hist["High"],
                    low=df_hist["Low"], close=df_hist["Close"], name=symbol,
                    increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
                )])
                fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", margin=dict(l=10, r=10, t=30, b=10), height=450)
                st.plotly_chart(fig, use_container_width=True)

                col_sub1, col_sub2 = st.columns([3, 1])
                with col_sub1:
                    st.subheader("📊 Resumen Histórico")
                    st.dataframe(df_hist[["Date", "Open", "High", "Low", "Close", "Volume"]].tail(10), use_container_width=True)
                with col_sub2:
                    st.subheader("💾 Guardar")
                    asset_type_input = st.selectbox("Tipo", ["Equity", "Commodity", "Index", "Crypto", "FX"], key="save_type")
                    if st.button(f"Guardar {symbol}", key="save_search_asset", use_container_width=True):
                        if PortfolioController.save_market_quote(symbol, long_name, asset_type_input, curr_price, chg_pct):
                            st.success(f"✅ {symbol} guardado.")
                        else:
                            st.error("❌ Error al guardar.")
            else:
                st.warning(f"⚠️ No hay datos para '{symbol}'.")
        except Exception as err:
            st.error(f"❌ Error al procesar el activo: {err}")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 3. HISTORIAL DE COTIZACIONES EN TiDB
    # -------------------------------------------------------------------------
    st.subheader("📋 Historial de Cotizaciones Registradas en TiDB")
    quotes = PortfolioController.get_market_quotes()
    if quotes:
        df_quotes = pd.DataFrame(quotes)
        st.dataframe(
            df_quotes.style.format({"price": "${:,.2f}", "change_percent": "{:+.2f}%"}),
            use_container_width=True,
        )
    else:
        st.info("ℹ️ No hay cotizaciones guardadas aún en TiDB Cloud.")