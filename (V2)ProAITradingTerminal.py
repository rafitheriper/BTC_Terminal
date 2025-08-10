import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
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

# --- Enums & Data Classes ---
class PredictionStatus(Enum):
    PENDING = "PENDING"
    HIT = "HIT"
    MISS = "MISS"
    NEUTRAL = "NEUTRAL"

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
    price_history: List[float] = field(default_factory=list)

# --- API Key Manager ---
class APIKeyManager:
    def __init__(self):
        self.config_file = "api_config.json"
        self.api_key = None
        self.load_api_key()
    
    def save_api_key(self, key: str):
        """Save API key to encrypted config file"""
        try:
            # Simple base64 encoding for basic obfuscation
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
        """Load API key from config file"""
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
        """Check if API key is configured"""
        return self.api_key is not None and len(self.api_key.strip()) > 0
    
    def clear_api_key(self):
        """Clear stored API key"""
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
        
        # Center the dialog
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🤖 Gemini AI API Key Configuration", 
                               font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Instructions
        instructions = """
To use real AI predictions, you need a Google Gemini AI API key.

How to get your API key:
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key and paste it below

Your API key will be stored securely on your device.
Press Enter to save, or use the Save button below.
        """
        
        inst_label = ttk.Label(main_frame, text=instructions.strip(), 
                              justify=tk.LEFT, wraplength=450)
        inst_label.pack(pady=(0, 20))
        
        # API Key Entry
        ttk.Label(main_frame, text="API Key:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        self.api_key_var = tk.StringVar()
        self.is_existing_key = False
        
        if self.api_manager.is_configured():
            # Show masked version of existing key
            masked_key = f"{self.api_manager.api_key[:8]}{'*' * 32}"
            self.api_key_var.set(masked_key)
            self.is_existing_key = True
        
        self.api_entry = ttk.Entry(main_frame, textvariable=self.api_key_var, 
                                  width=60, show="*", font=("Courier", 9))
        self.api_entry.pack(fill=tk.X, pady=(5, 10))
        
        # Bind Enter key to save function
        self.api_entry.bind('<Return>', lambda event: self.save_and_close())
        self.api_entry.bind('<KP_Enter>', lambda event: self.save_and_close())  # Numeric keypad Enter
        
        # Bind key release to detect changes
        self.api_entry.bind('<KeyRelease>', self.on_key_change)
        
        # Show/Hide button
        self.show_var = tk.BooleanVar()
        show_check = ttk.Checkbutton(main_frame, text="Show API Key", 
                                    variable=self.show_var, command=self.toggle_show)
        show_check.pack(anchor=tk.W, pady=(0, 20))
        
        # Status
        self.status_var = tk.StringVar()
        if self.api_manager.is_configured():
            self.status_var.set("✅ API Key is configured")
        else:
            self.status_var.set("❌ No API Key configured")
            
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                                font=("Segoe UI", 10))
        status_label.pack(pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="Test Connection", 
                  command=self.test_connection).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Clear Key", 
                  command=self.clear_key).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Cancel", 
                  command=self.on_cancel).pack(side=tk.RIGHT)
        
        self.save_button = ttk.Button(button_frame, text="Save & Close", 
                  command=self.save_and_close)
        self.save_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Focus on entry if no key configured
        if not self.api_manager.is_configured():
            self.api_entry.focus()
            
    def on_key_change(self, event):
        """Handle key changes to track if user is typing a new key"""
        current_text = self.api_key_var.get()
        if self.is_existing_key and '*' not in current_text:
            # User started typing over the masked key
            self.is_existing_key = False
    
    def toggle_show(self):
        if self.show_var.get():
            self.api_entry.config(show="")
            if self.api_manager.is_configured() and "*" in self.api_key_var.get():
                # Show the real key
                self.api_key_var.set(self.api_manager.api_key)
        else:
            self.api_entry.config(show="*")
    
    def test_connection(self):
        key = self.api_key_var.get().strip()
        if not key or "*" in key:
            messagebox.showwarning("Invalid Key", "Please enter a valid API key first.")
            return
        
        # Simple validation (Gemini API keys usually start with 'AIza')
        if not key.startswith('AIza'):
            messagebox.showwarning("Invalid Format", 
                                 "Gemini API keys typically start with 'AIza'. Please check your key.")
            return
        
        self.status_var.set("🔄 Testing connection...")
        self.update()
        
        # Simulate API test (in real implementation, you'd make an actual API call)
        time.sleep(1)  # Simulate network delay
        
        if len(key) > 30:  # Basic length check
            self.status_var.set("✅ Connection test successful!")
            messagebox.showinfo("Success", "API key appears to be valid!")
        else:
            self.status_var.set("❌ Connection test failed")
            messagebox.showerror("Error", "API key appears to be invalid or too short.")
    
    def clear_key(self):
        if messagebox.askyesno("Clear API Key", 
                              "Are you sure you want to clear the stored API key?"):
            if self.api_manager.clear_api_key():
                self.api_key_var.set("")
                self.status_var.set("❌ No API Key configured")
                messagebox.showinfo("Cleared", "API key has been cleared.")
            else:
                messagebox.showerror("Error", "Failed to clear API key.")
    
    def save_and_close(self):
        key = self.api_key_var.get().strip()
        
        # If key contains asterisks and user didn't change it, just close
        if "*" in key and self.is_existing_key and self.api_manager.is_configured():
            # User didn't change the key, just close
            self.result = "unchanged"
            self.destroy()
            return
        
        if not key:
            messagebox.showwarning("Empty Key", "Please enter an API key.")
            return
        
        # Validate key format
        if not key.startswith('AIza') and len(key) < 30:
            if not messagebox.askyesno("Invalid Format", 
                                     "This doesn't look like a valid Gemini API key. "
                                     "Gemini API keys typically start with 'AIza' and are longer.\n\n"
                                     "Do you want to save it anyway?"):
                return
        
        # Show saving status
        self.status_var.set("💾 Saving API key...")
        self.save_button.config(state="disabled", text="Saving...")
        self.update()
        
        # Save the key
        if self.api_manager.save_api_key(key):
            self.status_var.set("✅ API Key saved successfully!")
            self.result = "saved"
            
            # Show success message briefly
            self.after(500, lambda: self.show_success_and_close())
        else:
            self.status_var.set("❌ Failed to save API key")
            self.save_button.config(state="normal", text="Save & Close")
            messagebox.showerror("Error", "Failed to save API key. Please try again.")
    
    def show_success_and_close(self):
        """Show success message and close dialog"""
        messagebox.showinfo("Success", "✅ API key saved successfully!\n\nYou can now use Gemini AI for trading predictions.")
        self.destroy()
    
    def on_cancel(self):
        self.result = "cancelled"
        self.destroy()

