import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter import DoubleVar, TclError
import json
import time
import pandas as pd
import numpy as np
import threading
from datetime import datetime, timedelta
import os
import sys
from typing import Dict, Optional, Any, List
import logging
from dataclasses import dataclass, field
from enum import Enum
import math
import base64

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)
CANDLE_INTERVAL_SECONDS = 5 # Aggregate price ticks into 5-second candles

# --- Enums & Data Classes ---
class PredictionStatus(Enum):
    PENDING = "PENDING"
    HIT = "HIT"
    MISS = "MISS"
    NEUTRAL = "NEUTRAL"

class OperatingMode(Enum):
    DATA_COLLECTION = "Data Collection"
    AI_PREDICTION = "AI Prediction"
    PAPER_TRADING = "Paper Trading" # NEW MODE

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
    # Financial fields for Paper Trading mode
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

# --- API Key Manager ---
class APIKeyManager:
    def __init__(self):
        self.config_file = "api_config.json"
        self.api_key = None
        self.load_api_key()
    
    def save_api_key(self, key: str):
        try:
            encoded_key = base64.b64encode(key.encode()).decode()
            config = {"gemini_api_key": encoded_key}
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            self.api_key = key
            return True
        except Exception as e:
            logger.error(f"Error saving API key: {e}")
            return False
    
    def load_api_key(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                encoded_key = config.get("gemini_api_key", "")
                if encoded_key:
                    self.api_key = base64.b64decode(encoded_key).decode()
                    return True
        except Exception as e:
            logger.error(f"Error loading API key: {e}")
        return False
    
    def is_configured(self):
        return self.api_key is not None and len(self.api_key.strip()) > 0
    
    def clear_api_key(self):
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            self.api_key = None
            return True
        except Exception as e:
            logger.error(f"Error clearing API key: {e}")
            return False

# --- API Key Configuration Dialog ---
class APIKeyDialog(tk.Toplevel):
    def __init__(self, parent, api_manager):
        super().__init__(parent)
        self.parent = parent
        self.api_manager = api_manager
        self.result = None
        
        self.title("🔑 Gemini AI API Configuration")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_label = ttk.Label(main_frame, text="🤖 Gemini AI API Key Configuration", font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 20))
        instructions = """
To use real AI predictions, you need a Google Gemini AI API key.
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with your Google account & Click "Create API Key"
3. Copy the key and paste it below.
Your API key will be stored securely on your device."""
        inst_label = ttk.Label(main_frame, text=instructions.strip(), justify=tk.LEFT, wraplength=450)
        inst_label.pack(pady=(0, 20))
        
        ttk.Label(main_frame, text="API Key:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.api_key_var = tk.StringVar()
        self.is_existing_key = False
        if self.api_manager.is_configured():
            masked_key = f"{self.api_manager.api_key[:8]}{'*' * 32}"
            self.api_key_var.set(masked_key)
            self.is_existing_key = True
        
        self.api_entry = ttk.Entry(main_frame, textvariable=self.api_key_var, width=60, show="*", font=("Courier", 9))
        self.api_entry.pack(fill=tk.X, pady=(5, 10))
        self.api_entry.bind('<Return>', lambda event: self.save_and_close())
        self.api_entry.bind('<KeyRelease>', self.on_key_change)
        
        self.show_var = tk.BooleanVar()
        show_check = ttk.Checkbutton(main_frame, text="Show API Key", variable=self.show_var, command=self.toggle_show)
        show_check.pack(anchor=tk.W, pady=(0, 20))
        
        self.status_var = tk.StringVar(value="✅ API Key is configured" if self.api_manager.is_configured() else "❌ No API Key configured")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Segoe UI", 10))
        status_label.pack(pady=(0, 20))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        ttk.Button(button_frame, text="Clear Key", command=self.clear_key).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.on_cancel).pack(side=tk.RIGHT)
        self.save_button = ttk.Button(button_frame, text="Save & Close", command=self.save_and_close)
        self.save_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        if not self.api_manager.is_configured(): self.api_entry.focus()
            
    def on_key_change(self, event):
        current_text = self.api_key_var.get()
        if self.is_existing_key and '*' not in current_text:
            self.is_existing_key = False
    
    def toggle_show(self):
        self.api_entry.config(show="" if self.show_var.get() else "*")
        if self.show_var.get() and self.api_manager.is_configured() and "*" in self.api_key_var.get():
            self.api_key_var.set(self.api_manager.api_key)
    
    def clear_key(self):
        if messagebox.askyesno("Clear API Key", "Are you sure you want to clear the stored API key?"):
            if self.api_manager.clear_api_key():
                self.api_key_var.set("")
                self.status_var.set("❌ No API Key configured")
                messagebox.showinfo("Cleared", "API key has been cleared.")
            else:
                messagebox.showerror("Error", "Failed to clear API key.")
    
    def save_and_close(self):
        key = self.api_key_var.get().strip()
        if "*" in key and self.is_existing_key:
            self.destroy()
            return
        if not key:
            messagebox.showwarning("Empty Key", "Please enter an API key.")
            return
        
        if self.api_manager.save_api_key(key):
            self.status_var.set("✅ API Key saved successfully!")
            self.result = "saved"
            self.after(500, self.destroy)
        else:
            self.status_var.set("❌ Failed to save API key")
            messagebox.showerror("Error", "Failed to save API key. Please try again.")
    
    def on_cancel(self):
        self.result = "cancelled"
        self.destroy()

