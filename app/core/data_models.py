# app/core/data_models.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

class PredictionStatus(Enum):
    PENDING = "PENDING"
    HIT = "HIT"
    MISS = "MISS"
    NEUTRAL = "NEUTRAL"

class OperatingMode(Enum):
    DATA_COLLECTION = "Data Collection"
    AI_PREDICTION = "AI Prediction"
    PAPER_TRADING = "Paper Trading"

@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    timestamp: datetime

@dataclass
class PredictionInfo:
    trade_id: str
    signal: str
    confidence: float
    reasoning: str
    price_at_prediction: float
    timestamp: datetime
    expiry_time: datetime
    status: str = PredictionStatus.PENDING.value
    final_price: Optional[float] = None
    AI_Source: Optional[str] = None
    capital_before_trade: Optional[float] = None
    trade_amount: Optional[float] = None
    pnl: Optional[float] = None
    capital_after_trade: Optional[float] = None

@dataclass
class MarketData:
    price: float
    open: float
    high: float
    low: float
    volume: float
    rsi: float
    adx: float
    macd: float
    macd_signal: float
    ma_short: float
    ma_long: float
    candle_history: List[Candle] = field(default_factory=list)

@dataclass
class PaperTradingConfig:
    balance: float = 10000.0
    risk_percent: float = 2.0
    payout_percent: float = 85.0