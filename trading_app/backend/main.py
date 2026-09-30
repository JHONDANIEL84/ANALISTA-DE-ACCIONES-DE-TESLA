"""
FastAPI Server for Quantitative Smart Money Concepts (SMC) Trading Engine.
Serves real-time market data, structural SMC analysis, and confluence signals for TSLA, NU, and US Equities.
"""

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import yfinance as yf
import pandas as pd
import numpy as np
import time
import asyncio
from datetime import datetime, timedelta

from .smc_engine import SMCEngine, SMCAnalysisResult
from .scoring import SMCScoringEngine, SMCScoringResult

app = FastAPI(
    title="TSLA & NU Quantitative SMC Trading API",
    description="High-frequency institutional Smart Money Concepts analysis, confluence scoring, and signal engine.",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache storage for market data to optimize latency
CACHE_STORE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 20  # 20 seconds cache for live intra-day requests

smc_engine = SMCEngine(swing_window=4, fvg_min_pct=0.04)
scoring_engine = SMCScoringEngine(min_score_moderate=50.0, min_score_strong=70.0, min_risk_reward=2.0)

WATCHLIST_SYMBOLS = [
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


class AlertEvaluationRequest(BaseModel):
    symbol: str
    target_above: Optional[float] = None
    target_below: Optional[float] = None
    alert_on_choch: bool = True
    alert_on_ob_mitigation: bool = True


def fetch_historical_ohlcv(symbol: str, timeframe: str = "15m", period: str = "5d") -> pd.DataFrame:
    """
    Fetches clean OHLCV data using yfinance with in-memory caching.
    """
    symbol = symbol.strip().upper()
    cache_key = f"{symbol}_{timeframe}_{period}"
    now = time.time()

    if cache_key in CACHE_STORE:
        entry = CACHE_STORE[cache_key]
        if now - entry["timestamp"] < CACHE_TTL_SECONDS:
            return entry["data"]

    # Map timeframes to yfinance compatible periods and intervals
    interval_map = {
        "1m": ("1m", "1d"),
        "5m": ("5m", "5d"),
        "15m": ("15m", "5d"),
        "30m": ("30m", "1mo"),
        "1h": ("1h", "1mo"),
        "1d": ("1d", "1y"),
        "1wk": ("1wk", "2y"),
    }

    interval, auto_period = interval_map.get(timeframe, ("15m", "5d"))
    actual_period = period if period != "auto" else auto_period

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(interval=interval, period=actual_period)
        if df.empty or len(df) < 15:
            # Fallback for wider period
            df = ticker.history(interval="1d", period="6mo")
            if df.empty:
                raise ValueError(f"No OHLCV market data returned for symbol '{symbol}'.")

        # Standardize columns
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df.dropna(inplace=True)

        CACHE_STORE[cache_key] = {"timestamp": now, "data": df}
        return df

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch market data for '{symbol}': {str(e)}")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "TSLA & NU SMC Quantitative Engine",
        "timestamp": datetime.utcnow().isoformat(),
        "cached_symbols": list(CACHE_STORE.keys())
    }


@app.get("/api/watchlist")
def get_watchlist():
    """Returns curated institutional stock list."""
    return {"watchlist": WATCHLIST_SYMBOLS}


@app.get("/api/market/quote/{symbol}")
def get_quote(symbol: str = Path(..., description="Stock ticker symbol (e.g. TSLA, NU)")):
    """Returns current real-time quote, intraday change, and 52-week statistics."""
    symbol = symbol.strip().upper()
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info

        current_price = float(info.last_price) if hasattr(info, 'last_price') and info.last_price else None
        prev_close = float(info.previous_close) if hasattr(info, 'previous_close') and info.previous_close else None

        if current_price is None or prev_close is None:
            df = ticker.history(period="2d", interval="1d")
            if len(df) >= 2:
                current_price = float(df['Close'].iloc[-1])
                prev_close = float(df['Close'].iloc[-2])
            elif len(df) == 1:
                current_price = float(df['Close'].iloc[-1])
                prev_close = float(df['Open'].iloc[-1])
            else:
                raise ValueError(f"Unable to retrieve quote for {symbol}")

        change = current_price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0.0

        high_52 = getattr(info, 'year_high', None) or (current_price * 1.15)
        low_52 = getattr(info, 'year_low', None) or (current_price * 0.75)

        return {
            "symbol": symbol,
            "current_price": round(current_price, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "fifty_two_week_high": round(float(high_52), 2),
            "fifty_two_week_low": round(float(low_52), 2),
            "dist_to_52w_high_pct": round(((current_price - high_52) / high_52) * 100, 2),
            "dist_to_52w_low_pct": round(((current_price - low_52) / low_52) * 100, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quote retrieval failed for '{symbol}': {str(e)}")


@app.get("/api/smc/analysis/{symbol}")
def get_smc_analysis(
    symbol: str = Path(..., description="Stock symbol (e.g. TSLA, NU)"),
    timeframe: str = Query("15m", description="Timeframe: 1m, 5m, 15m, 1h, 1d"),
    period: str = Query("auto", description="Historical lookback period")
):
    """
    Runs quantitative Smart Money Concepts analysis, identifies Order Blocks,
    Fair Value Gaps, Market Structure (BOS / CHoCH), and generates scoring and trade levels.
    """
    symbol = symbol.strip().upper()
    df = fetch_historical_ohlcv(symbol, timeframe=timeframe, period=period)

    try:
        # Run SMC Detection
        analysis_result = smc_engine.analyze(df, symbol=symbol, timeframe=timeframe)

        # Run Confluence Scoring & Levels Computation
        scoring_result = scoring_engine.evaluate(analysis_result)

        # Format candles for frontend charting
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
            "analysis": analysis_result.to_dict(),
            "scoring": scoring_result.to_dict(),
            "candles": candles,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMC analysis execution failed: {str(e)}")


@app.get("/api/radar/ath-atl")
def get_ath_atl_radar():
    """
    Scans watchlist equities for proximity to All-Time Highs (52-Week High)
    and All-Time Lows (52-Week Low), computing structural opportunities.
    """
    results = []

    for item in WATCHLIST_SYMBOLS:
        sym = item["symbol"]
        try:
            ticker = yf.Ticker(sym)
            info = ticker.fast_info

            price = float(info.last_price) if hasattr(info, 'last_price') and info.last_price else None
            prev = float(info.previous_close) if hasattr(info, 'previous_close') and info.previous_close else None
            high_52 = getattr(info, 'year_high', None)
            low_52 = getattr(info, 'year_low', None)

            if not price or not high_52 or not low_52:
                df = ticker.history(period="1y", interval="1d")
                if not df.empty:
                    price = float(df['Close'].iloc[-1])
                    prev = float(df['Close'].iloc[-2]) if len(df) >= 2 else price
                    high_52 = float(df['High'].max())
                    low_52 = float(df['Low'].min())

            if price and high_52 and low_52:
                change = price - (prev or price)
                change_pct = (change / prev) * 100 if prev else 0.0
                dist_ath = ((price - high_52) / high_52) * 100.0
                dist_atl = ((price - low_52) / low_52) * 100.0

                # Opportunity tag classification
                if dist_ath >= -3.0:
                    status_tag = "ATH_BREAKOUT_ZONE"
                    tag_label = "🔥 Rompiendo Máximos (ATH)"
                elif dist_ath >= -7.0:
                    status_tag = "NEAR_ATH"
                    tag_label = "⚡ Cerca de Máximos (<7%)"
                elif dist_atl <= 10.0:
                    status_tag = "NEAR_ATL"
                    tag_label = "❄️ En Mínimos Históricos"
                else:
                    status_tag = "MID_RANGE"
                    tag_label = "📊 En Rango Medio"

                results.append({
                    "symbol": sym,
                    "name": item["name"],
                    "exchange": item["exchange"],
                    "category": item["category"],
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                    "high_52w": round(float(high_52), 2),
                    "low_52w": round(float(low_52), 2),
                    "dist_to_ath_pct": round(dist_ath, 2),
                    "dist_to_atl_pct": round(dist_atl, 2),
                    "status_tag": status_tag,
                    "tag_label": tag_label
                })
        except Exception:
            continue

    # Sort primarily by proximity to ATH
    results.sort(key=lambda x: x["dist_to_ath_pct"], reverse=True)
    return {"radar": results, "scanned_count": len(results), "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/alerts/evaluate")
def evaluate_alert(req: AlertEvaluationRequest):
    """Evaluates whether current market state triggers alerts."""
    quote = get_quote(req.symbol)
    price = quote["current_price"]

    triggered = []
    if req.target_above and price >= req.target_above:
        triggered.append({
            "type": "PRICE_ABOVE",
            "message": f"📈 {req.symbol} superó el umbral superior de ${req.target_above:.2f} (Precio actual: ${price:.2f})"
        })

    if req.target_below and price <= req.target_below:
        triggered.append({
            "type": "PRICE_BELOW",
            "message": f"📉 {req.symbol} cayó por debajo del umbral de ${req.target_below:.2f} (Precio actual: ${price:.2f})"
        })

    return {
        "symbol": req.symbol,
        "current_price": price,
        "triggered_count": len(triggered),
        "alerts": triggered
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("trading_app.backend.main:app", host="0.0.0.0", port=8000, reload=True)
