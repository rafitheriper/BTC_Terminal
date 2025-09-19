# app/utils/config.py
from typing import Dict

# --- Application Settings ---
APP_VERSION = "1.0.0"
UI_UPDATE_RATE_MS = 100

# --- Trading Simulation ---
CANDLE_INTERVAL_SECONDS = 5
TRADE_EXPIRY_MINUTES = 1

# --- AI & API Settings ---
GEMINI_REQUEST_LIMIT = 60
GEMINI_COOLDOWN_SECONDS = 60

# --- File Paths ---
API_CONFIG_FILE = "api_config.json"
PAPER_TRADING_CONFIG_FILE = "paper_trading_config.json"
TRADE_LOG_FILE = "trade_log.csv"
MARKET_DATA_LOG_FILE = "market_data_log.csv"

# --- UI Styling ---
class Style:
    DARK_BG = "#2e2e2e"
    LIGHT_BG = "#3c3c3c"
    TEXT_COLOR = "#e0e0e0"
    ACCENT_COLOR = "#26a69a"
    PROFIT_COLOR = "#26a69a"
    LOSS_COLOR = "#ef5350"
    WARNING_COLOR = "#ffc107"
    INFO_COLOR = "#64b5f6"

    FONTS: Dict[str, tuple] = {
        "default": ("Segoe UI", 10),
        "bold": ("Segoe UI", 10, "bold"),
        "h1": ("Segoe UI", 48, "bold"),
        "h2": ("Segoe UI", 12, "bold"),
        "price": ("Segoe UI", 42, "bold"),
        "mono": ("Courier", 9)
    }