# --- Main Application ---
class ProAITradingTerminal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🚀 Pro AI Trading Terminal v16.0 (Multi-Mode)")
        self.geometry("1400x950")
        self.minsize(1200, 850)

        # Performance-related settings
        self.UI_UPDATE_RATE_MS = 100
        self.automation_active = threading.Event()

        self.api_manager = APIKeyManager()
        self.latest_market_data: Optional[MarketData] = None
        self.last_prediction_info: Optional[PredictionInfo] = None
        self.trade_history: Dict[str, PredictionInfo] = {}
        self.chart_indicators = [] 

        self.operating_mode = tk.StringVar(value=OperatingMode.DATA_COLLECTION.value)
        
        # --- NEW: Paper Trading State Variables ---
        self.paper_balance = DoubleVar(value=10000.0)
        self.paper_risk_percent = DoubleVar(value=2.0)
        self.paper_payout_percent = DoubleVar(value=85.0)
        self.paper_config_file = "paper_trading_config.json"

        self._configure_styles()
        self._create_widgets()
        
        # Load persistent data
        self._check_and_create_files()
        self._load_paper_trading_config() # Load paper trading settings
        self._load_trade_history()       # Load trade logs

        self.sim_price = 60000.0
        self.candle_history: List[Candle] = []
        self.current_candle_ticks = []
        self.last_candle_time = datetime.now()
        
        self.on_mode_change() # Set initial UI state based on mode
        self.update_clock()
        self.start_ui_updater()
        logger.info("Pro AI Trading Terminal Initialized.")

    def _configure_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        
        dark_bg = "#2e2e2e"
        light_bg = "#3c3c3c"
        text_color = "#e0e0e0"
        self.accent_color = "#26a69a"
        self.profit_color = "#26a69a"
        self.loss_color = "#ef5350"
        
        self.configure(background=dark_bg)
        self.style.configure("TLabel", background=dark_bg, foreground=text_color, font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8, background=self.accent_color, foreground="white")
        self.style.map("TButton", background=[('active', '#00766c')])
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=self.accent_color)
        self.style.configure("Card.TFrame", background=light_bg, relief="solid", borderwidth=1)
        self.style.configure("Price.TLabel", font=("Segoe UI", 42, "bold"), foreground="white")
        self.style.configure("TNotebook.Tab", background=light_bg, foreground=text_color, padding=[10, 5], font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", self.accent_color)], foreground=[("selected", "white")])
        self.style.configure("Treeview", rowheight=25, fieldbackground=light_bg, background=light_bg, foreground=text_color)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=dark_bg, foreground=text_color)
        self.style.configure("TRadiobutton", background=light_bg, foreground=text_color, font=("Segoe UI", 10))

    def _create_widgets(self):
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        left_pane = ttk.PanedWindow(main_pane, orient=tk.VERTICAL)
        right_frame = ttk.Frame(main_pane, style="Card.TFrame", padding=15)
        main_pane.add(left_pane, weight=2)
        main_pane.add(right_frame, weight=1)
        chart_frame = ttk.Frame(left_pane, style="Card.TFrame", padding=10)
        ai_frame = ttk.Frame(left_pane, style="Card.TFrame", padding=10)
        left_pane.add(chart_frame, weight=2)
        left_pane.add(ai_frame, weight=1)

        self._create_chart_panel(chart_frame)
        self._create_ai_panel(ai_frame)
        self._create_dashboard_panel(right_frame)
        self._create_status_bar()
        self._create_menu_bar()

    def _create_menu_bar(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="🔑 Configure Gemini AI API", command=self.show_api_config)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="❓ About", command=self.show_about)

    def show_api_config(self):
        dialog = APIKeyDialog(self, self.api_manager)
        self.wait_window(dialog)
        self.on_mode_change()

    def show_about(self):
        messagebox.showinfo("About", "Pro AI Trading Terminal v16.0 (Multi-Mode)\n\nModes:\n- Data Collection: Gathers market data.\n- AI Prediction: Shows raw AI signals.\n- Paper Trading: Simulates automated trading with a virtual balance.")

    def _create_chart_panel(self, parent):
        ttk.Label(parent, text="📈 Live Candlestick Chart (BTC/USDT)", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 10))
        self.chart_canvas = tk.Canvas(parent, background="#1e1e1e", highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True)
        self.chart_canvas.bind("<Configure>", lambda e: self._update_price_chart())

    def _create_ai_panel(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        signal_tab = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(signal_tab, text="🎯 AI Signal")
        self.prediction_label = ttk.Label(signal_tab, text="DATA MODE", font=("Segoe UI", 48, "bold"), anchor="center", background="#3c3c3c", foreground="white")
        self.prediction_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.confidence_label = ttk.Label(signal_tab, text="Confidence: --", font=("Segoe UI", 11, 'bold'))
        self.confidence_label.pack()
        self.countdown_label = ttk.Label(signal_tab, text="", font=("Segoe UI", 12, "bold"), foreground="#ffc107")
        self.countdown_label.pack(pady=10)

        coach_tab = ttk.Frame(notebook, style="Card.TFrame", padding=10)
        notebook.add(coach_tab, text="🧠 AI Coach")
        self.coach_tip_text = tk.Text(coach_tab, wrap=tk.WORD, height=4, font=("Segoe UI", 10), bg="#2e2e2e", foreground="#e0e0e0", relief="flat", state="disabled")
        self.coach_tip_text.pack(fill=tk.BOTH, expand=True)
        
        history_tab = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(history_tab, text="📜 Performance")
        cols = ("Time", "Signal", "Entry", "Result", "Status", "P&L ($)")
        self.history_tree = ttk.Treeview(history_tab, columns=cols, show='headings')
        for col in cols: self.history_tree.heading(col, text=col)
        self.history_tree.column("Time", width=120)
        self.history_tree.column("Signal", width=80, anchor=tk.CENTER)
        self.history_tree.column("Entry", width=90, anchor=tk.E)
        self.history_tree.column("Result", width=100, anchor=tk.E)
        self.history_tree.column("Status", width=80, anchor=tk.CENTER)
        self.history_tree.column("P&L ($)", width=80, anchor=tk.E)
        self.history_tree.pack(fill=tk.BOTH, expand=True)

    def _create_dashboard_panel(self, parent):
        ttk.Label(parent, text="📊 Market Dashboard", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))
        
        # --- Mode Selection Frame with 3 Modes ---
        mode_frame = ttk.LabelFrame(parent, text="Operating Mode", style="Card.TFrame", padding=10)
        mode_frame.pack(fill='x', pady=(0, 10))
        ttk.Radiobutton(mode_frame, text="Data Collection", variable=self.operating_mode, value=OperatingMode.DATA_COLLECTION.value, command=self.on_mode_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="AI Prediction", variable=self.operating_mode, value=OperatingMode.AI_PREDICTION.value, command=self.on_mode_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Paper Trading", variable=self.operating_mode, value=OperatingMode.PAPER_TRADING.value, command=self.on_mode_change).pack(side=tk.LEFT, padx=10)

        self.automation_button = ttk.Button(parent, text="▶️ Start Automation", command=self.toggle_automation)
        self.automation_button.pack(fill='x', ipady=5, pady=(5, 15))
        
        # --- NEW: Context-aware Paper Trading Panel ---
        self._create_paper_trading_panel(parent)
        
        self.price_label = ttk.Label(parent, text="$ --.--", style="Price.TLabel")
        self.price_label.pack()
        self.change_label = ttk.Label(parent, text="Change: --", font=("Segoe UI", 12))
        self.change_label.pack(pady=5)

        indicators_frame = ttk.Frame(parent, style="Card.TFrame")
        indicators_frame.pack(fill=tk.X, pady=15, expand=True)
        self.rsi_label, self.rsi_bar = self._create_indicator_row(indicators_frame, 0, "RSI (14):")
        self.adx_label, self.adx_bar = self._create_indicator_row(indicators_frame, 1, "ADX (14):")
        self.macd_label = self._create_dashboard_row(indicators_frame, 2, "MACD:")
        self.ma_short_label = self._create_dashboard_row(indicators_frame, 3, "MA (20):")
        self.ma_long_label = self._create_dashboard_row(indicators_frame, 4, "MA (100):")

    def _create_paper_trading_panel(self, parent):
        """Creates the panel for paper trading, initially hidden."""
        self.paper_trading_frame = ttk.LabelFrame(parent, text="💰 Paper Trading Controls", style="Card.TFrame", padding=10)
        
        # Row 0: Balance
        ttk.Label(self.paper_trading_frame, text="Paper Balance ($):", font=("Segoe UI", 10, 'bold')).grid(row=0, column=0, sticky='w', pady=3, padx=5)
        balance_entry = ttk.Entry(self.paper_trading_frame, textvariable=self.paper_balance)
        balance_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=3)
        balance_entry.bind("<KeyRelease>", self._on_paper_config_change)

        # Row 1: Risk
        ttk.Label(self.paper_trading_frame, text="Risk Per Trade (%):", font=("Segoe UI", 10, 'bold')).grid(row=1, column=0, sticky='w', pady=3, padx=5)
        risk_entry = ttk.Entry(self.paper_trading_frame, textvariable=self.paper_risk_percent)
        risk_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=3)
        risk_entry.bind("<KeyRelease>", self._on_paper_config_change)

        # Row 2: Payout
        ttk.Label(self.paper_trading_frame, text="Win Payout (%):", font=("Segoe UI", 10, 'bold')).grid(row=2, column=0, sticky='w', pady=3, padx=5)
        payout_entry = ttk.Entry(self.paper_trading_frame, textvariable=self.paper_payout_percent)
        payout_entry.grid(row=2, column=1, sticky='ew', padx=5, pady=3)
        payout_entry.bind("<KeyRelease>", self._on_paper_config_change)

        ttk.Separator(self.paper_trading_frame, orient=tk.HORIZONTAL).grid(row=3, columnspan=2, sticky='ew', pady=10)
        
        # Calculated values
        ttk.Label(self.paper_trading_frame, text="Risk Amount:").grid(row=4, column=0, sticky='w', padx=5)
        self.paper_risk_amount_label = ttk.Label(self.paper_trading_frame, text="$0.00", font=("Segoe UI", 10, "bold"), foreground=self.loss_color)
        self.paper_risk_amount_label.grid(row=4, column=1, sticky='e', padx=5)
        ttk.Label(self.paper_trading_frame, text="Potential Profit:").grid(row=5, column=0, sticky='w', padx=5)
        self.paper_profit_label = ttk.Label(self.paper_trading_frame, text="$0.00", font=("Segoe UI", 10, "bold"), foreground=self.profit_color)
        self.paper_profit_label.grid(row=5, column=1, sticky='e', padx=5)

        self.paper_trading_frame.columnconfigure(1, weight=1)

    def _on_paper_config_change(self, event=None):
        """Calculates and displays trade parameters in real-time from UI inputs."""
        try:
            balance = self.paper_balance.get()
            risk_percent = self.paper_risk_percent.get()
            
            risk_amount = balance * (risk_percent / 100.0)
            potential_profit = risk_amount * (self.paper_payout_percent.get() / 100.0)

            self.paper_risk_amount_label.config(text=f"${risk_amount:,.2f}")
            self.paper_profit_label.config(text=f"${potential_profit:,.2f}")
            
            # Persist the latest valid data
            self._save_paper_trading_config()

        except (ValueError, TclError):
            self.paper_risk_amount_label.config(text="$---.---")
            self.paper_profit_label.config(text="$---.---")
            return

    def _load_paper_trading_config(self):
        try:
            if os.path.exists(self.paper_config_file):
                with open(self.paper_config_file, 'r') as f:
                    config = json.load(f)
                    self.paper_balance.set(float(config.get("balance", 10000.0)))
                    self.paper_risk_percent.set(float(config.get("risk_percent", 2.0)))
                    self.paper_payout_percent.set(float(config.get("payout_percent", 85.0)))
                    logger.info("Paper trading config loaded.")
        except Exception as e:
            logger.error(f"Could not load paper trading config: {e}. Using defaults.")
        self._on_paper_config_change() # Update calculated labels

    def _save_paper_trading_config(self):
        try:
            config = {
                "balance": self.paper_balance.get(),
                "risk_percent": self.paper_risk_percent.get(),
                "payout_percent": self.paper_payout_percent.get()
            }
            with open(self.paper_config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving paper trading config: {e}")

    def _create_dashboard_row(self, parent, row, label_text):
        ttk.Label(parent, text=label_text, font=("Segoe UI", 10, 'bold')).grid(row=row, column=0, sticky='w', padx=5, pady=2)
        value_label = ttk.Label(parent, text="--", font=("Segoe UI", 10))
        value_label.grid(row=row, column=1, sticky='e', padx=5, pady=2)
        parent.columnconfigure(1, weight=1)
        return value_label

    def _create_indicator_row(self, parent, row, label_text):
        ttk.Label(parent, text=label_text, font=("Segoe UI", 10, 'bold')).grid(row=row, column=0, sticky='w', padx=5, pady=5)
        value_label = ttk.Label(parent, text="--", font=("Segoe UI", 10))
        value_label.grid(row=row, column=1, sticky='e', padx=5, pady=5)
        progress_bar = ttk.Progressbar(parent, orient="horizontal", length=100, mode="determinate")
        progress_bar.grid(row=row, column=2, sticky='e', padx=5, pady=5)
        return value_label, progress_bar

    def _create_status_bar(self):
        frame = ttk.Frame(self, style="Card.TFrame")
        frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(frame, textvariable=self.status_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.clock_label = ttk.Label(frame, text="", font=("Segoe UI", 10))
        self.clock_label.pack(side=tk.RIGHT, padx=5)

    def start_ui_updater(self):
        self.update_ui()
        self.after(self.UI_UPDATE_RATE_MS, self.start_ui_updater)

    def on_mode_change(self):
        """Handles UI and logic changes when the operating mode is switched."""
        self._clear_chart_indicators()
        mode = self.operating_mode.get()
        self.last_prediction_info = None # Reset prediction on mode switch

        # Hide paper trading panel by default
        self.paper_trading_frame.pack_forget()

        if mode == OperatingMode.DATA_COLLECTION.value:
            self.status_var.set("Switched to Data Collection mode.")
            self.prediction_label.config(text="DATA MODE")
            self.confidence_label.config(text="Confidence: --")
            self._update_coach_tip("Data Collection Mode: Market data is recorded without AI analysis.", "info")
        
        elif mode == OperatingMode.AI_PREDICTION.value:
            self.status_var.set("Switched to AI Prediction mode (no financial tracking).")
            self.prediction_label.config(text="STANDBY")
            self._update_coach_tip("AI Prediction Mode: Providing raw AI signals without financial simulation.", "info")
            if not self.api_manager.is_configured():
                messagebox.showwarning("API Key Required", "AI Prediction mode will run in Mock AI mode. Configure your Gemini API key for real predictions.")
        
        elif mode == OperatingMode.PAPER_TRADING.value:
            # Show the paper trading panel
            self.paper_trading_frame.pack(fill='x', pady=(0, 15), before=self.price_label)
            self.status_var.set("Switched to Paper Trading simulation mode.")
            self.prediction_label.config(text="STANDBY")
            self._update_coach_tip("Paper Trading Mode: AI will automatically execute trades against the virtual balance.", "info")
            if not self.api_manager.is_configured():
                messagebox.showwarning("API Key Required", "Paper Trading will run in Mock AI mode. Configure your Gemini API key for real predictions.")
        
        logger.info(f"Switched to {mode} mode.")


    def toggle_automation(self):
        if self.automation_active.is_set():
            self.automation_active.clear()
            self.automation_button.config(text="▶️ Start Automation")
        else:
            self.automation_active.set()
            threading.Thread(target=self.simulation_loop, daemon=True).start()
            mode_text = self.operating_mode.get()
            self.automation_button.config(text=f"⏹️ Stop {mode_text}")

    def simulation_loop(self):
        while self.automation_active.is_set():
            now = datetime.now()
            price_movement = math.sin(now.timestamp() / 10) * 25 + np.random.normal(0, 15)
            self.sim_price += price_movement
            self.current_candle_ticks.append(self.sim_price)

            if (now - self.last_candle_time).total_seconds() >= CANDLE_INTERVAL_SECONDS:
                if not self.current_candle_ticks: 
                    time.sleep(1)
                    continue

                open_price = self.current_candle_ticks[0]
                high_price = max(self.current_candle_ticks)
                low_price = min(self.current_candle_ticks)
                close_price = self.current_candle_ticks[-1]
                
                new_candle = Candle(open=open_price, high=high_price, low=low_price, close=close_price, timestamp=now)
                self.candle_history.append(new_candle)
                if len(self.candle_history) > 100: self.candle_history.pop(0)

                self.update_market_data()
                mode = self.operating_mode.get()

                if mode == OperatingMode.DATA_COLLECTION.value:
                    self.log_market_data()
                elif mode in [OperatingMode.AI_PREDICTION.value, OperatingMode.PAPER_TRADING.value]:
                     if not self.last_prediction_info or self.last_prediction_info.status != PredictionStatus.PENDING.value:
                        self.run_ai_prediction()

                self.current_candle_ticks = [close_price]
                self.last_candle_time = now

            time.sleep(1)
    
    def update_market_data(self):
        if len(self.candle_history) < 2: return

        df_close = pd.Series([c.close for c in self.candle_history])
        df_high = pd.Series([c.high for c in self.candle_history])
        df_low = pd.Series([c.low for c in self.candle_history])
        df = pd.DataFrame({'Close': df_close, 'High': df_high, 'Low': df_low})

        last_candle = self.candle_history[-1]
        self.latest_market_data = MarketData(
            price=last_candle.close, open=last_candle.open, high=last_candle.high, low=last_candle.low,
            volume=np.random.uniform(10, 200),
            rsi=self._calculate_rsi(df_close),
            adx=self._calculate_adx(df),
            macd=self._calculate_macd(df_close)[0], macd_signal=self._calculate_macd(df_close)[1],
            ma_short=df_close.rolling(20).mean().iloc[-1] if len(df_close) > 20 else 0,
            ma_long=df_close.rolling(100).mean().iloc[-1] if len(df_close) > 100 else 0,
            candle_history=self.candle_history
        )

    def run_ai_prediction(self):
        if not self.latest_market_data: return
        self._update_coach_tip("🤖 Analyzing market...", "info")
        threading.Thread(target=self._get_and_display_prediction, daemon=True).start()

    def _get_and_display_prediction(self):
        time.sleep(1)
        signal, reasoning = self._get_gemini_ai_prediction() if self.api_manager.is_configured() else self._get_mock_prediction()
        
        mock_response = {"signal": signal, "confidence": np.random.uniform(0.7, 0.95), "reasoning": reasoning}
        
        # --- Handle financial data ONLY for Paper Trading mode ---
        capital_before = None
        trade_amount = None
        if self.operating_mode.get() == OperatingMode.PAPER_TRADING.value:
            try:
                balance = self.paper_balance.get()
                risk_percent = self.paper_risk_percent.get()
                capital_before = balance
                trade_amount = balance * (risk_percent / 100.0)
            except (ValueError, TclError):
                logger.error("Invalid paper trading config, skipping trade.")
                return

        self.last_prediction_info = PredictionInfo(
            trade_id=datetime.now().isoformat(), signal=mock_response["signal"], confidence=mock_response["confidence"],
            reasoning=mock_response["reasoning"], price_at_prediction=self.latest_market_data.price,
            timestamp=datetime.now(), expiry_time=datetime.now() + timedelta(minutes=1),
            AI_Source="Gemini_AI" if self.api_manager.is_configured() else "Mock_AI",
            capital_before_trade=capital_before,
            trade_amount=trade_amount
        )
        
        self.trade_history[self.last_prediction_info.trade_id] = self.last_prediction_info
        self.after(0, self._display_prediction_result, mock_response)

    def _get_base_prediction(self, ai_name=""):
        data = self.latest_market_data
        if data.macd > data.macd_signal and data.rsi < 70 and data.price > data.ma_short > 0:
            signal = "BUY CALL"
            reasoning = f"{ai_name} Bullish confluence. MACD crossover, RSI at {data.rsi:.1f}, price above short-term MA."
        elif data.macd < data.macd_signal and data.rsi > 30 and data.price < data.ma_short > 0:
            signal = "BUY PUT"
            reasoning = f"{ai_name} Bearish confluence. MACD crossover, RSI at {data.rsi:.1f}, price below short-term MA."
        else:
            signal = "HOLD"
            reasoning = f"{ai_name} Mixed signals. RSI at {data.rsi:.1f}. Waiting for clearer market structure."
        return signal, reasoning

    def _get_gemini_ai_prediction(self):
        return self._get_base_prediction("Gemini AI Analysis:")

    def _get_mock_prediction(self):
        return self._get_base_prediction("Mock AI Analysis:")
    
    def update_ui(self):
        if self.automation_active.is_set():
            if self.operating_mode.get() in [OperatingMode.AI_PREDICTION.value, OperatingMode.PAPER_TRADING.value]:
                self._check_prediction_expiry()
            self.status_var.set(f"🟢 {self.operating_mode.get()} | Last Update: {datetime.now().strftime('%H:%M:%S')}")
        
        self._update_prediction_tracker()
        if self.latest_market_data:
            self._update_dashboard()
            self._update_price_chart()

    def _update_dashboard(self):
        data = self.latest_market_data
        price_color = self.profit_color if data.price >= data.open else self.loss_color
        self.price_label.config(text=f"${data.price:,.2f}", foreground=price_color)
        self.change_label.config(text=f"Change: ${data.price - data.open:+,.2f}", foreground=price_color)
        self.rsi_label.config(text=f"{data.rsi:.1f}"); self.rsi_bar['value'] = data.rsi
        self.adx_label.config(text=f"{data.adx:.1f}"); self.adx_bar['value'] = data.adx
        macd_status = "Bullish 🟢" if data.macd > data.macd_signal else "Bearish 🔴"
        self.macd_label.config(text=f"{macd_status} ({data.macd:.2f})")
        self.ma_short_label.config(text=f"${data.ma_short:,.2f}")
        self.ma_long_label.config(text=f"${data.ma_long:,.2f}")

    def _clear_chart_indicators(self):
        for indicator in self.chart_indicators: self.chart_canvas.delete(indicator)
        self.chart_indicators = []

    def _update_price_chart(self):
        self.chart_canvas.delete("all")
        self._clear_chart_indicators()

        candles = self.candle_history
        if not candles: return

        w, h = self.chart_canvas.winfo_width(), self.chart_canvas.winfo_height()
        if w < 10 or h < 10: return

        max_p = max(c.high for c in candles)
        min_p = min(c.low for c in candles)
        price_range = max_p - min_p if max_p > min_p else 1

        def p_to_y(price): return h - ((price - min_p) / price_range * (h - 40)) - 20

        num_grid_lines = 6
        price_step = price_range / num_grid_lines
        for i in range(num_grid_lines + 1):
            price = min_p + (i * price_step)
            y = p_to_y(price)
            self.chart_canvas.create_line(0, y, w, y, fill="#3c3c3c", width=1, dash=(2, 2))
            self.chart_canvas.create_text(w - 5, y, text=f"${price:,.2f}", fill="white", anchor="e")

        candle_width = w / (len(candles) + 2)
        body_width = candle_width * 0.8

        for i, candle in enumerate(candles):
            x = (i + 1) * candle_width
            y_open, y_close = p_to_y(candle.open), p_to_y(candle.close)
            y_high, y_low = p_to_y(candle.high), p_to_y(candle.low)
            color = self.profit_color if candle.close >= candle.open else self.loss_color
            self.chart_canvas.create_line(x, y_high, x, y_low, fill=color, width=1)
            self.chart_canvas.create_rectangle(x - body_width/2, y_close, x + body_width/2, y_open, fill=color, outline=color)
        
        if self.last_prediction_info and self.last_prediction_info.status == PredictionStatus.PENDING.value:
            self._draw_prediction_marker(self.last_prediction_info)

    def _draw_prediction_marker(self, info: PredictionInfo):
        if not self.candle_history: return
        w, h = self.chart_canvas.winfo_width(), self.chart_canvas.winfo_height()
        if w < 10 or h < 10: return
        max_p = max(c.high for c in self.candle_history); min_p = min(c.low for c in self.candle_history)
        price_range = max_p - min_p if max_p > min_p else 1
        def p_to_y(price): return h - ((price - min_p) / price_range * (h - 40)) - 20
        candle_width = w / (len(self.candle_history) + 2)
        x = (len(self.candle_history)) * candle_width
        y_pred = p_to_y(info.price_at_prediction)

        if info.signal == "BUY CALL":
            color, points, y_text = self.profit_color, [(x, y_pred + 8), (x, y_pred), (x + 8, y_pred)], y_pred + 15
        elif info.signal == "BUY PUT":
            color, points, y_text = self.loss_color, [(x, y_pred - 8), (x, y_pred), (x + 8, y_pred)], y_pred - 15
        else: return

        poly = self.chart_canvas.create_polygon(points, fill=color, outline=color, width=2)
        text = self.chart_canvas.create_text(x + 10, y_text, text=info.signal.split(" ")[1], fill=color, font=("Segoe UI", 8, "bold"), anchor="w")
        line = self.chart_canvas.create_line(x, y_pred, w, y_pred, fill=color, width=1, dash=(3, 3))
        self.chart_indicators.extend([poly, text, line])

    def _display_prediction_result(self, data):
        self.prediction_label.config(text=data['signal'].replace(" ", "\n"))
        self.confidence_label.config(text=f"Confidence: {data['confidence']:.0%}")
        
        tip = data['reasoning']
        if self.last_prediction_info.trade_amount is not None:
            payout = self.last_prediction_info.trade_amount * (self.paper_payout_percent.get() / 100.0)
            tip += f"\n\nPAPER TRADING: Risking ${self.last_prediction_info.trade_amount:,.2f} to win ${payout:,.2f}."
        
        self._update_coach_tip(tip, "info")
        self._update_trade_history_tree(self.last_prediction_info, is_new=True)
        self._update_price_chart()

    def _check_prediction_expiry(self):
        if not self.latest_market_data: return
        for trade_id in list(self.trade_history.keys()):
            info = self.trade_history.get(trade_id)
            if info and info.status == PredictionStatus.PENDING.value and datetime.now() >= info.expiry_time:
                price_now = self.latest_market_data.price
                result = PredictionStatus.NEUTRAL
                
                if info.signal == "BUY CALL": 
                    result = PredictionStatus.HIT if price_now > info.price_at_prediction else PredictionStatus.MISS
                elif info.signal == "BUY PUT": 
                    result = PredictionStatus.HIT if price_now < info.price_at_prediction else PredictionStatus.MISS
                
                info.status, info.final_price = result.value, price_now

                # --- Calculate P&L only if it was a paper trade ---
                if info.trade_amount is not None:
                    pnl = 0.0
                    if result == PredictionStatus.HIT:
                        pnl = info.trade_amount * (self.paper_payout_percent.get() / 100.0)
                    elif result == PredictionStatus.MISS:
                        pnl = -info.trade_amount
                    
                    info.pnl = pnl
                    new_balance = info.capital_before_trade + pnl
                    info.capital_after_trade = new_balance
                    
                    # Update the master balance in the UI
                    self.paper_balance.set(new_balance)
                    self.after(0, self._on_paper_config_change) # Recalculate display values

                self._update_trade_history_tree(info)

    def _update_trade_history_tree(self, info: PredictionInfo, is_new=False):
        change = info.final_price - info.price_at_prediction if info.final_price else 0
        result_text = f"${info.final_price:,.2f} ({change:+.2f})" if info.final_price else "--"
        pnl_text = f"{info.pnl:+.2f}" if info.pnl is not None else "--"
        pnl_color = "profit" if info.pnl and info.pnl > 0 else "loss" if info.pnl and info.pnl < 0 else "white"
        
        values = (info.timestamp.strftime('%H:%M:%S'), info.signal, f"${info.price_at_prediction:,.2f}", result_text, info.status, pnl_text)
        
        if is_new: 
            self.history_tree.insert("", 0, iid=info.trade_id, values=values, tags=(pnl_color,))
        else: 
            self.history_tree.item(info.trade_id, values=values, tags=(pnl_color,))
        
        self.history_tree.tag_configure("profit", foreground=self.profit_color)
        self.history_tree.tag_configure("loss", foreground=self.loss_color)
        self.history_tree.tag_configure("white", foreground="#e0e0e0")


    def _calculate_rsi(self, prices: pd.Series, period=14):
        if len(prices) < period: return 50.0
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        if loss.iloc[-1] == 0: return 100.0
        rs = gain.iloc[-1] / loss.iloc[-1]
        return 100 - (100 / (1 + rs))

    def _calculate_adx(self, df: pd.DataFrame, period=14):
        if len(df) < period * 2: return 0.0
        h, l, c = df['High'], df['Low'], df['Close']
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1).ewm(alpha=1/period, adjust=False).mean()
        plus_dm = (h - h.shift()).where((h - h.shift()) > (l.shift() - l), 0).ewm(alpha=1/period, adjust=False).mean()
        minus_dm = (l.shift() - l).where((l.shift() - l) > (h - h.shift()), 0).ewm(alpha=1/period, adjust=False).mean()
        with np.errstate(divide='ignore', invalid='ignore'):
            plus_di, minus_di = 100 * (plus_dm / tr), 100 * (minus_dm / tr)
            dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di)).replace([np.inf, -np.inf], 0).fillna(0)
        return dx.ewm(alpha=1/period, adjust=False).mean().iloc[-1]

    def _calculate_macd(self, prices: pd.Series, fast=12, slow=26, signal=9):
        if len(prices) < slow: return 0.0, 0.0
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        return macd.iloc[-1], macd.ewm(span=signal, adjust=False).mean().iloc[-1]

    def log_market_data(self):
        if not self.latest_market_data: return
        log_entry = self.latest_market_data.__dict__.copy()
        log_entry.pop('candle_history', None)
        log_entry['Timestamp'] = datetime.now().isoformat()
        file_path = 'market_data_log.csv'
        pd.DataFrame([log_entry]).to_csv(file_path, mode='a', header=not os.path.exists(file_path), index=False)

    def _load_trade_history(self):
        try:
            if not os.path.exists('trade_log.csv') or os.path.getsize('trade_log.csv') == 0:
                return
            log_df = pd.read_csv('trade_log.csv', header=0, dtype={'trade_id': str})
            log_df['timestamp'] = pd.to_datetime(log_df['timestamp'])
            log_df['expiry_time'] = pd.to_datetime(log_df['expiry_time'])
            log_df.drop_duplicates(subset='trade_id', keep='last', inplace=True)

            for _, row in log_df.iterrows():
                row_dict = row.to_dict()
                for key in ['final_price', 'capital_before_trade', 'trade_amount', 'pnl', 'capital_after_trade']:
                    if key in row_dict and pd.isna(row_dict[key]):
                        row_dict[key] = None
                
                valid_keys = PredictionInfo.__annotations__.keys()
                filtered_dict = {k: v for k, v in row_dict.items() if k in valid_keys}

                info = PredictionInfo(**filtered_dict)
                self.trade_history[info.trade_id] = info
                self._update_trade_history_tree(info, is_new=True)
            logger.info(f"Loaded {len(self.trade_history)} trades from history.")
        except Exception as e:
            logger.error(f"Error loading trade history: {e}")
            if os.path.exists('trade_log.csv'):
                os.rename('trade_log.csv', f'trade_log_corrupted_{datetime.now().strftime("%Y%m%d%H%M%S")}.csv')
            self._check_and_create_files()

    def _save_trade_history_on_exit(self):
        if not self.trade_history:
            logger.info("No trade history to save.")
            return
        try:
            history_list = [info.__dict__ for info in self.trade_history.values()]
            history_df = pd.DataFrame(history_list)
            history_df = history_df[self.get_trade_log_columns()]
            history_df.to_csv('trade_log.csv', index=False)
            logger.info(f"Trade history with {len(history_df)} trades successfully saved.")
        except Exception as e:
            logger.error(f"Failed to save trade history on exit: {e}")
            
    def get_trade_log_columns(self):
        return [
            'trade_id', 'timestamp', 'signal', 'confidence', 'reasoning', 
            'price_at_prediction', 'expiry_time', 'status', 'final_price', 
            'AI_Source', 'capital_before_trade', 'trade_amount', 'pnl', 
            'capital_after_trade'
        ]

    def _check_and_create_files(self):
        if not os.path.exists('trade_log.csv'):
            pd.DataFrame(columns=self.get_trade_log_columns()).to_csv('trade_log.csv', index=False)
        if not os.path.exists('market_data_log.csv'):
            pd.DataFrame(columns=['price', 'open', 'high', 'low', 'volume', 'rsi', 'adx', 'macd', 'macd_signal', 'ma_short', 'ma_long', 'Timestamp']).to_csv('market_data_log.csv', index=False)

    def _update_coach_tip(self, msg, mtype):
        self.coach_tip_text.config(state="normal")
        self.coach_tip_text.delete(1.0, tk.END)
        self.coach_tip_text.insert(1.0, msg)
        self.coach_tip_text.config(state="disabled")

    def _update_prediction_tracker(self):
        # Only show countdown in modes that make predictions
        if self.operating_mode.get() not in [OperatingMode.AI_PREDICTION.value, OperatingMode.PAPER_TRADING.value]:
            self.countdown_label.config(text="")
            return
            
        if self.last_prediction_info and self.last_prediction_info.status == PredictionStatus.PENDING.value:
            time_left = self.last_prediction_info.expiry_time - datetime.now()
            self.countdown_label.config(text=f"⏱️ Expires in {int(time_left.total_seconds())}s" if time_left.total_seconds() > 0 else "⏰ Evaluating...")
        else:
            self.countdown_label.config(text="")

    def update_clock(self):
        self.clock_label.config(text=f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        self.after(1000, self.update_clock)
        
    def on_closing(self):
        self.automation_active.clear()
        logger.info("Automation stopped. Saving configurations and trade history...")
        self._save_paper_trading_config()
        self._save_trade_history_on_exit()
        self.destroy()

if __name__ == "__main__":
    app = ProAITradingTerminal()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
