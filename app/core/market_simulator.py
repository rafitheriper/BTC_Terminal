# app/core/market_simulator.py
import threading
import time
import math
import numpy as np
import pandas as pd
import logging
from datetime import datetime
from typing import List, Callable, Optional 

from .data_models import Candle, MarketData
# ... rest of the imports

from .data_models import Candle, MarketData
from ..utils import config, technical_indicators as ta

logger = logging.getLogger(__name__)

class MarketSimulator:
    """
    Simulates live market data, generates candles, and calculates technical indicators.
    Runs in a dedicated thread and uses a callback to notify of new candles.
    """
    def __init__(self, on_new_candle_callback: Callable[[MarketData], None]):
        self.on_new_candle = on_new_candle_callback
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

        self.sim_price: float = 60000.0
        self.candle_history: List[Candle] = []
        self.current_candle_ticks: List[float] = []
        self.last_candle_time: datetime = datetime.now()

    def run(self):
        """Starts the market simulation in a new thread."""
        if self.thread and self.thread.is_alive():
            logger.warning("Market simulator is already running.")
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self.thread.start()
        logger.info("Market simulator started.")

    def stop(self):
        """Stops the market simulation thread."""
        self.stop_event.set()
        if self.thread:
            self.thread.join()
        logger.info("Market simulator stopped.")

    def _simulation_loop(self):
        """The main loop that generates price ticks and candles."""
        while not self.stop_event.is_set():
            now = datetime.now()
            # Generate a new price tick
            price_movement = math.sin(now.timestamp() / 10) * 25 + np.random.normal(0, 15)
            self.sim_price += price_movement
            self.current_candle_ticks.append(self.sim_price)

            # Check if a new candle should be formed
            if (now - self.last_candle_time).total_seconds() >= config.CANDLE_INTERVAL_SECONDS:
                self._form_new_candle(now)

            time.sleep(1)

    def _form_new_candle(self, now: datetime):
        """Creates a new candle from the collected ticks and triggers the callback."""
        if not self.current_candle_ticks:
            time.sleep(0.1)
            return

        open_price = self.current_candle_ticks[0]
        high_price = max(self.current_candle_ticks)
        low_price = min(self.current_candle_ticks)
        close_price = self.current_candle_ticks[-1]

        new_candle = Candle(
            open=open_price, high=high_price, low=low_price, close=close_price, timestamp=now
        )
        self.candle_history.append(new_candle)
        if len(self.candle_history) > 100:  # Keep history size manageable
            self.candle_history.pop(0)

        market_data = self._calculate_market_data(new_candle)
        if market_data:
            self.on_new_candle(market_data)

        self.current_candle_ticks = [close_price]
        self.last_candle_time = now

    def _calculate_market_data(self, last_candle: Candle) -> Optional[MarketData]:
        """Calculates all technical indicators based on the current candle history."""
        if len(self.candle_history) < 2:
            return None

        df_close = pd.Series([c.close for c in self.candle_history])
        df_high = pd.Series([c.high for c in self.candle_history])
        df_low = pd.Series([c.low for c in self.candle_history])
        df = pd.DataFrame({'Close': df_close, 'High': df_high, 'Low': df_low})

        macd_val, macd_signal_val = ta.calculate_macd(df_close)

        return MarketData(
            price=last_candle.close, open=last_candle.open, high=last_candle.high, low=last_candle.low,
            volume=np.random.uniform(10, 200),
            rsi=ta.calculate_rsi(df_close),
            adx=ta.calculate_adx(df),
            macd=macd_val, macd_signal=macd_signal_val,
            ma_short=df_close.rolling(20).mean().iloc[-1] if len(df_close) >= 20 else 0,
            ma_long=df_close.rolling(100).mean().iloc[-1] if len(df_close) >= 100 else 0,
            candle_history=self.candle_history.copy()
        )