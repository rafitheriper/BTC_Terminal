# app/core/ai_engine.py
import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional #, List

from .data_models import MarketData, PredictionInfo, PaperTradingConfig
# ... rest of the imports

from .data_models import MarketData, PredictionInfo, PaperTradingConfig
from ..utils import config

logger = logging.getLogger(__name__)

class AIEngine:
    """
    Handles all AI-related logic, including rule-based predictions
    and simulating calls to an external AI model like Gemini.
    """
    def __init__(self):
        self.gemini_request_count = 0
        self.gemini_limit_reached = False
        self.gemini_cooldown_end_time: Optional[datetime] = None
        self._current_ai_source = "Rules_Engine_v2"
        logger.info("AI Engine initialized.")

    def get_current_ai_source(self) -> str:
        """Returns the name of the AI source currently in use."""
        return self._current_ai_source

    def get_prediction(self, market_data: MarketData, use_gemini: bool, is_paper_trade: bool,
                       paper_trading_config: PaperTradingConfig) -> Optional[PredictionInfo]:
        """
        Main prediction method. Decides which AI to use and returns a complete
        PredictionInfo object if a trade signal is generated.
        """
        should_use_gemini = self._check_gemini_rate_limit(use_gemini)
        
        if should_use_gemini:
            signal, reasoning, confidence = self._get_gemini_prediction(market_data)
            self._current_ai_source = "Gemini_AI_Simulated"
        else:
            signal, reasoning, confidence = self._get_rules_based_prediction(market_data)
            self._current_ai_source = "Rules Engine (Fallback)" if self.gemini_limit_reached else "Rules_Engine_v2"

        if signal == "HOLD":
            return None # Do not generate a trade for HOLD signals

        # If it's a paper trade, calculate the trade details
        capital_before, trade_amount = None, None
        if is_paper_trade:
            capital_before = paper_trading_config.balance
            trade_amount = capital_before * (paper_trading_config.risk_percent / 100.0)

        return PredictionInfo(
            trade_id=datetime.now().isoformat(),
            signal=signal,
            confidence=confidence,
            reasoning=reasoning,
            price_at_prediction=market_data.price,
            timestamp=datetime.now(),
            expiry_time=datetime.now() + timedelta(minutes=config.TRADE_EXPIRY_MINUTES),
            AI_Source=self._current_ai_source,
            capital_before_trade=capital_before,
            trade_amount=trade_amount
        )

    def _check_gemini_rate_limit(self, use_gemini: bool) -> bool:
        """Manages the Gemini API rate limit simulation."""
        if not use_gemini:
            return False

        if self.gemini_limit_reached:
            if datetime.now() < self.gemini_cooldown_end_time:
                return False  # Cooldown active, fallback to rules
            else:
                self.gemini_limit_reached = False
                self.gemini_request_count = 0
                logger.info("Gemini API cooldown finished. Resuming with Gemini AI.")

        self.gemini_request_count += 1
        if self.gemini_request_count > config.GEMINI_REQUEST_LIMIT:
            logger.warning("Gemini API request limit simulated. Falling back to Rules Engine.")
            self.gemini_limit_reached = True
            self.gemini_cooldown_end_time = datetime.now() + timedelta(seconds=config.GEMINI_COOLDOWN_SECONDS)
            return False
        
        return True

    def _get_rules_based_prediction(self, data: MarketData) -> Tuple[str, str, float]:
        """A more sophisticated rules-based engine using a scoring system."""
        bullish_score, bearish_score = 0.0, 0.0
        reasons = []

        # 1. MACD Analysis
        if data.macd > data.macd_signal:
            bullish_score += 1.5; reasons.append("Bullish MACD crossover.")
        elif data.macd < data.macd_signal:
            bearish_score += 1.5; reasons.append("Bearish MACD crossover.")

        # 2. RSI Analysis
        if data.rsi < 30:
            bullish_score += 1; reasons.append(f"RSI is oversold ({data.rsi:.1f}).")
        elif data.rsi > 70:
            bearish_score += 1; reasons.append(f"RSI is overbought ({data.rsi:.1f}).")

        # 3. Moving Average Analysis
        if data.ma_short > 0 and data.price > data.ma_short:
            bullish_score += 1; reasons.append("Price is above the short-term MA.")
        elif data.ma_short > 0 and data.price < data.ma_short:
            bearish_score += 1; reasons.append("Price is below the short-term MA.")
        
        # 4. ADX Trend Strength Analysis
        if data.adx > 25:
            bullish_score *= 1.2; bearish_score *= 1.2
            reasons.append(f"Market is trending strongly (ADX: {data.adx:.1f}).")

        # Determine final signal
        if bullish_score > bearish_score and bullish_score >= 2.0:
            signal = "BUY CALL"
        elif bearish_score > bullish_score and bearish_score >= 2.0:
            signal = "BUY PUT"
        else:
            signal = "HOLD"
        
        total_score = max(bullish_score, bearish_score)
        confidence = min(0.5 + (total_score / 8.0), 0.95) if signal != "HOLD" else 0.5
        
        final_reasoning = f"Decision: {signal}. " + " ".join(reasons)
        if signal == "HOLD":
            final_reasoning = "Decision: HOLD. Signals are mixed or weak. " + " ".join(reasons)
            
        return signal, final_reasoning, confidence

    def _get_gemini_prediction(self, data: MarketData) -> Tuple[str, str, float]:
        """
        Simulates creating a prompt for and receiving a response from Gemini.
        In a real application, this would contain the actual API call logic.
        """
        candle_history_str = "\n".join([f" - T-{len(data.candle_history)-i}: O={c.open:.2f} H={c.high:.2f} L={c.low:.2f} C={c.close:.2f}" for i, c in enumerate(data.candle_history[-10:])])
        prompt = f"""
You are a world-class financial analyst specializing in short-term binary options trading on the BTC/USDT pair.
Your task is to analyze the provided market data and determine whether to issue a 'BUY CALL' (price will go up), 'BUY PUT' (price will go down), or 'HOLD' (unclear signal) for the next {config.TRADE_EXPIRY_MINUTES} minute(s).

Analyze the following data points:
- Current Price: {data.price:.2f}
- Technical Indicators:
  - RSI (14): {data.rsi:.2f}
  - ADX (14): {data.adx:.2f}
  - MACD Line: {data.macd:.4f}, MACD Signal: {data.macd_signal:.4f}
  - MA (Short, 20): {data.ma_short:.2f}
  - MA (Long, 100): {data.ma_long:.2f}
- Last 10 Candles (O, H, L, C):
{candle_history_str}

Provide your response in a strict JSON format with "signal", "confidence", and "reasoning".
"""
        logger.info(f"Simulating Gemini API call with prompt length: {len(prompt)}")
        
        # For this simulation, we'll use the rules engine to generate a realistic response.
        signal, _, confidence = self._get_rules_based_prediction(data)
        
        # Then, we'll generate a more "LLM-like" reasoning.
        if signal == "BUY CALL":
            reasoning = f"A bullish confluence is detected. The MACD crossover suggests upward momentum, supported by the price maintaining its position above key moving averages. With an ADX of {data.adx:.1f}, any trend has strength behind it."
        elif signal == "BUY PUT":
            reasoning = f"A bearish outlook is warranted. The MACD has crossed below its signal line, a classic bearish indicator. This is compounded by the price trading below its short-term MA."
        else:
            reasoning = f"A neutral stance is advised. Conflicting signals and a weak ADX of {data.adx:.1f} indicate a lack of a discernible trend. It's prudent to wait for a clearer market structure."

        return signal, reasoning, confidence