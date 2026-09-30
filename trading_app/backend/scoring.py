"""
Quantitative Confluence & Trade Setup Scoring Engine.
Evaluates SMC signals, assigns multi-factor weights, and computes
exact Entry, Stop Loss, Take Profit targets, and Risk:Reward ratios.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from .smc_engine import SMCAnalysisResult


@dataclass
class ConfluenceFactor:
    name: str
    weight: float
    score: float
    passed: bool
    description: str


@dataclass
class TradeLevels:
    direction: str  # 'LONG', 'SHORT', 'NEUTRAL'
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_per_share: float
    risk_reward_ratio: float
    risk_reward_tp1: float


@dataclass
class SMCScoringResult:
    symbol: str
    timeframe: str
    signal: str  # 'STRONG_LONG', 'MODERATE_LONG', 'STRONG_SHORT', 'MODERATE_SHORT', 'NEUTRAL'
    bias: str    # 'BULLISH', 'BEARISH', 'NEUTRAL'
    total_confluence_score: float  # 0.0 to 100.0
    quality_grade: str             # 'A+ (Institutional Setup)', 'A', 'B', 'C (No Trade)'
    confluence_factors: List[Dict[str, Any]]
    trade_levels: Optional[Dict[str, Any]]
    execution_verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SMCScoringEngine:
    """
    Evaluates confluence score based on institutional SMC factors.
    """

    def __init__(
        self,
        min_score_moderate: float = 50.0,
        min_score_strong: float = 70.0,
        min_risk_reward: float = 2.0
    ):
        self.min_score_moderate = min_score_moderate
        self.min_score_strong = min_score_strong
        self.min_risk_reward = min_risk_reward

    def evaluate(self, analysis: SMCAnalysisResult) -> SMCScoringResult:
        current_price = analysis.current_price
        current_trend = analysis.current_trend
        dealing_range = analysis.dealing_range
        structure_events = analysis.structure_events
        bull_obs = analysis.active_bullish_obs
        bear_obs = analysis.active_bearish_obs
        bull_fvgs = analysis.active_bullish_fvgs
        bear_fvgs = analysis.active_bearish_fvgs
        sweeps = analysis.liquidity_sweeps

        # -------------------------------------------------------------
        # 1. EVALUATE BULLISH (LONG) FACTORS
        # -------------------------------------------------------------
        long_factors: List[ConfluenceFactor] = []

        # 1.1 Structure / Trend (25%)
        trend_score = 25.0 if current_trend == 'BULLISH' else 0.0
        has_bull_choch = any(e['event_type'] == 'CHOCH' and e['direction'] == 'BULLISH' for e in structure_events[-3:])
        if has_bull_choch:
            trend_score = 25.0
        long_factors.append(ConfluenceFactor(
            name="Market Structure (Trend / CHoCH)",
            weight=25.0,
            score=trend_score,
            passed=trend_score >= 20.0,
            description=f"Current structure is {current_trend}. Bullish continuation or recent Bullish CHoCH confirmed."
        ))

        # 1.2 Order Block Alignment (25%)
        # Check if price is within or near a Bullish OB (within 1.5% distance)
        ob_score = 0.0
        nearest_bull_ob = None
        for ob in bull_obs:
            top = ob['top']
            bottom = ob['bottom']
            if bottom <= current_price <= top * 1.015:
                ob_score = 25.0
                nearest_bull_ob = ob
                break
            elif current_price >= top and (current_price - top) / top <= 0.02:
                ob_score = 15.0
                nearest_bull_ob = ob
                break

        long_factors.append(ConfluenceFactor(
            name="Demand Zone (Bullish Order Block)",
            weight=25.0,
            score=ob_score,
            passed=ob_score >= 15.0,
            description=f"Price is located in institutional demand zone ({nearest_bull_ob['bottom']:.2f} - {nearest_bull_ob['top']:.2f})" if nearest_bull_ob else "No immediate Bullish Order Block mitigation."
        ))

        # 1.3 Fair Value Gap Imbalance (20%)
        fvg_score = 0.0
        nearest_bull_fvg = None
        for fvg in bull_fvgs:
            top = fvg['top']
            bottom = fvg['bottom']
            if bottom <= current_price <= top * 1.01:
                fvg_score = 20.0
                nearest_bull_fvg = fvg
                break
        long_factors.append(ConfluenceFactor(
            name="Imbalance / Bullish FVG Tap",
            weight=20.0,
            score=fvg_score,
            passed=fvg_score >= 15.0,
            description=f"Price reacting inside Bullish FVG ({nearest_bull_fvg['bottom']:.2f} - {nearest_bull_fvg['top']:.2f})" if nearest_bull_fvg else "No active Bullish FVG interaction."
        ))

        # 1.4 Dealing Range & Discount Zone (15%)
        range_zone = dealing_range.get('current_zone', 'EQUILIBRIUM')
        range_score = 0.0
        if range_zone in ['DISCOUNT', 'OTE_BULLISH']:
            range_score = 15.0
        elif range_zone == 'EQUILIBRIUM':
            range_score = 7.5
        long_factors.append(ConfluenceFactor(
            name="Dealing Range Discount / OTE",
            weight=15.0,
            score=range_score,
            passed=range_score >= 12.0,
            description=f"Current price is in {range_zone} ({dealing_range.get('discount_depth_pct', 50):.1f}% of range). Favorable risk profile."
        ))

        # 1.5 Liquidity Sweep (15%)
        sweep_score = 0.0
        recent_sell_sweeps = [s for s in sweeps if s['sweep_type'] == 'SELL_SIDE']
        if recent_sell_sweeps:
            sweep_score = 15.0
        long_factors.append(ConfluenceFactor(
            name="Sell-Side Liquidity Sweep (Purge)",
            weight=15.0,
            score=sweep_score,
            passed=sweep_score > 0,
            description="Institutional purge of sell-side liquidity below recent lows detected." if sweep_score > 0 else "No recent Sell-Side Liquidity sweep."
        ))

        total_long_score = sum(f.score for f in long_factors)

        # -------------------------------------------------------------
        # 2. EVALUATE BEARISH (SHORT) FACTORS
        # -------------------------------------------------------------
        short_factors: List[ConfluenceFactor] = []

        # 2.1 Trend / Structure
        trend_short_score = 25.0 if current_trend == 'BEARISH' else 0.0
        has_bear_choch = any(e['event_type'] == 'CHOCH' and e['direction'] == 'BEARISH' for e in structure_events[-3:])
        if has_bear_choch:
            trend_short_score = 25.0
        short_factors.append(ConfluenceFactor(
            name="Market Structure (Trend / CHoCH)",
            weight=25.0,
            score=trend_short_score,
            passed=trend_short_score >= 20.0,
            description=f"Current structure is {current_trend}. Bearish continuation or recent Bearish CHoCH confirmed."
        ))

        # 2.2 Bearish Order Block
        ob_short_score = 0.0
        nearest_bear_ob = None
        for ob in bear_obs:
            top = ob['top']
            bottom = ob['bottom']
            if bottom * 0.985 <= current_price <= top:
                ob_short_score = 25.0
                nearest_bear_ob = ob
                break
            elif current_price <= bottom and (bottom - current_price) / bottom <= 0.02:
                ob_short_score = 15.0
                nearest_bear_ob = ob
                break
        short_factors.append(ConfluenceFactor(
            name="Supply Zone (Bearish Order Block)",
            weight=25.0,
            score=ob_short_score,
            passed=ob_short_score >= 15.0,
            description=f"Price is located in institutional supply zone ({nearest_bear_ob['bottom']:.2f} - {nearest_bear_ob['top']:.2f})" if nearest_bear_ob else "No immediate Bearish Order Block mitigation."
        ))

        # 2.3 Bearish FVG
        fvg_short_score = 0.0
        nearest_bear_fvg = None
        for fvg in bear_fvgs:
            top = fvg['top']
            bottom = fvg['bottom']
            if bottom * 0.99 <= current_price <= top:
                fvg_short_score = 20.0
                nearest_bear_fvg = fvg
                break
        short_factors.append(ConfluenceFactor(
            name="Imbalance / Bearish FVG Tap",
            weight=20.0,
            score=fvg_short_score,
            passed=fvg_short_score >= 15.0,
            description=f"Price reacting inside Bearish FVG ({nearest_bear_fvg['bottom']:.2f} - {nearest_bear_fvg['top']:.2f})" if nearest_bear_fvg else "No active Bearish FVG interaction."
        ))

        # 2.4 Dealing Range Premium
        range_short_score = 0.0
        if range_zone in ['PREMIUM', 'OTE_BEARISH']:
            range_short_score = 15.0
        elif range_zone == 'EQUILIBRIUM':
            range_short_score = 7.5
        short_factors.append(ConfluenceFactor(
            name="Dealing Range Premium / OTE",
            weight=15.0,
            score=range_short_score,
            passed=range_short_score >= 12.0,
            description=f"Current price is in {range_zone} ({dealing_range.get('discount_depth_pct', 50):.1f}% of range). Favorable short risk profile."
        ))

        # 2.5 Buy-side liquidity sweep
        sweep_short_score = 0.0
        recent_buy_sweeps = [s for s in sweeps if s['sweep_type'] == 'BUY_SIDE']
        if recent_buy_sweeps:
            sweep_short_score = 15.0
        short_factors.append(ConfluenceFactor(
            name="Buy-Side Liquidity Sweep (Purge)",
            weight=15.0,
            score=sweep_short_score,
            passed=sweep_short_score > 0,
            description="Institutional purge of buy-side liquidity above recent highs detected." if sweep_short_score > 0 else "No recent Buy-Side Liquidity sweep."
        ))

        total_short_score = sum(f.score for f in short_factors)

        # -------------------------------------------------------------
        # 3. DECIDE DIRECTION, GRADE & TRADE LEVELS
        # -------------------------------------------------------------
        if total_long_score >= total_short_score and total_long_score >= self.min_score_moderate:
            bias = 'BULLISH'
            total_score = total_long_score
            chosen_factors = long_factors
            if total_score >= self.min_score_strong:
                signal = 'STRONG_LONG'
                quality = 'A+ (Institutional Setup)'
            else:
                signal = 'MODERATE_LONG'
                quality = 'A'
            levels = self._calculate_long_levels(current_price, nearest_bull_ob, dealing_range, bull_obs)
            verdict = f"High probability LONG setup with {total_score:.1f}% confluence. Risk:Reward ratio is {levels.risk_reward_ratio:.2f}:1."
        elif total_short_score > total_long_score and total_short_score >= self.min_score_moderate:
            bias = 'BEARISH'
            total_score = total_short_score
            chosen_factors = short_factors
            if total_score >= self.min_score_strong:
                signal = 'STRONG_SHORT'
                quality = 'A+ (Institutional Setup)'
            else:
                signal = 'MODERATE_SHORT'
                quality = 'A'
            levels = self._calculate_short_levels(current_price, nearest_bear_ob, dealing_range, bear_obs)
            verdict = f"High probability SHORT setup with {total_score:.1f}% confluence. Risk:Reward ratio is {levels.risk_reward_ratio:.2f}:1."
        else:
            bias = 'NEUTRAL'
            total_score = max(total_long_score, total_short_score)
            chosen_factors = long_factors if total_long_score >= total_short_score else short_factors
            signal = 'NEUTRAL'
            quality = 'C (No Trade / Wait Confirmation)'
            levels = None
            verdict = f"Market is currently balanced/consolidating. Confluence score ({total_score:.1f}%) is below actionable threshold ({self.min_score_moderate}%)."

        return SMCScoringResult(
            symbol=analysis.symbol,
            timeframe=analysis.timeframe,
            signal=signal,
            bias=bias,
            total_confluence_score=round(total_score, 1),
            quality_grade=quality,
            confluence_factors=[asdict(f) for f in chosen_factors],
            trade_levels=asdict(levels) if levels else None,
            execution_verdict=verdict
        )

    def _calculate_long_levels(
        self,
        current_price: float,
        ob: Optional[Dict[str, Any]],
        dealing_range: Dict[str, Any],
        all_bull_obs: List[Dict[str, Any]]
    ) -> TradeLevels:
        entry = current_price
        range_high = dealing_range.get('high', current_price * 1.05)
        range_low = dealing_range.get('low', current_price * 0.95)
        eq_50 = dealing_range.get('equilibrium_50', (range_high + range_low) / 2)

        # Stop loss placed below the active OB or lowest recent structure
        if ob:
            sl = float(ob['bottom']) * 0.995  # 0.5% safety buffer below OB
        elif all_bull_obs:
            sl = float(all_bull_obs[-1]['bottom']) * 0.995
        else:
            sl = float(range_low) * 0.995

        # Fallback if SL is too tight or upside down
        if sl >= entry or (entry - sl) / entry < 0.005:
            sl = entry * 0.985  # 1.5% fixed safety buffer

        risk = entry - sl

        tp1 = float(max(entry + (risk * 1.5), eq_50 if eq_50 > entry else entry + (risk * 2.0)))
        tp2 = float(max(range_high, entry + (risk * 3.0)))
        tp3 = float(range_high + (range_high - range_low) * 0.272)  # Fib extension -27.2%

        rr_tp1 = (tp1 - entry) / (risk + 1e-6)
        rr_tp2 = (tp2 - entry) / (risk + 1e-6)

        return TradeLevels(
            direction='LONG',
            entry_price=round(entry, 2),
            stop_loss=round(sl, 2),
            take_profit_1=round(tp1, 2),
            take_profit_2=round(tp2, 2),
            take_profit_3=round(tp3, 2),
            risk_per_share=round(risk, 2),
            risk_reward_ratio=round(rr_tp2, 2),
            risk_reward_tp1=round(rr_tp1, 2)
        )

    def _calculate_short_levels(
        self,
        current_price: float,
        ob: Optional[Dict[str, Any]],
        dealing_range: Dict[str, Any],
        all_bear_obs: List[Dict[str, Any]]
    ) -> TradeLevels:
        entry = current_price
        range_high = dealing_range.get('high', current_price * 1.05)
        range_low = dealing_range.get('low', current_price * 0.95)
        eq_50 = dealing_range.get('equilibrium_50', (range_high + range_low) / 2)

        # Stop loss placed above the active Bearish OB
        if ob:
            sl = float(ob['top']) * 1.005  # 0.5% buffer above OB
        elif all_bear_obs:
            sl = float(all_bear_obs[-1]['top']) * 1.005
        else:
            sl = float(range_high) * 1.005

        if sl <= entry or (sl - entry) / entry < 0.005:
            sl = entry * 1.015  # 1.5% fixed buffer

        risk = sl - entry

        tp1 = float(min(entry - (risk * 1.5), eq_50 if eq_50 < entry else entry - (risk * 2.0)))
        tp2 = float(min(range_low, entry - (risk * 3.0)))
        tp3 = float(range_low - (range_high - range_low) * 0.272)

        rr_tp1 = (entry - tp1) / (risk + 1e-6)
        rr_tp2 = (entry - tp2) / (risk + 1e-6)

        return TradeLevels(
            direction='SHORT',
            entry_price=round(entry, 2),
            stop_loss=round(sl, 2),
            take_profit_1=round(tp1, 2),
            take_profit_2=round(tp2, 2),
            take_profit_3=round(tp3, 2),
            risk_per_share=round(risk, 2),
            risk_reward_ratio=round(rr_tp2, 2),
            risk_reward_tp1=round(rr_tp1, 2)
        )
