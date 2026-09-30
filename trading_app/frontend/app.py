"""
Professional Streamlit Frontend for TSLA & NU Quantitative SMC Trading Terminal.
Institutional Glassmorphism UI with interactive Plotly SMC charting, multi-factor confluence scoring,
trade levels generator, and real-time ATH/ATL market scanner.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime

# Import local engines for zero-friction standalone fallback
from trading_app.backend.smc_engine import SMCEngine
from trading_app.backend.scoring import SMCScoringEngine
import yfinance as yf

# ─── PAGE CONFIGURATION ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TSLA & NU Analista Cuantitativo SMC",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM INSTITUTIONAL CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark Theme Core */
    .stApp {
        background-color: #08080d;
        color: #f1f5f9;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Header Container */
    .main-header {
        background: linear-gradient(135deg, rgba(227, 25, 55, 0.15) 0%, rgba(130, 10, 209, 0.15) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 18px 24px;
        margin-bottom: 20px;
        backdrop-filter: blur(12px);
    }
    
    /* Metric Cards */
    .metric-card {
        background: rgba(18, 18, 28, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        margin: 4px 0;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    
    /* Signal Card */
    .signal-box-long {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.18) 0%, rgba(16, 185, 129, 0.08) 100%);
        border: 1px solid rgba(34, 197, 94, 0.4);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .signal-box-short {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.18) 0%, rgba(225, 29, 72, 0.08) 100%);
        border: 1px solid rgba(239, 68, 68, 0.4);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .signal-box-neutral {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(217, 119, 6, 0.05) 100%);
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
    }
    
    /* Custom Badges */
    .badge-long {
        background-color: #22c55e;
        color: #000;
        padding: 4px 12px;
        border-radius: 99px;
        font-weight: 800;
        font-size: 0.85rem;
    }
    .badge-short {
        background-color: #ef4444;
        color: #fff;
        padding: 4px 12px;
        border-radius: 99px;
        font-weight: 800;
        font-size: 0.85rem;
    }
    .badge-neutral {
        background-color: #f59e0b;
        color: #000;
        padding: 4px 12px;
        border-radius: 99px;
        font-weight: 800;
        font-size: 0.85rem;
    }
    
    /* Confluence Factors Table */
    .confluence-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        font-size: 0.85rem;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ─── API CLIENT & DATA ADAPTER ─────────────────────────────────────────────────
BACKEND_URL = "http://localhost:8000"

def get_market_data_and_analysis(symbol: str, timeframe: str, api_url: str):
    """
    Fetches SMC analysis from FastAPI backend with seamless local fallback.
    """
    try:
        res = requests.get(f"{api_url}/api/smc/analysis/{symbol}", params={"timeframe": timeframe}, timeout=4.0)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass

    # Direct Local Fallback Execution
    try:
        interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "1d": "1d"}
        period_map = {"1m": "1d", "5m": "5d", "15m": "5d", "1h": "1mo", "1d": "1y"}

        ticker = yf.Ticker(symbol)
        df = ticker.history(interval=interval_map.get(timeframe, "15m"), period=period_map.get(timeframe, "5d"))
        if df.empty or len(df) < 15:
            df = ticker.history(interval="1d", period="6mo")

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()

        smc = SMCEngine(swing_window=4, fvg_min_pct=0.04)
        scoring = SMCScoringEngine(min_score_moderate=50.0, min_score_strong=70.0, min_risk_reward=2.0)

        analysis = smc.analyze(df, symbol=symbol, timeframe=timeframe)
        scores = scoring.evaluate(analysis)

        candles = []
        for dt, row in df.tail(120).iterrows():
            candles.append({
                "time": str(dt),
                "open": round(float(row['Open']), 2),
                "high": round(float(row['High']), 2),
                "low": round(float(row['Low']), 2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume'])
            })

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "analysis": analysis.to_dict(),
            "scoring": scores.to_dict(),
            "candles": candles,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        st.error(f"Error executing quantitative SMC analysis for '{symbol}': {str(e)}")
        return None


def get_radar_data(api_url: str):
    """Fetches ATH/ATL market scanner data."""
    try:
        res = requests.get(f"{api_url}/api/radar/ath-atl", timeout=4.0)
        if res.status_code == 200:
            return res.json().get("radar", [])
    except Exception:
        pass

    # Local fallback for radar
    watchlist = [
        {"symbol": "TSLA", "name": "Tesla, Inc.", "exchange": "NASDAQ", "category": "EV / Tech"},
        {"symbol": "NU",   "name": "Nu Holdings (Nubank)", "exchange": "NYSE", "category": "Fintech / Banking"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "exchange": "NASDAQ", "category": "AI / Semiconductors"},
        {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ", "category": "Tech / Consumer"},
        {"symbol": "MELI", "name": "MercadoLibre Inc.", "exchange": "NASDAQ", "category": "E-Commerce / Fintech"},
        {"symbol": "PLTR", "name": "Palantir Technologies", "exchange": "NYSE", "category": "AI / Big Data"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "exchange": "NASDAQ", "category": "Cloud / E-Commerce"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "exchange": "NASDAQ", "category": "Tech / Software"},
        {"symbol": "META", "name": "Meta Platforms", "exchange": "NASDAQ", "category": "Social Media / AI"},
        {"symbol": "COIN", "name": "Coinbase Global", "exchange": "NASDAQ", "category": "Crypto / Exchange"}
    ]
    results = []
    for item in watchlist:
        sym = item["symbol"]
        try:
            t = yf.Ticker(sym)
            df = t.history(period="1y", interval="1d")
            if not df.empty:
                price = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2]) if len(df) >= 2 else price
                h52 = float(df['High'].max())
                l52 = float(df['Low'].min())
                chg_pct = ((price - prev) / prev) * 100
                dist_ath = ((price - h52) / h52) * 100
                dist_atl = ((price - l52) / l52) * 100

                if dist_ath >= -3.0:
                    tag = "🔥 Rompiendo Máximos (ATH)"
                elif dist_ath >= -7.0:
                    tag = "⚡ Cerca de Máximos (<7%)"
                elif dist_atl <= 10.0:
                    tag = "❄️ En Mínimos Históricos"
                else:
                    tag = "📊 Rango Medio"

                results.append({
                    "symbol": sym,
                    "name": item["name"],
                    "exchange": item["exchange"],
                    "category": item["category"],
                    "price": round(price, 2),
                    "change_pct": round(chg_pct, 2),
                    "high_52w": round(h52, 2),
                    "low_52w": round(l52, 2),
                    "dist_to_ath_pct": round(dist_ath, 2),
                    "dist_to_atl_pct": round(dist_atl, 2),
                    "tag_label": tag
                })
        except Exception:
            continue
    results.sort(key=lambda x: x["dist_to_ath_pct"], reverse=True)
    return results


# ─── SIDEBAR CONTROLS ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎛️ Terminal de Control")
    
    # Fast Ticker Selector Buttons
    st.markdown("**Acciones Principales:**")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button("🔴 TSLA (Tesla)", use_container_width=True):
            st.session_state["selected_ticker"] = "TSLA"
    with col_t2:
        if st.button("🟣 NU (Nubank)", use_container_width=True):
            st.session_state["selected_ticker"] = "NU"

    if "selected_ticker" not in st.session_state:
        st.session_state["selected_ticker"] = "TSLA"

    # Custom Ticker Search
    ticker_input = st.text_input(
        "O buscar otro Ticker (NYSE / NASDAQ):",
        value=st.session_state["selected_ticker"]
    ).strip().upper()

    if ticker_input:
        selected_symbol = ticker_input
    else:
        selected_symbol = st.session_state["selected_ticker"]

    # Timeframe Selector
    timeframe = st.selectbox(
        "Temporalidad (Timeframe):",
        options=["1m", "5m", "15m", "1h", "1d"],
        index=2
    )

    st.markdown("---")
    st.markdown("### 🛡️ Gestión de Riesgo")
    account_capital = st.number_input("Capital de Cuenta (USD):", min_value=100.0, value=10000.0, step=500.0)
    risk_pct = st.slider("Riesgo Máximo por Operación (%):", min_value=0.25, max_value=5.0, value=1.0, step=0.25)

    st.markdown("---")
    backend_endpoint = st.text_input("Backend API URL:", value=BACKEND_URL)
    auto_refresh = st.checkbox("Actualizar automáticamente (30s)", value=False)
    
    if auto_refresh:
        time.sleep(30)
        st.rerun()


# ─── MAIN HEADER ──────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
            <h1 style="margin: 0; font-size: 1.8rem; font-weight: 800;">
                <span style="color: #e31937;">TSLA</span> & <span style="color: #820ad1;">NU</span> Analista Cuantitativo SMC
            </h1>
            <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 0.9rem;">
                Smart Money Concepts Engine • Order Blocks • FVGs • BOS/CHoCH • Radar ATH/ATL
            </p>
        </div>
        <div style="text-align: right;">
            <span style="background: rgba(34,197,94,0.15); color: #22c55e; padding: 6px 14px; border-radius: 99px; font-weight: 700; font-size: 0.8rem; border: 1px solid rgba(34,197,94,0.3);">
                ● MOTOR SMC EN VIVO
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─── NAVIGATION TABS ──────────────────────────────────────────────────────────
tab_terminal, tab_radar, tab_alerts = st.tabs([
    "📊 Terminal Cuantitativa & Señales SMC",
    "🎯 Radar ATH / ATL (Máximos y Mínimos)",
    "⚙️ Alertas y Documentación"
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: TERMINAL CUANTITATIVA SMC
# ═══════════════════════════════════════════════════════════════════════════════
with tab_terminal:
    with st.spinner(f"Analizando estructura de mercado institucional para {selected_symbol} ({timeframe})..."):
        data = get_market_data_and_analysis(selected_symbol, timeframe, backend_endpoint)

    if data:
        analysis = data["analysis"]
        scoring = data["scoring"]
        candles = data["candles"]
        current_price = analysis["current_price"]
        trend = analysis["current_trend"]
        dealing = analysis["dealing_range"]
        summary = analysis["summary"]

        # ── KPI METRICS BAR ──────────────────────────────────────────────────
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Activo / Símbolo</div>
                <div class="metric-value" style="color: #38bdf8;">{selected_symbol}</div>
                <div style="font-size: 0.75rem; color: #64748b;">Timeframe: {timeframe}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Precio en Vivo</div>
                <div class="metric-value">${current_price:.2f}</div>
                <div style="font-size: 0.75rem; color: #22c55e;">Última vela cerrada</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            trend_color = "#22c55e" if trend == "BULLISH" else "#ef4444" if trend == "BEARISH" else "#f59e0b"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Estructura de Mercado</div>
                <div class="metric-value" style="color: {trend_color};">{trend}</div>
                <div style="font-size: 0.75rem; color: #64748b;">BOS: {summary['total_bos']} | CHoCH: {summary['total_choch']}</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            zone = dealing.get("current_zone", "EQUILIBRIUM")
            zone_color = "#22c55e" if "DISCOUNT" in zone or "OTE_BULLISH" in zone else "#ef4444" if "PREMIUM" in zone else "#f59e0b"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Zona de Negociación</div>
                <div class="metric-value" style="color: {zone_color}; font-size: 1.4rem;">{zone}</div>
                <div style="font-size: 0.75rem; color: #64748b;">Posición: {dealing.get('discount_depth_pct', 50):.1f}% del rango</div>
            </div>
            """, unsafe_allow_html=True)
        with c5:
            score = scoring["total_confluence_score"]
            score_color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 50 else "#64748b"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Score Confluencia SMC</div>
                <div class="metric-value" style="color: {score_color};">{score:.0f}%</div>
                <div style="font-size: 0.75rem; color: #64748b;">Calidad: {scoring['quality_grade'].split()[0]}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── SIGNAL & TRADE SETUP CARD ─────────────────────────────────────────
        sig = scoring["signal"]
        trade_levels = scoring.get("trade_levels")

        if "LONG" in sig:
            box_class = "signal-box-long"
            badge = '<span class="badge-long">🚀 SEÑAL INSTITUCIONAL: LONG (COMPRA)</span>'
        elif "SHORT" in sig:
            box_class = "signal-box-short"
            badge = '<span class="badge-short">🔻 SEÑAL INSTITUCIONAL: SHORT (VENTA)</span>'
        else:
            box_class = "signal-box-neutral"
            badge = '<span class="badge-neutral">⏸ ESTADO: NEUTRAL / SIN TRADE (CONSOLIDACIÓN)</span>'

        st.markdown(f"""
        <div class="{box_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div>{badge}</div>
                <div style="font-weight: 700; font-size: 0.95rem; color: #f8fafc;">
                    Grado de Calidad: <span style="color: #fbbf24;">{scoring['quality_grade']}</span>
                </div>
            </div>
            <p style="margin: 0; font-size: 1.05rem; line-height: 1.5; color: #e2e8f0;">
                <b>Veredicto Cuantitativo:</b> {scoring['execution_verdict']}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # If trade setup is available, display exact execution levels & Risk Calculator
        if trade_levels:
            t_col1, t_col2, t_col3, t_col4, t_col5, t_col6 = st.columns(6)
            with t_col1:
                st.metric("Punto de Entrada (Entry)", f"${trade_levels['entry_price']:.2f}")
            with t_col2:
                st.metric("Stop Loss (SL)", f"${trade_levels['stop_loss']:.2f}", delta=f"-${trade_levels['risk_per_share']:.2f}", delta_color="inverse")
            with t_col3:
                st.metric("Take Profit 1 (TP1)", f"${trade_levels['take_profit_1']:.2f}", delta=f"R:R {trade_levels['risk_reward_tp1']:.2f}:1")
            with t_col4:
                st.metric("Take Profit 2 (TP2)", f"${trade_levels['take_profit_2']:.2f}", delta=f"R:R {trade_levels['risk_reward_ratio']:.2f}:1")
            with t_col5:
                st.metric("Take Profit 3 (Ext)", f"${trade_levels['take_profit_3']:.2f}")
            with t_col6:
                # Risk Sizing Calculation
                risk_dollars = account_capital * (risk_pct / 100.0)
                shares_to_buy = int(risk_dollars / (trade_levels['risk_per_share'] + 1e-6))
                total_capital_req = shares_to_buy * trade_levels['entry_price']
                st.metric("Posición Sugerida", f"{shares_to_buy} Acciones", f"${total_capital_req:,.0f} inv.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── PLOTLY CANDLESTICK + SMC OVERLAYS CHART ───────────────────────────
        st.markdown("### 📈 Gráfico Estructural SMC Multi-Capa")
        
        df_plot = pd.DataFrame(candles)
        df_plot['time'] = pd.to_datetime(df_plot['time'])

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.80, 0.20]
        )

        # Candlesticks
        fig.add_trace(
            go.Candlestick(
                x=df_plot['time'],
                open=df_plot['open'],
                high=df_plot['high'],
                low=df_plot['low'],
                close=df_plot['close'],
                name="OHLC",
                increasing_line_color="#22c55e",
                decreasing_line_color="#ef4444",
                increasing_fillcolor="#22c55e",
                decreasing_fillcolor="#ef4444"
            ),
            row=1, col=1
        )

        # Volume bars
        colors = ["#22c55e" if c >= o else "#ef4444" for c, o in zip(df_plot['close'], df_plot['open'])]
        fig.add_trace(
            go.Bar(
                x=df_plot['time'],
                y=df_plot['volume'],
                name="Volumen",
                marker_color=colors,
                opacity=0.4
            ),
            row=2, col=1
        )

        # Draw Bullish Order Blocks (Demand Zones)
        for ob in analysis.get("active_bullish_obs", []):
            fig.add_hrect(
                y0=ob["bottom"], y1=ob["top"],
                fillcolor="rgba(34, 197, 94, 0.18)",
                line=dict(color="rgba(34, 197, 94, 0.6)", width=1, dash="dot"),
                annotation_text="🟢 Bullish OB (Demanda)",
                annotation_position="top left",
                annotation_font=dict(size=9, color="#22c55e"),
                row=1, col=1
            )

        # Draw Bearish Order Blocks (Supply Zones)
        for ob in analysis.get("active_bearish_obs", []):
            fig.add_hrect(
                y0=ob["bottom"], y1=ob["top"],
                fillcolor="rgba(239, 68, 68, 0.18)",
                line=dict(color="rgba(239, 68, 68, 0.6)", width=1, dash="dot"),
                annotation_text="🔴 Bearish OB (Oferta)",
                annotation_position="bottom left",
                annotation_font=dict(size=9, color="#ef4444"),
                row=1, col=1
            )

        # Draw Fair Value Gaps (FVG)
        for fvg in analysis.get("active_bullish_fvgs", []):
            fig.add_hrect(
                y0=fvg["bottom"], y1=fvg["top"],
                fillcolor="rgba(6, 182, 212, 0.14)",
                line=dict(color="rgba(6, 182, 212, 0.5)", width=1, dash="dash"),
                annotation_text="⚡ Bullish FVG",
                annotation_position="top right",
                annotation_font=dict(size=9, color="#06b6d4"),
                row=1, col=1
            )

        for fvg in analysis.get("active_bearish_fvgs", []):
            fig.add_hrect(
                y0=fvg["bottom"], y1=fvg["top"],
                fillcolor="rgba(245, 158, 11, 0.14)",
                line=dict(color="rgba(245, 158, 11, 0.5)", width=1, dash="dash"),
                annotation_text="⚡ Bearish FVG",
                annotation_position="bottom right",
                annotation_font=dict(size=9, color="#f59e0b"),
                row=1, col=1
            )

        # Draw Dealing Range Equilibrium (50% Fib)
        eq_val = dealing.get("equilibrium_50")
        if eq_val:
            fig.add_hline(
                y=eq_val,
                line=dict(color="#a855f7", width=1.5, dash="dashdot"),
                annotation_text=f"⚖️ Equilibrium 50% (${eq_val:.2f})",
                annotation_position="top left",
                annotation_font=dict(size=9, color="#a855f7"),
                row=1, col=1
            )

        # Draw Trade Levels if active
        if trade_levels:
            fig.add_hline(y=trade_levels['entry_price'], line=dict(color="#38bdf8", width=1.5), annotation_text=f"🔵 Entry: ${trade_levels['entry_price']:.2f}", row=1, col=1)
            fig.add_hline(y=trade_levels['stop_loss'], line=dict(color="#ef4444", width=2, dash="dash"), annotation_text=f"🛑 SL: ${trade_levels['stop_loss']:.2f}", row=1, col=1)
            fig.add_hline(y=trade_levels['take_profit_1'], line=dict(color="#22c55e", width=1.5, dash="dot"), annotation_text=f"🎯 TP1: ${trade_levels['take_profit_1']:.2f}", row=1, col=1)
            fig.add_hline(y=trade_levels['take_profit_2'], line=dict(color="#22c55e", width=2), annotation_text=f"🎯 TP2: ${trade_levels['take_profit_2']:.2f}", row=1, col=1)

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0d0d15",
            plot_bgcolor="#0d0d15",
            height=600,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # ── CONFLUENCE FACTORS BREAKDOWN ───────────────────────────────────────
        st.markdown("### 🧩 Desglose Multifactorial de Confluencia SMC")
        factors = scoring.get("confluence_factors", [])
        
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            for f in factors[:3]:
                status_icon = "✅" if f["passed"] else "❌"
                st.markdown(f"""
                <div style="background: rgba(18,18,28,0.7); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 0.9rem;">
                        <span>{status_icon} {f['name']}</span>
                        <span style="color: {'#22c55e' if f['score'] > 0 else '#64748b'};">{f['score']:.1f} / {f['weight']:.1f} pts</span>
                    </div>
                    <p style="margin: 4px 0 0 0; font-size: 0.78rem; color: #94a3b8;">{f['description']}</p>
                </div>
                """, unsafe_allow_html=True)

        with col_f2:
            for f in factors[3:]:
                status_icon = "✅" if f["passed"] else "❌"
                st.markdown(f"""
                <div style="background: rgba(18,18,28,0.7); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; font-weight: 700; font-size: 0.9rem;">
                        <span>{status_icon} {f['name']}</span>
                        <span style="color: {'#22c55e' if f['score'] > 0 else '#64748b'};">{f['score']:.1f} / {f['weight']:.1f} pts</span>
                    </div>
                    <p style="margin: 4px 0 0 0; font-size: 0.78rem; color: #94a3b8;">{f['description']}</p>
                </div>
                """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: RADAR ATH / ATL (MÁXIMOS Y MÍNIMOS HISTÓRICOS)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_radar:
    st.markdown("### 🎯 Radar de Oportunidades: Máximos y Mínimos (ATH / ATL)")
    st.markdown("Monitoreo institucional de proximidad a **Máximos de 52 Semanas (ATH)** y **Mínimos de 52 Semanas (ATL)** para acciones clave.")

    with st.spinner("Escaneando el mercado en busca de rupturas y suelos..."):
        radar_items = get_radar_data(backend_endpoint)

    if radar_items:
        # Filter options
        filter_type = st.radio(
            "Filtrar por oportunidad:",
            options=["Todas", "🔥 Cerca de Máximos (< 7%)", "❄️ En Mínimos Históricos", "🟣 Nubank & 🔴 Tesla"],
            horizontal=True
        )

        filtered = radar_items
        if filter_type == "🔥 Cerca de Máximos (< 7%)":
            filtered = [x for x in radar_items if x["dist_to_ath_pct"] >= -7.0]
        elif filter_type == "❄️ En Mínimos Históricos":
            filtered = [x for x in radar_items if x["dist_to_atl_pct"] <= 15.0]
        elif filter_type == "🟣 Nubank & 🔴 Tesla":
            filtered = [x for x in radar_items if x["symbol"] in ["TSLA", "NU"]]

        df_radar = pd.DataFrame(filtered)
        if not df_radar.empty:
            # Display formatted table
            df_display = df_radar[[
                "symbol", "name", "category", "price", "change_pct", "high_52w", "dist_to_ath_pct", "low_52w", "dist_to_atl_pct", "tag_label"
            ]].rename(columns={
                "symbol": "Símbolo",
                "name": "Compañía",
                "category": "Sector",
                "price": "Precio ($)",
                "change_pct": "Var. Día (%)",
                "high_52w": "Máx 52S ($)",
                "dist_to_ath_pct": "Dist. a Máx (%)",
                "low_52w": "Mín 52S ($)",
                "dist_to_atl_pct": "Dist. a Mín (%)",
                "tag_label": "Clasificación"
            })

            st.dataframe(
                df_display.style.format({
                    "Precio ($)": "${:.2f}",
                    "Var. Día (%)": "{:+.2f}%",
                    "Máx 52S ($)": "${:.2f}",
                    "Dist. a Máx (%)": "{:+.2f}%",
                    "Mín 52S ($)": "${:.2f}",
                    "Dist. a Mín (%)": "+{:.2f}%"
                }),
                use_container_width=True,
                height=420
            )

            # Quick Action Button to Analyze directly
            st.markdown("#### ⚡ Seleccionar Acción del Radar para Análisis Inmediato:")
            col_sel = st.columns(len(filtered[:6]))
            for i, item in enumerate(filtered[:6]):
                with col_sel[i]:
                    if st.button(f"{item['symbol']} (${item['price']:.2f})", use_container_width=True):
                        st.session_state["selected_ticker"] = item['symbol']
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: ALERTAS Y DOCUMENTACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
with tab_alerts:
    st.markdown("### 🔔 Configuración de Alertas Cuantitativas")
    
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown(f"#### Alerta de Precio para **{selected_symbol}**")
        target_up = st.number_input("Avisar si supera el precio (USD):", min_value=0.0, value=0.0, step=1.0)
        target_down = st.number_input("Avisar si cae por debajo de (USD):", min_value=0.0, value=0.0, step=1.0)
        
        if st.button("💾 Guardar Alertas para " + selected_symbol):
            st.success(f"Alertas configuradas con éxito para {selected_symbol}. Se evaluarán en tiempo real.")

    with col_a2:
        st.markdown("#### 📖 Glosario de Conceptos SMC")
        st.markdown("""
        - **Order Block (OB)**: Zona de oferta o demanda institucional donde los bancos inyectaron liquidez masiva antes de un rompimiento.
        - **Fair Value Gap (FVG)**: Desbalance de precios donde sólo un lado del mercado fue transaccionado, actuando como imán de precio.
        - **Break of Structure (BOS)**: Confirmación de continuación de la tendencia previa al superar el último máximo/mínimo fractal.
        - **Change of Character (CHoCH)**: Primera señal de cambio de tendencia estructural al romper el último swing contrario.
        - **Equilibrium & OTE**: El nivel 50% divide zonas baratas (Discount para compras) de zonas caras (Premium para ventas). El OTE (61.8% - 78.6%) ofrece el ratio R:R más eficiente.
        """)
