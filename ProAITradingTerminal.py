import tkinter as tk
from tkinter import ttk
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

# --- Main Application ---
class ProAITradingTerminal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🚀 Pro AI Trading Terminal v14.0")
        self.geometry("1400x900")
        self.minsize(1200, 800)

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

        self.status_var.set("🟡 Ready. Start Automation to begin simulation.")
        logger.info("Pro AI Trading Terminal Initialized.")

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
        self._update_coach_tip("🤖 AI is analyzing the market...", "info")
        threading.Thread(target=self._get_and_display_prediction, daemon=True).start()

    def _get_and_display_prediction(self):
        time.sleep(1) # Simulate network latency
        signal, reasoning = "HOLD", "Market is sideways."
        if self.latest_market_data.macd > self.latest_market_data.macd_signal and self.latest_market_data.rsi < 70:
            signal, reasoning = "BUY CALL", "MACD bullish crossover detected with room for RSI to grow."
        elif self.latest_market_data.macd < self.latest_market_data.macd_signal and self.latest_market_data.rsi > 30:
            signal, reasoning = "BUY PUT", "MACD bearish crossover detected."
        
        mock_response = {"signal": signal, "confidence": np.random.uniform(0.7, 0.9), "reasoning": reasoning}
        trade_id = datetime.now().isoformat()
        
        self.last_prediction_info = PredictionInfo(
            trade_id=trade_id, signal=mock_response["signal"], confidence=mock_response["confidence"],
            reasoning=mock_response["reasoning"], price_at_prediction=self.latest_market_data.price,
            timestamp=datetime.now(), expiry_time=datetime.now() + timedelta(minutes=self.settings["prediction_expiry_minutes"])
        )
        self.trade_history[trade_id] = self.last_prediction_info
        self.after(0, self._display_prediction_result, mock_response)
    
    # --- UI Update Functions ---
    def update_ui(self):
        if not self.latest_market_data: return
        self._check_prediction_expiry()
        self._update_dashboard()
        self._update_price_chart()
        self._update_prediction_tracker()
        self.status_var.set(f"🟢 Connected (Simulation) | Last Update: {datetime.now().strftime('%H:%M:%S')}")

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
        self._update_coach_tip(f"AI Reasoning: {data['reasoning']}", "info")
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

    # --- Other Methods (Logging, Settings, etc.) ---
    def _log_prediction_to_file(self):
        info = self.last_prediction_info
        log_entry = {'Trade_ID': info.trade_id, 'Timestamp': info.timestamp.isoformat(), 'Signal': info.signal, 'Confidence': info.confidence,
                     'Reasoning': info.reasoning, 'Entry_Price': info.price_at_prediction, 'Final_Price': None, 'Status': info.status}
        pd.DataFrame([log_entry]).to_csv('trade_log.csv', mode='a', header=False, index=False)
        logger.info(f"Logged new prediction: {info.signal}")

    def _log_trade_result_to_file(self, info: PredictionInfo):
        # **THIS IS THE CORRECTED LOGIC**
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

    # (Add other helper methods like _check_and_create_files, _create_settings_dialog, _update_coach_tip, _start_prediction_countdown, _update_prediction_tracker, update_clock, on_closing etc. here)
    # These methods are mostly unchanged from your original script but should be adapted for the new UI elements.
    # To keep this example concise, I've omitted them, but they are required for full functionality.
    
    # Placeholder for coach tip update
    def _update_coach_tip(self, msg, mtype):
        self.coach_tip_text.config(state="normal")
        self.coach_tip_text.delete(1.0, tk.END)
        self.coach_tip_text.insert(1.0, msg)
        self.coach_tip_text.config(state="disabled")

    # Placeholder for prediction tracker update
    def _update_prediction_tracker(self):
        # This is now handled by the Treeview
        pass

    def _start_prediction_countdown(self):
        # This logic is still relevant
        pass
    
    def _check_and_create_files(self):
        if not os.path.exists('trade_log.csv'):
            pd.DataFrame(columns=['Trade_ID', 'Timestamp', 'Signal', 'Confidence', 'Reasoning', 'Entry_Price', 'Final_Price', 'Status']).to_csv('trade_log.csv', index=False)
    
    def update_clock(self):
        self.clock_label.config(text=f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        self.after(1000, self.update_clock)
        
    def on_closing(self):
        self.automation_active.clear()
        self.destroy()

if __name__ == "__main__":
    app = ProAITradingTerminal()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