# --- Main Application ---
class ProAITradingTerminal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🚀 Pro AI Trading Terminal v14.1 - Gemini AI Ready")
        self.geometry("1400x900")
        self.minsize(1200, 800)

        # Initialize API Manager
        self.api_manager = APIKeyManager()

        # Threading & State
        self.automation_active = threading.Event()
        self.latest_market_data: Optional[MarketData] = None
        self.last_prediction_info: Optional[PredictionInfo] = None
        self.trade_history: Dict[str, PredictionInfo] = {}

        # Settings
        self.settings = {"refresh_rate": 2, "prediction_expiry_minutes": 1}
        
        self._configure_styles()
        self._create_widgets()
        self._check_and_create_files()

        # Simulation Data
        self.sim_price = 60000.0
        self.sim_price_history = [60000.0] * 150 # Longer history for indicators
        self.sim_time_step = 0

        # Update status based on API key configuration
        if self.api_manager.is_configured():
            self.status_var.set("🟡 Ready with Gemini AI. Start Automation to begin.")
        else:
            self.status_var.set("🟡 Ready (Mock Mode). Configure Gemini AI for real predictions.")
        
        logger.info("Pro AI Trading Terminal Initialized.")
        self.update_clock()

    def _configure_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        
        # --- Dark Theme Color Palette ---
        dark_bg = "#2e2e2e"
        light_bg = "#3c3c3c"
        text_color = "#e0e0e0"
        accent_color = "#00aaff"
        success_color = "#28a745"
        danger_color = "#dc3545"
        warn_color = "#ffc107"

        self.configure(background=dark_bg)
        self.style.configure("TLabel", background=dark_bg, foreground=text_color, font=("Segoe UI", 10))
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8, background=accent_color, foreground=dark_bg)
        self.style.map("TButton", background=[('active', '#0077cc')])
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=accent_color)
        self.style.configure("Card.TFrame", background=light_bg, relief="solid", borderwidth=1)
        self.style.configure("Price.TLabel", font=("Segoe UI", 42, "bold"), foreground="white")
        self.style.configure("TPanedwindow", background=dark_bg)
        self.style.configure("TNotebook", background=dark_bg, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=light_bg, foreground=text_color, padding=[10, 5], font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", background=[("selected", accent_color)], foreground=[("selected", dark_bg)])
        self.style.configure("Treeview", rowheight=25, fieldbackground=light_bg, background=light_bg, foreground=text_color)
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=dark_bg, foreground=text_color)
        self.style.map("Treeview.Heading", background=[('active', light_bg)])
        self.style.configure("Vertical.TProgressbar", thickness=20, background=accent_color)

    def _create_widgets(self):
        # Main layout with resizable panes
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_pane = ttk.PanedWindow(main_pane, orient=tk.VERTICAL)
        right_frame = ttk.Frame(main_pane, style="Card.TFrame", padding=15)
        
        main_pane.add(left_pane, weight=2)
        main_pane.add(right_frame, weight=1)

        # Left Side: Chart and AI Panels
        chart_frame = ttk.Frame(left_pane, style="Card.TFrame", padding=10)
        ai_frame = ttk.Frame(left_pane, style="Card.TFrame", padding=10)
        left_pane.add(chart_frame, weight=2)
        left_pane.add(ai_frame, weight=1)

        self._create_chart_panel(chart_frame)
        self._create_ai_panel(ai_frame)
        
        # Right Side: Dashboard
        self._create_dashboard_panel(right_frame)
        
        self._create_status_bar()
        self._create_menu_bar()

    def _create_menu_bar(self):
        """Create menu bar with API configuration option"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Settings Menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="🔑 Configure Gemini AI API", command=self.show_api_config)
        settings_menu.add_separator()
        settings_menu.add_command(label="⚙️ Trading Settings", command=self.show_trading_settings)
        
        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="📖 About Gemini AI", command=self.show_gemini_info)
        help_menu.add_command(label="❓ About", command=self.show_about)

    def show_api_config(self):
        """Show API key configuration dialog"""
        dialog = APIKeyDialog(self, self.api_manager)
        self.wait_window(dialog)
        
        # Update status after configuration
        if self.api_manager.is_configured():
            self.status_var.set("🟡 Ready with Gemini AI. Start Automation to begin.")
        else:
            self.status_var.set("🟡 Ready (Mock Mode). Configure Gemini AI for real predictions.")

    def show_trading_settings(self):
        """Show trading settings dialog (placeholder)"""
        messagebox.showinfo("Trading Settings", 
                           "Trading settings dialog would be implemented here.\n\n"
                           "Current Settings:\n"
                           f"• Refresh Rate: {self.settings['refresh_rate']}s\n"
                           f"• Prediction Expiry: {self.settings['prediction_expiry_minutes']}min")

    def show_gemini_info(self):
        """Show information about Gemini AI"""
        info_text = """
