# app/core/trade_manager.py
import os
import json
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List #   added List

from .data_models import PredictionInfo, PredictionStatus, MarketData, PaperTradingConfig
# ... rest of the imports

from .data_models import PredictionInfo, PredictionStatus, MarketData, PaperTradingConfig
from ..utils import config

logger = logging.getLogger(__name__)

class TradeManager:
    """
    Manages trade history, paper trading logic, and performance metrics for the session.
    """
    def __init__(self, trade_log_file: str):
        self.trade_log_file = trade_log_file
        self.session_history: Dict[str, PredictionInfo] = {}
        self.paper_config = PaperTradingConfig()
        self._load_paper_trading_config()
        self._ensure_log_files_exist()

    def get_last_prediction(self) -> Optional[PredictionInfo]:
        """Returns the most recent prediction, if any."""
        if not self.session_history:
            return None
        return list(self.session_history.values())[-1]

    def is_trade_pending(self) -> bool:
        """Checks if there is an active, pending trade."""
        last_pred = self.get_last_prediction()
        return last_pred and last_pred.status == PredictionStatus.PENDING.value

    def register_new_prediction(self, prediction: PredictionInfo):
        """Adds a new prediction to the session history."""
        self.session_history[prediction.trade_id] = prediction
        logger.info(f"New trade registered: {prediction.trade_id} ({prediction.signal})")

    def check_prediction_expiry(self, current_market_data: MarketData):
        """Checks and resolves any pending predictions that have expired."""
        for trade_id, info in self.session_history.items():
            if info.status == PredictionStatus.PENDING.value and datetime.now() >= info.expiry_time:
                self._resolve_trade(info, current_market_data.price)

    def _resolve_trade(self, info: PredictionInfo, final_price: float):
        """Determines the outcome of a trade and calculates P&L."""
        result = PredictionStatus.NEUTRAL
        if info.signal == "BUY CALL":
            result = PredictionStatus.HIT if final_price > info.price_at_prediction else PredictionStatus.MISS
        elif info.signal == "BUY PUT":
            result = PredictionStatus.HIT if final_price < info.price_at_prediction else PredictionStatus.MISS
        
        info.status = result.value
        info.final_price = final_price

        if info.trade_amount is not None:
            pnl = 0.0
            payout_rate = self.paper_config.payout_percent / 100.0
            if result == PredictionStatus.HIT:
                pnl = info.trade_amount * payout_rate
            elif result == PredictionStatus.MISS:
                pnl = -info.trade_amount
            
            info.pnl = pnl
            new_balance = (info.capital_before_trade or self.paper_config.balance) + pnl
            info.capital_after_trade = new_balance
            self.paper_config.balance = new_balance
            logger.info(f"Trade resolved: {info.trade_id} | Status: {result.value} | P&L: ${pnl:.2f}")
        else:
             logger.info(f"Prediction resolved: {info.trade_id} | Status: {result.value}")

    def get_session_history(self) -> List[PredictionInfo]:
        """Returns the trade history for the current session."""
        return list(self.session_history.values())

    def get_performance_summary(self) -> Dict[str, any]:
        """Calculates and returns a summary of the session's performance."""
        wins, losses, net_pnl = 0, 0, 0.0
        for trade in self.session_history.values():
            if trade.status == PredictionStatus.HIT.value:
                wins += 1
            elif trade.status == PredictionStatus.MISS.value:
                losses += 1
            if trade.pnl is not None:
                net_pnl += trade.pnl
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        return {"wins": wins, "losses": losses, "win_rate": win_rate, "net_pnl": net_pnl}
    
    # ... (Paper config and file logging methods below) ...

    def get_paper_trading_config(self) -> PaperTradingConfig:
        return self.paper_config

    def update_paper_config(self, new_config: PaperTradingConfig):
        self.paper_config = new_config
        self._save_paper_trading_config()

    def _load_paper_trading_config(self):
        try:
            if os.path.exists(config.PAPER_TRADING_CONFIG_FILE):
                with open(config.PAPER_TRADING_CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.paper_config = PaperTradingConfig(**data)
                    logger.info("Paper trading config loaded.")
        except Exception as e:
            logger.error(f"Could not load paper trading config: {e}. Using defaults.")

    def _save_paper_trading_config(self):
        try:
            with open(config.PAPER_TRADING_CONFIG_FILE, 'w') as f:
                json.dump(self.paper_config.__dict__, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving paper trading config: {e}")
    
    def get_trade_log_columns(self):
        return [
            'trade_id', 'timestamp', 'signal', 'confidence', 'reasoning', 
            'price_at_prediction', 'expiry_time', 'status', 'final_price', 'AI_Source',
            'capital_before_trade', 'trade_amount', 'pnl', 'capital_after_trade'
        ]

    def log_market_data(self, data: MarketData, file_path: str):
        """Logs the latest market data to a CSV file."""
        log_entry = data.__dict__.copy()
        log_entry.pop('candle_history', None)
        log_entry['Timestamp'] = datetime.now().isoformat()
        try:
            pd.DataFrame([log_entry]).to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)
        except Exception as e:
            logger.error(f"Failed to log market data: {e}")

    def save_session_history_to_log(self):
        """Appends all trades from the current session to the master log file."""
        if not self.session_history:
            logger.info("No new trades in this session to append to log.")
            return
        
        try:
            write_header = not os.path.exists(self.trade_log_file) or os.path.getsize(self.trade_log_file) == 0
            session_trades_df = pd.DataFrame([info.__dict__ for info in self.session_history.values()])
            
            # Ensure columns are in the correct order
            session_trades_df = session_trades_df[self.get_trade_log_columns()]
            
            session_trades_df.to_csv(self.trade_log_file, mode='a', header=write_header, index=False)
            logger.info(f"Appended {len(session_trades_df)} session trades to {self.trade_log_file}.")
        except Exception as e:
            logger.error(f"Failed to append session trades to log: {e}")

    def _ensure_log_files_exist(self):
        """Creates empty log files with headers if they don't exist."""
        if not os.path.exists(self.trade_log_file):
            pd.DataFrame(columns=self.get_trade_log_columns()).to_csv(self.trade_log_file, index=False)
        if not os.path.exists(config.MARKET_DATA_LOG_FILE):
             pd.DataFrame(columns=[
                 'price', 'open', 'high', 'low', 'volume', 'rsi', 'adx', 
                 'macd', 'macd_signal', 'ma_short', 'ma_long', 'Timestamp'
             ]).to_csv(config.MARKET_DATA_LOG_FILE, index=False)