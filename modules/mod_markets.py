# mod_markets.py
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from portfolio_controller import PortfolioController

# -------------------------------------------------------------------------
# FUNCIÓN EN CACHÉ PARA CARGAR LAS ACCIONES DEL S&P 500 DINÁMICAMENTE
# -------------------------------------------------------------------------
@st.cache_data(ttl=86400)  # Guarda la lista en caché durante 24 horas
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
# FUNCIÓN EN CACHÉ PARA OBTENER COTIZACIONES
# -------------------------------------------------------------------------
@st.cache_data(ttl=120, show_spinner=False)
def get_ticker_snapshot(symbol: str):
    """Obtiene de forma segura el precio actual y variación del ticker con caché."""
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
    
    # CSS personalizado para:
    # 1. Crear un contenedor con scroll horizontal.
    # 2. Asegurar que cada columna tenga un ancho mínimo fijo.
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
        selected_metal_name = st.selectbox(
            "Seleccione:", list(dict_metales.keys()), key="sel_metal"
        )
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
        selected_index_name = st.selectbox(
            "Seleccione:", list(dict_indices.keys()), key="sel_index"
        )
        index_ticker = dict_indices[selected_index_name]

        i_price, i_chg = get_ticker_snapshot(index_ticker)
        st.metric(selected_index_name, f"{i_price:,.2f} pts", f"{i_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_index_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(
                index_ticker, selected_index_name, "Index", i_price, i_chg
            )
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    # 3. ACCIONES
    with col_m3:
        st.markdown("### 🏢 Acciones")
        dict_acciones = load_sp500_tickers()
        
        selected_stock_label = st.selectbox(
            "Seleccione:",
            options=list(dict_acciones.keys()),
            key="sel_stock"
        )
        stock_ticker = dict_acciones[selected_stock_label]

        s_price, s_chg = get_ticker_snapshot(stock_ticker)
        st.metric(selected_stock_label.split(" - ")[0], f"${s_price:,.2f}", f"{s_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_stock_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(
                stock_ticker, selected_stock_label, "Equity", s_price, s_chg
            )
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    # 4. DIVISAS BCV
    with col_m4:
        st.markdown("### 🇻🇪 Divisas BCV")
        dict_divisas = {
            "Dólar Oficial (BCV)": "USDVES=X",
            "Euro Oficial (BCV)": "EURVES=X",
        }
        selected_divisa_name = st.selectbox(
            "Seleccione:", list(dict_divisas.keys()), key="sel_divisa"
        )
        divisa_ticker = dict_divisas[selected_divisa_name]

        d_price, d_chg = get_ticker_snapshot(divisa_ticker)
        price_str = f"Bs. {d_price:,.2f}" if d_price and d_price > 0 else "Bs. S/D"
        st.metric(selected_divisa_name, price_str, f"{d_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_divisa_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(
                divisa_ticker, selected_divisa_name, "Currency", d_price, d_chg
            )
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    # 5. FOREX MAJORS
    with col_m5:
        st.markdown("### 💱 Forex Majors")
        dict_forex = {
            "Euro / Dólar (EUR/USD)": "EURUSD=X",
            "Libra / Dólar (GBP/USD)": "GBPUSD=X",
            "Dólar / Yen (USD/JPY)": "USDJPY=X",
            "Dólar / Dólar Canadiense (USD/CAD)": "USDCAD=X",
            "Dólar / Corona Sueca (USD/SEK)": "USDSEK=X",
        }
        selected_forex_name = st.selectbox(
            "Seleccione:", list(dict_forex.keys()), key="sel_forex"
        )
        forex_ticker = dict_forex[selected_forex_name]

        f_price, f_chg = get_ticker_snapshot(forex_ticker)
        price_forex_str = f"{f_price:,.4f}" if f_price and f_price > 0 else "S/D"
        st.metric(selected_forex_name, price_forex_str, f"{f_chg:+.2f}%")

        if st.button("💾 Guardar", key="save_forex_btn", use_container_width=True):
            success, err_msg = PortfolioController.save_market_quote(
                forex_ticker, selected_forex_name, "Forex", f_price, f_chg
            )
            if success:
                st.success("✅ Guardado.")
            else:
                st.error(f"❌ Error: {err_msg}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------------------------------------------------------
    # 2. BUSCADOR E HISTÓRICO DE ACTIVOS
    # -------------------------------------------------------------------------
    st.subheader("🔍 Buscador & Asesor Inteligente de Activos")

    col_search1, col_search2 = st.columns([3, 1])
    with col_search1:
        symbol = st.text_input(
            "Ingrese el Ticker o Símbolo de Mercado (ej. AAPL, NVDA, TSLA, GC=F, ^IXIC, BTC-USD):",
            value="NVDA",
            key="input_search_symbol",
        ).strip().upper()
    with col_search2:
        period = st.selectbox(
            "Rango de Tiempo",
            ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
            index=3,
            key="select_search_period",
        )

    if symbol:
        try:
            asset = yf.Ticker(symbol)
            df_hist = asset.history(period=period)

            if not df_hist.empty:
                curr_price, chg_pct = get_ticker_snapshot(symbol)

                # METADATOS Y ESTADOS FINANCIEROS
                info = getattr(asset, "info", {})
                long_name = info.get("longName", symbol)
                currency = info.get("currency", "USD")
                pe_ratio = info.get("trailingPE", None)
                target_price = info.get("targetMeanPrice", None)
                recommendation = info.get("recommendationKey", "N/A").upper()
                roe = info.get("returnOnEquity", None)
                w52_high = info.get("fiftyTwoWeekHigh", None)
                w52_low = info.get("fiftyTwoWeekLow", None)
                
                market_cap = info.get("marketCap", None)
                shares_out = info.get("sharesOutstanding", None)
                eps = info.get("trailingEps", None)
                dividend_rate = info.get("dividendRate", None)
                dividend_yield = info.get("dividendYield", None)

                q_rev_str, q_net_str = "N/A", "N/A"
                try:
                    qf = asset.quarterly_financials
                    if qf is not None and not qf.empty:
                        rev_rows = [r for r in qf.index if "Revenue" in str(r)]
                        net_rows = [r for r in qf.index if "Net Income" in str(r)]
                        if rev_rows:
                            val_rev = qf.loc[rev_rows[0]].iloc[0]
                            if pd.notnull(val_rev):
                                q_rev_str = f"${val_rev:,.0f}"
                        if net_rows:
                            val_net = qf.loc[net_rows[0]].iloc[0]
                            if pd.notnull(val_net):
                                q_net_str = f"${val_net:,.0f}"
                except Exception:
                    pass

                # PANEL EJECUTIVO INTELIGENTE
                st.markdown(f"### 💡 Diagnóstico Financiero: **{long_name} ({symbol})**")
                
                # Fila 1
                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                with col_i1:
                    st.metric("Precio Actual", f"${curr_price:,.2f} {currency}", f"{chg_pct:+.2f}%")
                with col_i2:
                    pe_str = f"{pe_ratio:.1f}x" if pe_ratio else "N/A"
                    st.metric("P/E Ratio (Valuación)", pe_str, "Caro > 35 / Barato < 15")
                with col_i3:
                    roe_str = f"{roe*100:.1f}%" if roe else "N/A"
                    st.metric("ROE (¿Da Ganancias?)", roe_str, "Eficiencia del capital")
                with col_i4:
                    rec_display = recommendation.replace("_", " ") if recommendation else "NEUTRAL"
                    st.metric("Opinión Wall Street", rec_display, "Consenso de analistas")

                # Fila 2
                col_j1, col_j2, col_j3, col_j4 = st.columns(4)
                with col_j1:
                    mcap_str = f"${market_cap:,.0f}" if market_cap else "N/A"
                    st.metric("Capitalización Bursátil", mcap_str, "Valor total de mercado")
                with col_j2:
                    shares_str = f"{shares_out:,.0f}" if shares_out else "N/A"
                    st.metric("Acciones en Circulación", shares_str, "Total de títulos vivos")
                with col_j3:
                    st.metric("Ingresos Trimestrales", q_rev_str, "Último reporte trimestral")
                with col_j4:
                    st.metric("Ganancias Trimestrales", q_net_str, "Utilidad neta trimestral")

                # Fila 3
                col_k1, col_k2, col_k3, col_k4 = st.columns(4)
                with col_k1:
                    eps_str = f"${eps:,.2f}" if eps is not None else "N/A"
                    st.metric("Utilidad por Acción (EPS)", eps_str, "Ganancia neta por título")
                with col_k2:
                    div_rate_str = f"${dividend_rate:,.2f}" if dividend_rate is not None else "$0.00"
                    st.metric("Dividendo Anual / Acción", div_rate_str, "Pago anual al inversor")
                with col_k3:
                    div_yield_str = f"{dividend_yield*100:.2f}%" if dividend_yield is not None else "0.00%"
                    st.metric("Rendimiento por Dividendo", div_yield_str, "Yield porcentual anual")
                with col_k4:
                    if dividend_rate is not None and shares_out is not None:
                        total_divs = dividend_rate * shares_out
                        tot_divs_str = f"${total_divs:,.0f}"
                    else:
                        tot_divs_str = "N/A"
                    st.metric("Total Dividendos Pagados", tot_divs_str, "Estimación global anual")

                # Fila 4
                profit_margin = info.get("profitMargins", None)
                debt_to_equity = info.get("debtToEquity", None)
                pb_ratio = info.get("priceToBook", None)
                beta = info.get("beta", None)

                col_l1, col_l2, col_l3, col_l4 = st.columns(4)
                with col_l1:
                    margin_str = f"{profit_margin*100:.1f}%" if profit_margin is not None else "N/A"
                    st.metric("Margen de Utilidad Neta", margin_str, "Eficiencia en ganancias")
                with col_l2:
                    debt_str = f"{debt_to_equity:.1f}%" if debt_to_equity is not None else "N/A"
                    st.metric("Deuda / Capital (D/E)", debt_str, "Nivel de apalancamiento")
                with col_l3:
                    pb_str = f"{pb_ratio:.2f}x" if pb_ratio is not None else "N/A"
                    st.metric("Precio / Valor en Libros", pb_str, "Valuación patrimonial")
                with col_l4:
                    beta_str = f"{beta:.2f}" if beta is not None else "N/A"
                    st.metric("Beta (Volatilidad)", beta_str, "Riesgo frente al mercado")

                st.markdown("---")

                # =============================================================
                # GENERACIÓN DE ANÁLISIS TÉCNICO Y PEDAGÓGICO AVANZADO (HTML)
                # =============================================================
                pe_text = f"Con un P/E de {pe_ratio:.1f}x y un P/B de {pb_ratio:.2f}x, la acción cotiza con una prima exigente, reflejando altas expectativas de crecimiento futuro." if pe_ratio and pe_ratio > 30 else f"P/E de {pe_ratio:.1f}x y P/B de {pb_ratio:.2f}x, sugiriendo una valoración equilibrada frente a sus fundamentales."
                roe_text = f"Destacada eficiencia en la generación de valor con un ROE del {(roe*100):.1f}% y un margen neto del {(profit_margin*100):.1f}%, demostrando un sólido poder de fijación de precios y control de costos." if roe and profit_margin else "Rentabilidad bajo revisión por falta de datos históricos completos."
                risk_text = f"Nivel de apalancamiento (Deuda/Capital) ubicado en un sano {debt_to_equity:.1f}%. El coeficiente Beta de {beta:.2f} indica una volatilidad superior a la media del mercado, ideal para estrategias dinámicas." if debt_to_equity is not None and beta is not None else "Perfil de riesgo moderado bajo las condiciones actuales del sector."
                
                potencial = ((target_price - curr_price) / curr_price) * 100 if target_price and target_price > 0 else 0.0
                target_text = f"El consenso de analistas (Opinión: <b>{recommendation.replace('_', ' ')}</b>) proyecta un precio objetivo medio de <b>${target_price:,.2f}</b>, lo que representa un potencial de retorno estimado de <b>{potencial:+.1f}%</b> desde el precio actual." if target_price else "Sin cobertura de precio objetivo activo por el consenso."

                html_interpretation = (
                    f'<div style="background-color: #e8f4f8; border-left: 5px solid #29b6f6; padding: 18px 20px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; color: #1a202c; margin-bottom: 20px;">'
                    f'<div style="font-size: 1.05rem; font-weight: bold; margin-bottom: 12px; color: #0288d1;">📝 Diagnóstico Financiero Integral y Análisis Técnico:</div>'
                    f'<ul style="margin: 0; padding-left: 20px; line-height: 1.6;">'
                    f'<li style="margin-bottom: 8px;"><b>🏢 Valuación y Múltiplos de Mercado:</b> {pe_text}</li>'
                    f'<li style="margin-bottom: 8px;"><b>📈 Rentabilidad y Calidad Operativa:</b> {roe_text}</li>'
                    f'<li style="margin-bottom: 8px;"><b>⚖️ Estructura de Capital y Riesgo Sistemático (Beta):</b> {risk_text}</li>'
                    f'<li style="margin-bottom: 0px;"><b>🎯 Perspectiva de Wall Street y Consenso:</b> {target_text}</li>'
                    f'</ul>'
                    f'</div>'
                )

                st.markdown(html_interpretation, unsafe_allow_html=True)
                st.markdown("---")
                st.write(f"### Evolución del Precio (Velas Japonesas): **{symbol}**")

                # GRÁFICO DE VELAS CON PLOTLY
                df_hist = df_hist.reset_index()
                fig = go.Figure(
                    data=[
                        go.Candlestick(
                            x=df_hist["Date"],
                            open=df_hist["Open"],
                            high=df_hist["High"],
                            low=df_hist["Low"],
                            close=df_hist["Close"],
                            name=symbol,
                            increasing_line_color="#26a69a",
                            decreasing_line_color="#ef5350",
                        )
                    ]
                )

                fig.update_layout(
                    xaxis_rangeslider_visible=False,
                    template="plotly_dark",
                    margin=dict(l=10, r=10, t=30, b=10),
                    height=450,
                )

                st.plotly_chart(fig, use_container_width=True, key=f"candlestick_chart_{symbol}_{period}")

                col_sub1, col_sub2 = st.columns([3, 1])
                with col_sub1:
                    st.subheader("📊 Resumen de Datos Históricos")
                    st.dataframe(
                        df_hist[["Date", "Open", "High", "Low", "Close", "Volume"]].tail(10),
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
                        key="select_asset_type_save",
                    )
                    if st.button(f"💾 Guardar {symbol} en TiDB", key="save_search_asset"):
                        if PortfolioController.save_market_quote(
                            symbol,
                            long_name,
                            asset_type_input,
                            curr_price,
                            chg_pct,
                        ):
                            st.success(f"✅ {symbol} ({long_name}) guardado en TiDB Cloud.")
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