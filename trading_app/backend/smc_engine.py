"""
Quantitative Smart Money Concepts (SMC) Engine.
Detects Swings, Market Structure (BOS / CHoCH), Order Blocks (OB),
Fair Value Gaps (FVG), Liquidity Sweeps, and Premium/Discount Dealing Ranges.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
import pandas as pd


@dataclass
class SwingPoint:
    index: int
    timestamp: str
    price: float
    point_type: str  # 'HIGH' or 'LOW'
    broken: bool = False
    broken_by_index: Optional[int] = None


@dataclass
class MarketStructureEvent:
    event_type: str  # 'BOS' or 'CHOCH'
    direction: str   # 'BULLISH' or 'BEARISH'
    index: int
    timestamp: str
    break_price: float
    broken_swing_price: float
    broken_swing_index: int
    description: str


@dataclass
class OrderBlock:
    ob_type: str  # 'BULLISH' or 'BEARISH'
    index: int
    timestamp: str
    top: float
    bottom: float
    open_price: float
    close_price: float
    volume: float
    mitigated: bool = False
    mitigated_at_index: Optional[int] = None
    strength: float = 1.0  # Normalized 0.0 - 1.0


@dataclass
class FairValueGap:
    fvg_type: str  # 'BULLISH' or 'BEARISH'
    index: int
    timestamp: str
    top: float
    bottom: float
    size: float
    size_pct: float
    mitigated: bool = False
    mitigated_at_index: Optional[int] = None
    mitigation_pct: float = 0.0


@dataclass
class LiquiditySweep:
    sweep_type: str  # 'BUY_SIDE' (Swept High) or 'SELL_SIDE' (Swept Low)
    index: int
    timestamp: str
    level_price: float
    wick_extreme: float
    closed_inside: float


@dataclass
class DealingRange:
    high: float
    low: float
    range_span: float
    equilibrium_50: float
    premium_zone_min: float
    discount_zone_max: float
    ote_618: float
    ote_786: float
    current_price: float
    current_zone: str  # 'PREMIUM', 'DISCOUNT', 'EQUILIBRIUM', 'OTE_BULLISH', 'OTE_BEARISH'
    discount_depth_pct: float


@dataclass
class SMCAnalysisResult:
    symbol: str
    timeframe: str
    current_price: float
    current_trend: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    swings: List[Dict[str, Any]]
    structure_events: List[Dict[str, Any]]
    active_bullish_obs: List[Dict[str, Any]]
    active_bearish_obs: List[Dict[str, Any]]
    active_bullish_fvgs: List[Dict[str, Any]]
    active_bearish_fvgs: List[Dict[str, Any]]
    liquidity_sweeps: List[Dict[str, Any]]
    dealing_range: Dict[str, Any]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SMCEngine:
    """
    Algorithmic Smart Money Concepts analyzer.
    Processes OHLCV DataFrames and extracts institutional market structures.
    """

    def __init__(self, swing_window: int = 4, fvg_min_pct: float = 0.05):
        self.swing_window = swing_window
        self.fvg_min_pct = fvg_min_pct

    def analyze(self, df: pd.DataFrame, symbol: str = "TSLA", timeframe: str = "15m") -> SMCAnalysisResult:
        if df.empty or len(df) < (self.swing_window * 2 + 5):
            raise ValueError(f"Insufficient data points ({len(df)}) for SMC analysis.")

        df = df.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            elif 'Datetime' in df.columns:
                df['Datetime'] = pd.to_datetime(df['Datetime'])
                df.set_index('Datetime', inplace=True)

        swings = self.detect_swings(df)
        structure_events, current_trend = self.detect_market_structure(df, swings)
        order_blocks = self.detect_order_blocks(df, structure_events)
        fvgs = self.detect_fair_value_gaps(df)
        sweeps = self.detect_liquidity_sweeps(df, swings)
        dealing_range = self.calculate_dealing_range(df, swings)

        # Filter active (non-mitigated or currently relevant) elements
        current_price = float(df['Close'].iloc[-1])

        active_bull_obs = [ob for ob in order_blocks if ob.ob_type == 'BULLISH' and not ob.mitigated and ob.top >= current_price * 0.70]
        active_bear_obs = [ob for ob in order_blocks if ob.ob_type == 'BEARISH' and not ob.mitigated and ob.bottom <= current_price * 1.30]

        active_bull_fvgs = [fvg for fvg in fvgs if fvg.fvg_type == 'BULLISH' and not fvg.mitigated]
        active_bear_fvgs = [fvg for fvg in fvgs if fvg.fvg_type == 'BEARISH' and not fvg.mitigated]

        summary = {
            "total_bos": sum(1 for e in structure_events if e.event_type == 'BOS'),
            "total_choch": sum(1 for e in structure_events if e.event_type == 'CHOCH'),
            "active_bullish_ob_count": len(active_bull_obs),
            "active_bearish_ob_count": len(active_bear_obs),
            "active_bullish_fvg_count": len(active_bull_fvgs),
            "active_bearish_fvg_count": len(active_bear_fvgs),
            "recent_sweeps_count": len(sweeps[-5:]) if sweeps else 0,
            "dealing_zone": dealing_range.current_zone,
            "last_close": current_price
        }

        return SMCAnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            current_trend=current_trend,
            swings=[asdict(s) for s in swings],
            structure_events=[asdict(e) for e in structure_events],
            active_bullish_obs=[asdict(ob) for ob in active_bull_obs[-6:]],
            active_bearish_obs=[asdict(ob) for ob in active_bear_obs[-6:]],
            active_bullish_fvgs=[asdict(f) for f in active_bull_fvgs[-6:]],
            active_bearish_fvgs=[asdict(f) for f in active_bear_fvgs[-6:]],
            liquidity_sweeps=[asdict(sw) for sw in sweeps[-8:]],
            dealing_range=asdict(dealing_range),
            summary=summary
        )

    def detect_swings(self, df: pd.DataFrame) -> List[SwingPoint]:
        swings: List[SwingPoint] = []
        n = len(df)
        w = self.swing_window

        highs = df['High'].values
        lows = df['Low'].values
        timestamps = [str(t) for t in df.index]

        for i in range(w, n - w):
            current_high = highs[i]
            is_swing_high = True
            for j in range(i - w, i + w + 1):
                if j != i and highs[j] >= current_high:
                    is_swing_high = False
                    break

            if is_swing_high:
                swings.append(SwingPoint(
                    index=i,
                    timestamp=timestamps[i],
                    price=float(current_high),
                    point_type='HIGH'
                ))

            current_low = lows[i]
            is_swing_low = True
            for j in range(i - w, i + w + 1):
                if j != i and lows[j] <= current_low:
                    is_swing_low = False
                    break

            if is_swing_low:
                swings.append(SwingPoint(
                    index=i,
                    timestamp=timestamps[i],
                    price=float(current_low),
                    point_type='LOW'
                ))

        # Sort chronologically by index
        swings.sort(key=lambda x: x.index)
        return swings

    def detect_market_structure(
        self, df: pd.DataFrame, swings: List[SwingPoint]
    ) -> Tuple[List[MarketStructureEvent], str]:
        events: List[MarketStructureEvent] = []
        if len(swings) < 2:
            return events, 'NEUTRAL'

        closes = df['Close'].values
        timestamps = [str(t) for t in df.index]
        current_trend = 'NEUTRAL'

        swing_highs: List[SwingPoint] = [s for s in swings if s.point_type == 'HIGH']
        swing_lows: List[SwingPoint] = [s for s in swings if s.point_type == 'LOW']

        active_swing_high: Optional[SwingPoint] = swing_highs[0] if swing_highs else None
        active_swing_low: Optional[SwingPoint] = swing_lows[0] if swing_lows else None

        for i in range(len(df)):
            close_price = closes[i]

            # Update active swings up to current index
            for sh in swing_highs:
                if sh.index <= i and not sh.broken:
                    active_swing_high = sh
            for sl in swing_lows:
                if sl.index <= i and not sl.broken:
                    active_swing_low = sl

            # Check Bullish Break (Breaking above active swing high)
            if active_swing_high and not active_swing_high.broken and i > active_swing_high.index:
                if close_price > active_swing_high.price:
                    active_swing_high.broken = True
                    active_swing_high.broken_by_index = i

                    # If previous trend was Bearish -> Change of Character (CHoCH), else BOS
                    if current_trend == 'BEARISH':
                        event_type = 'CHOCH'
                        desc = f"Bullish Change of Character: Price closed above last swing high ({active_swing_high.price:.2f})"
                    else:
                        event_type = 'BOS'
                        desc = f"Bullish Break of Structure: Continuation above swing high ({active_swing_high.price:.2f})"

                    current_trend = 'BULLISH'
                    events.append(MarketStructureEvent(
                        event_type=event_type,
                        direction='BULLISH',
                        index=i,
                        timestamp=timestamps[i],
                        break_price=float(close_price),
                        broken_swing_price=float(active_swing_high.price),
                        broken_swing_index=active_swing_high.index,
                        description=desc
                    ))

            # Check Bearish Break (Breaking below active swing low)
            if active_swing_low and not active_swing_low.broken and i > active_swing_low.index:
                if close_price < active_swing_low.price:
                    active_swing_low.broken = True
                    active_swing_low.broken_by_index = i

                    # If previous trend was Bullish -> Change of Character (CHoCH), else BOS
                    if current_trend == 'BULLISH':
                        event_type = 'CHOCH'
                        desc = f"Bearish Change of Character: Price closed below last swing low ({active_swing_low.price:.2f})"
                    else:
                        event_type = 'BOS'
                        desc = f"Bearish Break of Structure: Continuation below swing low ({active_swing_low.price:.2f})"

                    current_trend = 'BEARISH'
                    events.append(MarketStructureEvent(
                        event_type=event_type,
                        direction='BEARISH',
                        index=i,
                        timestamp=timestamps[i],
                        break_price=float(close_price),
                        broken_swing_price=float(active_swing_low.price),
                        broken_swing_index=active_swing_low.index,
                        description=desc
                    ))

        return events, current_trend

    def detect_order_blocks(
        self, df: pd.DataFrame, structure_events: List[MarketStructureEvent]
    ) -> List[OrderBlock]:
        order_blocks: List[OrderBlock] = []
        n = len(df)
        opens = df['Open'].values
        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values
        volumes = df['Volume'].values if 'Volume' in df.columns else np.ones(n)
        timestamps = [str(t) for t in df.index]

        avg_volume = float(np.mean(volumes)) if len(volumes) > 0 else 1.0

        for event in structure_events:
            break_idx = event.index
            origin_idx = event.broken_swing_index

            if event.direction == 'BULLISH':
                # Find the last bearish candle prior to the bullish expansion
                ob_candidate_idx = None
                for k in range(break_idx - 1, max(0, origin_idx - 5), -1):
                    if closes[k] < opens[k]:  # Bearish candle
                        ob_candidate_idx = k
                        break

                if ob_candidate_idx is not None:
                    top = float(max(opens[ob_candidate_idx], highs[ob_candidate_idx]))
                    bottom = float(lows[ob_candidate_idx])
                    vol = float(volumes[ob_candidate_idx])
                    vol_strength = min(1.0, vol / (avg_volume + 1e-6))

                    # Check mitigation by subsequent candles
                    mitigated = False
                    mitigated_idx = None
                    for m in range(ob_candidate_idx + 1, n):
                        if lows[m] <= top and closes[m] < bottom:
                            # Full invalidation or deep mitigation
                            mitigated = True
                            mitigated_idx = m
                            break
                        elif lows[m] <= top:
                            # Tapped into the order block zone
                            mitigated = True
                            mitigated_idx = m
                            break

                    order_blocks.append(OrderBlock(
                        ob_type='BULLISH',
                        index=ob_candidate_idx,
                        timestamp=timestamps[ob_candidate_idx],
                        top=top,
                        bottom=bottom,
                        open_price=float(opens[ob_candidate_idx]),
                        close_price=float(closes[ob_candidate_idx]),
                        volume=vol,
                        mitigated=mitigated,
                        mitigated_at_index=mitigated_idx,
                        strength=vol_strength
                    ))

            elif event.direction == 'BEARISH':
                # Find the last bullish candle prior to the bearish expansion
                ob_candidate_idx = None
                for k in range(break_idx - 1, max(0, origin_idx - 5), -1):
                    if closes[k] > opens[k]:  # Bullish candle
                        ob_candidate_idx = k
                        break

                if ob_candidate_idx is not None:
                    top = float(highs[ob_candidate_idx])
                    bottom = float(min(opens[ob_candidate_idx], lows[ob_candidate_idx]))
                    vol = float(volumes[ob_candidate_idx])
                    vol_strength = min(1.0, vol / (avg_volume + 1e-6))

                    mitigated = False
                    mitigated_idx = None
                    for m in range(ob_candidate_idx + 1, n):
                        if highs[m] >= bottom and closes[m] > top:
                            mitigated = True
                            mitigated_idx = m
                            break
                        elif highs[m] >= bottom:
                            mitigated = True
                            mitigated_idx = m
                            break

                    order_blocks.append(OrderBlock(
                        ob_type='BEARISH',
                        index=ob_candidate_idx,
                        timestamp=timestamps[ob_candidate_idx],
                        top=top,
                        bottom=bottom,
                        open_price=float(opens[ob_candidate_idx]),
                        close_price=float(closes[ob_candidate_idx]),
                        volume=vol,
                        mitigated=mitigated,
                        mitigated_at_index=mitigated_idx,
                        strength=vol_strength
                    ))

        # Deduplicate order blocks at identical index
        unique_obs: Dict[int, OrderBlock] = {}
        for ob in order_blocks:
            unique_obs[ob.index] = ob

        return sorted(list(unique_obs.values()), key=lambda x: x.index)

    def detect_fair_value_gaps(self, df: pd.DataFrame) -> List[FairValueGap]:
        fvgs: List[FairValueGap] = []
        n = len(df)
        if n < 3:
            return fvgs

        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values
        timestamps = [str(t) for t in df.index]

        for i in range(2, n):
            c_prev2_high = highs[i - 2]
            c_curr_low = lows[i]

            # Bullish FVG: Low of candle i > High of candle i-2
            if c_curr_low > c_prev2_high:
                gap_size = c_curr_low - c_prev2_high
                gap_pct = (gap_size / closes[i]) * 100

                if gap_pct >= self.fvg_min_pct:
                    # Check mitigation
                    mitigated = False
                    mitigated_idx = None
                    fill_pct = 0.0

                    for k in range(i + 1, n):
                        if lows[k] <= c_curr_low:
                            penetration = c_curr_low - lows[k]
                            fill_pct = min(100.0, (penetration / (gap_size + 1e-6)) * 100)
                            if fill_pct >= 50.0:
                                mitigated = True
                                mitigated_idx = k
                                break

                    fvgs.append(FairValueGap(
                        fvg_type='BULLISH',
                        index=i - 1,
                        timestamp=timestamps[i - 1],
                        top=float(c_curr_low),
                        bottom=float(c_prev2_high),
                        size=float(gap_size),
                        size_pct=float(gap_pct),
                        mitigated=mitigated,
                        mitigated_at_index=mitigated_idx,
                        mitigation_pct=float(fill_pct)
                    ))

            # Bearish FVG: High of candle i < Low of candle i-2
            c_prev2_low = lows[i - 2]
            c_curr_high = highs[i]

            if c_curr_high < c_prev2_low:
                gap_size = c_prev2_low - c_curr_high
                gap_pct = (gap_size / closes[i]) * 100

                if gap_pct >= self.fvg_min_pct:
                    mitigated = False
                    mitigated_idx = None
                    fill_pct = 0.0

                    for k in range(i + 1, n):
                        if highs[k] >= c_curr_high:
                            penetration = highs[k] - c_curr_high
                            fill_pct = min(100.0, (penetration / (gap_size + 1e-6)) * 100)
                            if fill_pct >= 50.0:
                                mitigated = True
                                mitigated_idx = k
                                break

                    fvgs.append(FairValueGap(
                        fvg_type='BEARISH',
                        index=i - 1,
                        timestamp=timestamps[i - 1],
                        top=float(c_prev2_low),
                        bottom=float(c_curr_high),
                        size=float(gap_size),
                        size_pct=float(gap_pct),
                        mitigated=mitigated,
                        mitigated_at_index=mitigated_idx,
                        mitigation_pct=float(fill_pct)
                    ))

        return fvgs

    def detect_liquidity_sweeps(self, df: pd.DataFrame, swings: List[SwingPoint]) -> List[LiquiditySweep]:
        sweeps: List[LiquiditySweep] = []
        n = len(df)
        highs = df['High'].values
        lows = df['Low'].values
        closes = df['Close'].values
        timestamps = [str(t) for t in df.index]

        for s in swings:
            # Look at bars after the swing point formation
            for i in range(s.index + self.swing_window + 1, n):
                if s.point_type == 'HIGH':
                    # Buy-Side Liquidity Sweep: High pierces swing high, but close finishes below it
                    if highs[i] > s.price and closes[i] <= s.price:
                        sweeps.append(LiquiditySweep(
                            sweep_type='BUY_SIDE',
                            index=i,
                            timestamp=timestamps[i],
                            level_price=float(s.price),
                            wick_extreme=float(highs[i]),
                            closed_inside=float(closes[i])
                        ))
                        break  # Count first valid sweep of this level
                elif s.point_type == 'LOW':
                    # Sell-Side Liquidity Sweep: Low pierces swing low, but close finishes above it
                    if lows[i] < s.price and closes[i] >= s.price:
                        sweeps.append(LiquiditySweep(
                            sweep_type='SELL_SIDE',
                            index=i,
                            timestamp=timestamps[i],
                            level_price=float(s.price),
                            wick_extreme=float(lows[i]),
                            closed_inside=float(closes[i])
                        ))
                        break

        return sweeps

    def calculate_dealing_range(self, df: pd.DataFrame, swings: List[SwingPoint]) -> DealingRange:
        current_price = float(df['Close'].iloc[-1])

        # Find most recent significant high and low
        swing_highs = [s for s in swings if s.point_type == 'HIGH']
        swing_lows = [s for s in swings if s.point_type == 'LOW']

        if swing_highs and swing_lows:
            recent_high = max(s.price for s in swing_highs[-3:])
            recent_low = min(s.price for s in swing_lows[-3:])
        else:
            recent_high = float(df['High'].max())
            recent_low = float(df['Low'].min())

        if recent_high <= recent_low:
            recent_high = recent_low + (current_price * 0.05)

        range_span = recent_high - recent_low
        equilibrium_50 = recent_low + (range_span * 0.50)
        ote_618 = recent_low + (range_span * 0.618)
        ote_786 = recent_low + (range_span * 0.786)

        # Discount depth calculation
        pos_pct = ((current_price - recent_low) / (range_span + 1e-6)) * 100.0

        if current_price < equilibrium_50:
            if ote_618 <= current_price <= ote_786:
                zone = 'OTE_BULLISH'
            else:
                zone = 'DISCOUNT'
        else:
            if ote_618 <= current_price <= ote_786:
                zone = 'OTE_BEARISH'
            else:
                zone = 'PREMIUM'

        return DealingRange(
            high=float(recent_high),
            low=float(recent_low),
            range_span=float(range_span),
            equilibrium_50=float(equilibrium_50),
            premium_zone_min=float(equilibrium_50),
            discount_zone_max=float(equilibrium_50),
            ote_618=float(ote_618),
            ote_786=float(ote_786),
            current_price=float(current_price),
            current_zone=zone,
            discount_depth_pct=float(pos_pct)
        )
