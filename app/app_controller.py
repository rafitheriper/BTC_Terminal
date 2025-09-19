# app/app_controller.py
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable # <--- CORRECT LINE

from .core.ai_engine import AIEngine
# ... rest of the imports

from .core.ai_engine import AIEngine
from .core.market_simulator import MarketSimulator
from .core.trade_manager import TradeManager
from .core.data_models import OperatingMode, MarketData, PredictionInfo
from .utils.api_key_manager import APIKeyManager
from .utils import config

logger = logging.getLogger(__name__)

class AppController:
    """
    Manages the application's core logic, acting as a bridge between the UI
    and the backend services (AI, market simulation, trade management).
    """

    def __init__(self):
        self.api_manager = APIKeyManager(config.API_CONFIG_FILE)
        self.ai_engine = AIEngine()
        self.trade_manager = TradeManager(config.TRADE_LOG_FILE)
        self.market_simulator = MarketSimulator(self._on_new_candle)

        self.operating_mode = OperatingMode.DATA_COLLECTION
        self.automation_active = threading.Event()
        self.automation_thread: Optional[threading.Thread] = None

        self.latest_market_data: Optional[MarketData] = None
        self.last_prediction: Optional[PredictionInfo] = None

        # Callbacks to update the UI
        self.ui_update_callback: Optional[Callable] = None
        self.ui_new_prediction_callback: Optional[Callable] = None
        self.ui_show_message_callback: Optional[Callable] = None

    def start_automation(self):
        """Starts the market simulation and AI processing loop."""
        if not self.automation_active.is_set():
            self.automation_active.set()
            self.automation_thread = threading.Thread(target=self._automation_loop, daemon=True)
            self.automation_thread.start()
            logger.info(f"Automation started in {self.operating_mode.value} mode.")

    def stop_automation(self):
        """Stops the automation loop."""
        if self.automation_active.is_set():
            self.automation_active.clear()
            if self.automation_thread:
                self.automation_thread.join(timeout=2)
            logger.info("Automation stopped.")

    def set_operating_mode(self, mode: OperatingMode):
        """Sets the current operating mode of the application."""
        self.operating_mode = mode
        if self.operating_mode in [OperatingMode.AI_PREDICTION, OperatingMode.PAPER_TRADING]:
            if not self.api_manager.is_configured():
                 if self.ui_show_message_callback:
                    self.ui_show_message_callback(
                        "API Key Not Found",
                        "The selected mode will use the internal Rules Engine. "
                        "Configure a Gemini API key for real AI predictions.",
                        "warning"
                    )
        logger.info(f"Operating mode changed to: {mode.value}")

    def _automation_loop(self):
        """The main loop that drives the market simulator."""
        self.market_simulator.run()
        while self.automation_active.is_set():
            time.sleep(1) # Keep thread alive while simulator runs in its own thread

    def _on_new_candle(self, market_data: MarketData):
        """Callback triggered by MarketSimulator on each new candle."""
        self.latest_market_data = market_data
        self.trade_manager.check_prediction_expiry(market_data)

        if self.operating_mode == OperatingMode.DATA_COLLECTION:
            self.trade_manager.log_market_data(market_data, config.MARKET_DATA_LOG_FILE)
        elif self.operating_mode in [OperatingMode.AI_PREDICTION, OperatingMode.PAPER_TRADING]:
            # Only trigger a new prediction if the last one is complete
            if self.trade_manager.is_trade_pending() is False:
                self._request_ai_prediction()

        if self.ui_update_callback:
            self.ui_update_callback()

    def _request_ai_prediction(self):
        """Requests a prediction from the AI engine and processes it."""
        if not self.latest_market_data:
            return

        is_paper_trade = self.operating_mode == OperatingMode.PAPER_TRADING

        prediction_info = self.ai_engine.get_prediction(
            market_data=self.latest_market_data,
            use_gemini=self.api_manager.is_configured(),
            is_paper_trade=is_paper_trade,
            paper_trading_config=self.trade_manager.get_paper_trading_config()
        )

        if prediction_info:
            self.trade_manager.register_new_prediction(prediction_info)
            if self.ui_new_prediction_callback:
                self.ui_new_prediction_callback(prediction_info)

    def get_app_state(self) -> dict:
        """Provides the current state of the application for the UI."""
        return {
            "market_data": self.latest_market_data,
            "trade_history": self.trade_manager.get_session_history(),
            "performance_summary": self.trade_manager.get_performance_summary(),
            "last_prediction": self.trade_manager.get_last_prediction(),
            "is_trade_pending": self.trade_manager.is_trade_pending(),
            "paper_trading_config": self.trade_manager.get_paper_trading_config(),
            "ai_source": self.ai_engine.get_current_ai_source()
        }

    def shutdown(self):
        """Gracefully shuts down the application."""
        self.stop_automation()
        self.trade_manager.save_session_history_to_log()
        logger.info("Application shutdown complete.")