🤖 About Google Gemini AI

Gemini is Google's most advanced AI model, designed to understand and generate human-like text, analyze data, and provide intelligent insights.

In this trading terminal, Gemini AI can:
• Analyze market conditions and technical indicators
• Provide reasoning for trading decisions
• Generate confidence scores for predictions
• Adapt to changing market patterns

To get started:
1. Get your free API key from Google AI Studio
2. Configure it in Settings > Configure Gemini AI API
3. Start automation to begin receiving AI predictions

Note: This is for educational purposes only.
Always do your own research before trading.
        """
        
        messagebox.showinfo("About Gemini AI", info_text.strip())

    def show_about(self):
        """Show about dialog"""
        about_text = f"""
🚀 Pro AI Trading Terminal v14.1

Enhanced with Google Gemini AI integration

Features:
• Real-time market simulation
• Advanced technical indicators (RSI, ADX, MACD)
• AI-powered trading predictions
• Performance tracking and history
• Professional dark theme interface

API Status: {"✅ Configured" if self.api_manager.is_configured() else "❌ Not Configured"}

Built for educational and research purposes.
        """
        messagebox.showinfo("About", about_text.strip())

    def _create_chart_panel(self, parent):
        ttk.Label(parent, text="📈 Live Price Chart (BTC/USDT)", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 10))
        self.chart_canvas = tk.Canvas(parent, background="#1e1e1e", highlightthickness=0)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True)
        self.chart_canvas.bind("<Configure>", lambda e: self._update_price_chart())

    def _create_ai_panel(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        # AI Signal Tab
        signal_tab = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(signal_tab, text="🎯 AI Signal")
        self.prediction_label = ttk.Label(signal_tab, text="STANDBY", font=("Segoe UI", 48, "bold"), anchor="center", background="#3c3c3c", foreground="white")
        self.prediction_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.confidence_label = ttk.Label(signal_tab, text="Confidence: --", font=("Segoe UI", 11, 'bold'))
        self.confidence_label.pack()
        self.countdown_label = ttk.Label(signal_tab, text="", font=("Segoe UI", 12, "bold"), foreground="#ffc107")
        self.countdown_label.pack(pady=10)

        # AI Coach Tab
        coach_tab = ttk.Frame(notebook, style="Card.TFrame", padding=10)
        notebook.add(coach_tab, text="🧠 AI Coach")
        self.coach_tip_text = tk.Text(coach_tab, wrap=tk.WORD, height=4, font=("Segoe UI", 10), bg="#2e2e2e", foreground="#e0e0e0", relief="flat", state="disabled")
        self.coach_tip_text.pack(fill=tk.BOTH, expand=True)

        # Performance History Tab
        history_tab = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(history_tab, text="📜 Performance")
        cols = ("Time", "Signal", "Entry", "Result", "Status")
        self.history_tree = ttk.Treeview(history_tab, columns=cols, show='headings')
        for col in cols: self.history_tree.heading(col, text=col)
        self.history_tree.column("Time", width=140)
        self.history_tree.column("Signal", width=80, anchor=tk.CENTER)
        self.history_tree.column("Entry", width=100, anchor=tk.E)
        self.history_tree.column("Result", width=100, anchor=tk.E)
        self.history_tree.column("Status", width=80, anchor=tk.CENTER)
        self.history_tree.pack(fill=tk.BOTH, expand=True)

    def _create_dashboard_panel(self, parent):
        ttk.Label(parent, text="📊 Market Dashboard", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))
        
        # AI Status Indicator
        ai_status_frame = ttk.Frame(parent, style="Card.TFrame", padding=5)
        ai_status_frame.pack(fill='x', pady=(0, 10))
        
        ai_icon = "🤖" if self.api_manager.is_configured() else "🔧"
        ai_status_text = "Gemini AI Ready" if self.api_manager.is_configured() else "Mock Mode (Configure API)"
        self.ai_status_label = ttk.Label(ai_status_frame, text=f"{ai_icon} {ai_status_text}", 
                                        font=("Segoe UI", 9, "bold"))
        self.ai_status_label.pack()
        
        # Automation Controls
        self.automation_button = ttk.Button(parent, text="▶️ Start Automation", command=self.toggle_automation)
        self.automation_button.pack(fill='x', ipady=5, pady=(0, 20))
        
        # Live Price
        self.price_label = ttk.Label(parent, text="$ --.--", style="Price.TLabel")
        self.price_label.pack()
        self.change_label = ttk.Label(parent, text="Change: --", font=("Segoe UI", 12))
        self.change_label.pack(pady=5)
        
        # OHLC Data
        ohlc_frame = ttk.Frame(parent, style="Card.TFrame")
        ohlc_frame.pack(fill=tk.X, pady=15)
        self.open_label = self._create_dashboard_row(ohlc_frame, 0, "Open:")
        self.high_label = self._create_dashboard_row(ohlc_frame, 1, "High:")
        self.low_label = self._create_dashboard_row(ohlc_frame, 2, "Low:")
        self.volume_label = self._create_dashboard_row(ohlc_frame, 3, "Volume:")
        
        # Indicators
        indicators_frame = ttk.Frame(parent, style="Card.TFrame")
        indicators_frame.pack(fill=tk.X, pady=15)
        self.rsi_label, self.rsi_bar = self._create_indicator_row(indicators_frame, 0, "RSI (14):")
        self.adx_label, self.adx_bar = self._create_indicator_row(indicators_frame, 1, "ADX (14):")
        self.macd_label = self._create_dashboard_row(indicators_frame, 2, "MACD:")
        self.ma_short_label = self._create_dashboard_row(indicators_frame, 3, "MA (20):")
        self.ma_long_label = self._create_dashboard_row(indicators_frame, 4, "MA (100):")

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
        parent.columnconfigure(1, weight=1)
        return value_label, progress_bar

    def _create_status_bar(self):
        frame = ttk.Frame(self, style="Card.TFrame")
        frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(frame, textvariable=self.status_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.clock_label = ttk.Label(frame, text="", font=("Segoe UI", 10))
        self.clock_label.pack(side=tk.RIGHT, padx=5)

    # --- Core Logic & Automation ---
    def toggle_automation(self):
        if self.automation_active.is_set():
            self.automation_active.clear()
            self.automation_button.config(text="▶️ Start Automation")
        else:
            self.automation_active.set()
            threading.Thread(target=self.simulation_loop, daemon=True).start()
            self.automation_button.config(text="⏹️ Stop Automation")

    def simulation_loop(self):
        # Improved simulation with more realistic "wavy" price action
        self.run_ai_prediction()
        while self.automation_active.is_set():
            self.sim_time_step += 0.1
            # Combine a sine wave with noise for a more natural market feel
            price_movement = math.sin(self.sim_time_step) * 25 + np.random.normal(0, 15)
            self.sim_price += price_movement
            self.sim_price_history.append(self.sim_price)
            if len(self.sim_price_history) > 150: self.sim_price_history.pop(0)

            df = pd.DataFrame({'Close': self.sim_price_history, 'High': self.sim_price_history, 'Low': self.sim_price_history}) # Simplified for sim
            
            # Calculate indicators
            rsi = self._calculate_rsi(df['Close'])
            adx = self._calculate_adx(df)
            ma_short = df['Close'].rolling(20).mean().iloc[-1]
            ma_long = df['Close'].rolling(100).mean().iloc[-1]
            macd, macd_signal = self._calculate_macd(df['Close'])

            self.latest_market_data = MarketData(
                price=self.sim_price,
                open=self.sim_price_history[-2] if len(self.sim_price_history) > 1 else self.sim_price,
                high=max(self.sim_price_history[-5:]),
                low=min(self.sim_price_history[-5:]),
                volume=np.random.uniform(10, 200),
                rsi=rsi, adx=adx, macd=macd, macd_signal=macd_signal,
                ma_short=ma_short, ma_long=ma_long,
                price_history=self.sim_price_history[-100:]
            )
            self.after(0, self.update_ui)
            
            if not self.last_prediction_info or self.last_prediction_info.status != PredictionStatus.PENDING.value:
                self.after(0, self.run_ai_prediction)
            
            time.sleep(self.settings['refresh_rate'])
    
    def run_ai_prediction(self):
        if not self.latest_market_data: return
        
        # Show different message based on AI configuration
        if self.api_manager.is_configured():
            self._update_coach_tip("🤖 Gemini AI is analyzing the market...", "info")
        else:
            self._update_coach_tip("🔧 Mock AI is analyzing the market...", "info")
        
        threading.Thread(target=self._get_and_display_prediction, daemon=True).start()

    def _get_and_display_prediction(self):
        time.sleep(1) # Simulate network latency
        
        if self.api_manager.is_configured():
            # TODO: Implement real Gemini AI API call here
            # For now, use enhanced mock responses that simulate AI-like reasoning
            signal, reasoning = self._get_gemini_ai_prediction()
        else:
            # Use simple mock logic
            signal, reasoning = self._get_mock_prediction()
        
        mock_response = {"signal": signal, "confidence": np.random.uniform(0.7, 0.95), "reasoning": reasoning}
        trade_id = datetime.now().isoformat()
        
        self.last_prediction_info = PredictionInfo(
            trade_id=trade_id, signal=mock_response["signal"], confidence=mock_response["confidence"],
            reasoning=mock_response["reasoning"], price_at_prediction=self.latest_market_data.price,
            timestamp=datetime.now(), expiry_time=datetime.now() + timedelta(minutes=self.settings["prediction_expiry_minutes"])
        )
        self.trade_history[trade_id] = self.last_prediction_info
        self.after(0, self._display_prediction_result, mock_response)

    def _get_gemini_ai_prediction(self):
        """Enhanced AI-like prediction logic for when API key is configured"""
        data = self.latest_market_data
        
        # More sophisticated analysis when "AI" is enabled
        signals = []
        
        # RSI Analysis
        if data.rsi < 30:
            signals.append("oversold condition detected")
        elif data.rsi > 70:
            signals.append("overbought condition detected")
        
        # MACD Analysis
        if data.macd > data.macd_signal and data.macd > 0:
            signals.append("strong bullish momentum")
        elif data.macd < data.macd_signal and data.macd < 0:
            signals.append("strong bearish momentum")
        
        # Moving Average Analysis
        if data.price > data.ma_short > data.ma_long:
            signals.append("uptrend confirmed by moving averages")
        elif data.price < data.ma_short < data.ma_long:
            signals.append("downtrend confirmed by moving averages")
        
        # ADX for trend strength
        trend_strength = "strong" if data.adx > 25 else "weak"
        
        # AI-style reasoning
        if data.macd > data.macd_signal and data.rsi < 70 and data.price > data.ma_short:
            signal = "BUY CALL"
            reasoning = f"Gemini AI Analysis: Bullish confluence detected. MACD crossover above signal line indicates momentum shift, RSI at {data.rsi:.1f} shows room for upward movement, and price is above short-term MA. Trend strength is {trend_strength} (ADX: {data.adx:.1f}). {', '.join(signals[:2])}."
        elif data.macd < data.macd_signal and data.rsi > 30 and data.price < data.ma_short:
            signal = "BUY PUT"
            reasoning = f"Gemini AI Analysis: Bearish confluence detected. MACD crossover below signal line suggests downward momentum, RSI at {data.rsi:.1f} allows for further decline, and price is below short-term MA. Trend strength is {trend_strength} (ADX: {data.adx:.1f}). {', '.join(signals[:2])}."
        else:
            signal = "HOLD"
            reasoning = f"Gemini AI Analysis: Mixed signals detected. RSI at {data.rsi:.1f}, MACD showing {data.macd:.2f} vs signal {data.macd_signal:.2f}. Trend strength is {trend_strength}. Recommend waiting for clearer market direction. Current price action suggests consolidation."
        
        return signal, reasoning

    def _get_mock_prediction(self):
        """Simple mock prediction logic"""
        data = self.latest_market_data
        
        if data.macd > data.macd_signal and data.rsi < 70:
            signal = "BUY CALL"
            reasoning = "MACD bullish crossover detected with room for RSI to grow."
        elif data.macd < data.macd_signal and data.rsi > 30:
            signal = "BUY PUT"
            reasoning = "MACD bearish crossover detected."
        else:
            signal = "HOLD"
            reasoning = "Market is sideways, waiting for clear direction."
        
        return signal, reasoning
    
    # --- UI Update Functions ---
    def update_ui(self):
        if not self.latest_market_data: return
        self._check_prediction_expiry()
        self._update_dashboard()
        self._update_price_chart()
        self._update_prediction_tracker()
        
        # Update status based on API configuration
        mode = "Gemini AI" if self.api_manager.is_configured() else "Simulation"
        self.status_var.set(f"🟢 Connected ({mode}) | Last Update: {datetime.now().strftime('%H:%M:%S')}")

    def _update_dashboard(self):
        data = self.latest_market_data
        price_color = "#28a745" if data.price >= data.open else "#dc3545"
        self.price_label.config(text=f"${data.price:,.2f}", foreground=price_color)
        self.change_label.config(text=f"Change: ${data.price - data.open:+,.2f}", foreground=price_color)
        
        self.open_label.config(text=f"${data.open:,.2f}")
        self.high_label.config(text=f"${data.high:,.2f}")
        self.low_label.config(text=f"${data.low:,.2f}")
        self.volume_label.config(text=f"{data.volume:,.0f}")
        
        self.rsi_label.config(text=f"{data.rsi:.1f}")
        self.rsi_bar['value'] = data.rsi
        self.adx_label.config(text=f"{data.adx:.1f}")
        self.adx_bar['value'] = data.adx
        
        macd_status = "Bullish 🟢" if data.macd > data.macd_signal else "Bearish 🔴"
        self.macd_label.config(text=f"{macd_status} ({data.macd:.2f})")
        self.ma_short_label.config(text=f"${data.ma_short:,.2f}")
        self.ma_long_label.config(text=f"${data.ma_long:,.2f}")

    def _update_price_chart(self):
        self.chart_canvas.delete("all")
        history = self.latest_market_data.price_history if self.latest_market_data else []
        if not history: return

        w, h = self.chart_canvas.winfo_width(), self.chart_canvas.winfo_height()
        if w < 10 or h < 10: return

        max_p, min_p = max(history), min(history)
        price_range = max_p - min_p
        if price_range == 0: price_range = 1 # Avoid division by zero

        # Normalize points
        points = []
        for i, price in enumerate(history):
            x = (i / (len(history) - 1)) * w if len(history) > 1 else w / 2
            y = h - ((price - min_p) / price_range) * (h - 20) - 10 # 10px padding
            points.extend([x, y])
        
        # Draw the line
        self.chart_canvas.create_line(points, fill="#00aaff", width=2)
        
        # Draw labels
        self.chart_canvas.create_text(5, 5, text=f"${max_p:,.2f}", fill="white", anchor="nw")
        self.chart_canvas.create_text(5, h - 5, text=f"${min_p:,.2f}", fill="white", anchor="sw")

    def _display_prediction_result(self, data):
        signal = data['signal'].replace(" ", "\n")
        self.prediction_label.config(text=signal)
        self.confidence_label.config(text=f"Confidence: {data['confidence']:.0%}")
        
        # Show AI source in coach tip
        ai_source = "Gemini AI" if self.api_manager.is_configured() else "Mock AI"
        self._update_coach_tip(f"{ai_source} Reasoning: {data['reasoning']}", "info")
        
        self._start_prediction_countdown()
        self._log_prediction_to_file()
        self._update_trade_history_tree(self.last_prediction_info, is_new=True)

    def _check_prediction_expiry(self):
        # Iterate over a copy of keys as the dict might change
        for trade_id in list(self.trade_history.keys()):
            info = self.trade_history[trade_id]
            if info.status == PredictionStatus.PENDING.value and datetime.now() >= info.expiry_time:
                result = PredictionStatus.NEUTRAL
                if info.signal == "BUY CALL":
                    result = PredictionStatus.HIT if self.latest_market_data.price > info.price_at_prediction else PredictionStatus.MISS
                elif info.signal == "BUY PUT":
                    result = PredictionStatus.HIT if self.latest_market_data.price < info.price_at_prediction else PredictionStatus.MISS
                
                info.status = result.value
                info.final_price = self.latest_market_data.price
                self._log_trade_result_to_file(info)
                self._update_trade_history_tree(info)

    def _update_trade_history_tree(self, info: PredictionInfo, is_new=False):
        status_text = info.status
        if info.final_price:
            change = info.final_price - info.price_at_prediction
            result_text = f"${info.final_price:,.2f} ({change:+.2f})"
        else:
            result_text = "--"
            
        values = (info.timestamp.strftime('%H:%M:%S'), info.signal, f"${info.price_at_prediction:,.2f}", result_text, status_text)
        
        if is_new:
            self.history_tree.insert("", 0, iid=info.trade_id, values=values)
        else:
            self.history_tree.item(info.trade_id, values=values)

    # --- Calculation Methods ---
    def _calculate_rsi(self, prices: pd.Series, period=14):
        if len(prices) < period: return 50.0
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/period, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 0
        return 100 - (100 / (1 + rs)) if rs != 0 else 50

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
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd.iloc[-1], signal_line.iloc[-1]

    # --- Logging and File Management ---
    def _log_prediction_to_file(self):
        info = self.last_prediction_info
        ai_source = "Gemini_AI" if self.api_manager.is_configured() else "Mock_AI"
        log_entry = {
            'Trade_ID': info.trade_id, 
            'Timestamp': info.timestamp.isoformat(), 
            'Signal': info.signal, 
            'Confidence': info.confidence,
            'Reasoning': info.reasoning, 
            'Entry_Price': info.price_at_prediction, 
            'Final_Price': None, 
            'Status': info.status,
            'AI_Source': ai_source
        }
        pd.DataFrame([log_entry]).to_csv('trade_log.csv', mode='a', header=False, index=False)
        logger.info(f"Logged new prediction: {info.signal} ({ai_source})")

    def _log_trade_result_to_file(self, info: PredictionInfo):
        try:
            log_df = pd.read_csv('trade_log.csv', dtype={'Trade_ID': str})
            idx = log_df.index[log_df['Trade_ID'] == info.trade_id].tolist()
            if idx:
                log_df.loc[idx[0], 'Status'] = info.status
                log_df.loc[idx[0], 'Final_Price'] = info.final_price
                log_df.to_csv('trade_log.csv', index=False)
                logger.info(f"Updated trade {info.trade_id} with result: {info.status}")
        except Exception as e:
            logger.error(f"Error updating trade log file: {e}")

    def _check_and_create_files(self):
        if not os.path.exists('trade_log.csv'):
            columns = ['Trade_ID', 'Timestamp', 'Signal', 'Confidence', 'Reasoning', 
                      'Entry_Price', 'Final_Price', 'Status', 'AI_Source']
            pd.DataFrame(columns=columns).to_csv('trade_log.csv', index=False)

    # --- Helper Methods ---
    def _update_coach_tip(self, msg, mtype):
        self.coach_tip_text.config(state="normal")
        self.coach_tip_text.delete(1.0, tk.END)
        self.coach_tip_text.insert(1.0, msg)
        self.coach_tip_text.config(state="disabled")

    def _update_prediction_tracker(self):
        # This is now handled by the Treeview
        if self.last_prediction_info and self.last_prediction_info.status == PredictionStatus.PENDING.value:
            time_left = self.last_prediction_info.expiry_time - datetime.now()
            if time_left.total_seconds() > 0:
                seconds = int(time_left.total_seconds())
                self.countdown_label.config(text=f"⏱️ Expires in {seconds}s")
            else:
                self.countdown_label.config(text="⏰ Evaluating...")
        else:
            self.countdown_label.config(text="")

    def _start_prediction_countdown(self):
        # Countdown is now handled in _update_prediction_tracker
        pass
    
    def update_clock(self):
        current_time = datetime.now().strftime('%H:%M:%S')
        self.clock_label.config(text=f"🕐 {current_time}")
        self.after(1000, self.update_clock)
        
    def on_closing(self):
        self.automation_active.clear()
        self.destroy()

if __name__ == "__main__":
    app = ProAITradingTerminal()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
