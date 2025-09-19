# app/utils/technical_indicators.py
import pandas as pd
import numpy as np
from typing import Tuple

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculates the Relative Strength Index (RSI)."""
    if len(prices) < period:
        return 50.0
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    if loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return 100 - (100 / (1 + rs))

def calculate_adx(df: pd.DataFrame, period: int = 14) -> float:
    """Calculates the Average Directional Index (ADX)."""
    if len(df) < period * 2:
        return 0.0
    h, l, c = df['High'], df['Low'], df['Close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1).ewm(alpha=1/period, adjust=False).mean()
    plus_dm = (h - h.shift()).where((h - h.shift()) > (l.shift() - l), 0).ewm(alpha=1/period, adjust=False).mean()
    minus_dm = (l.shift() - l).where((l.shift() - l) > (h - h.shift()), 0).ewm(alpha=1/period, adjust=False).mean()
    with np.errstate(divide='ignore', invalid='ignore'):
        plus_di, minus_di = 100 * (plus_dm / tr), 100 * (minus_dm / tr)
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di)).replace([np.inf, -np.inf], 0).fillna(0)
    return dx.ewm(alpha=1/period, adjust=False).mean().iloc[-1]

def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float]:
    """Calculates the Moving Average Convergence Divergence (MACD) and its signal line."""
    if len(prices) < slow:
        return 0.0, 0.0
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]