# app/ui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import pandas as pd
from typing import Optional # This import is necessary

from ..app_controller import AppController
from ..core.data_models import OperatingMode, PredictionStatus, PredictionInfo, Candle, PaperTradingConfig
from ..utils.config import Style, APP_VERSION, TRADE_LOG_FILE
from .api_key_dialog import APIKeyDialog
from . import panels

class ProAITradingTerminal(tk.Tk):
    """
    The main application window. It is responsible for rendering the UI and
    delegating all logic to the AppController.
    """
    def __init__(self, controller: AppController):
        super().__init__()
        self.controller = controller

        # --- TKinter Variables ---
        self.operating_mode = tk.StringVar(value=OperatingMode.DATA_COLLECTION.value)
        self.status_var = tk.StringVar(value="Ready")
        self.paper_balance = tk.DoubleVar()
        self.paper_risk_percent = tk.DoubleVar()
        self.paper_payout_percent = tk.DoubleVar()
        self.chart_indicators = []

        # --- Initialize ---
        self._setup_window()
        self._link_controller_callbacks()
        self._configure_styles()
        self._create_widgets()
        self._load_initial_configs()

        self.update_clock()
        self.start_ui_updater()

    def _setup_window(self):
        self.title(f"🚀 Pro AI Trading Terminal v{APP_VERSION}")
        self.geometry("1400x950")
        self.minsize(1200, 850)
        self.configure(background=Style.DARK_BG)

    def _link_controller_callbacks(self):
        self.controller.ui_update_callback = self.update_ui_from_state
        self.controller.ui_new_prediction_callback = self.on_new_prediction
        self.controller.ui_show_message_callback = self._show_message

    def _configure_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure("TLabel", background=Style.DARK_BG, foreground=Style.TEXT_COLOR, font=Style.FONTS["default"])
        self.style.configure("SubHeader.TLabel", font=Style.FONTS["h2"], foreground=Style.ACCENT_COLOR)
        self.style.configure("Card.TFrame", background=Style.LIGHT_BG, relief="solid", borderwidth=1)
        self.style.configure("Active.Card.TFrame", background=Style.LIGHT_BG, relief="solid", borderwidth=2, bordercolor=Style.ACCENT_COLOR)
        self.style.configure("Price.TLabel", font=Style.FONTS["price"], foreground="white")
        self.style.configure("Treeview", rowheight=25, fieldbackground=Style.LIGHT_BG, background=Style.LIGHT_BG, foreground=Style.TEXT_COLOR)
        self.style.configure("Treeview.Heading", font=Style.FONTS["bold"], background=Style.DARK_BG, foreground=Style.TEXT_COLOR)

    def _create_widgets(self):
        menu_callbacks = {'show_api_config': self.show_api_config, 'show_about': self.show_about}
        panels.create_menu_bar(self, menu_callbacks)

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

        self.chart_widgets = panels.create_chart_panel(chart_frame)
        
        dashboard_vars = {
            'operating_mode': self.operating_mode, 'paper_balance': self.paper_balance,
            'paper_risk_percent': self.paper_risk_percent, 'paper_payout_percent': self.paper_payout_percent
        }
        dashboard_callbacks = {
            'on_mode_change': self.on_mode_change, 'toggle_automation': self.toggle_automation,
            'on_paper_config_change': self._on_paper_config_change
        }
        self.dashboard_widgets = panels.create_dashboard_panel(right_frame, dashboard_vars, dashboard_callbacks)

        ai_callbacks = {'export_trade_history': self.export_trade_history}
        self.ai_widgets = panels.create_ai_panel(ai_frame, ai_callbacks)

        status_bar_vars = {'status_var': self.status_var}
        self.status_bar_widgets = panels.create_status_bar(self, status_bar_vars)

    def _load_initial_configs(self):
        initial_config = self.controller.trade_manager.get_paper_trading_config()
        self.paper_balance.set(initial_config.balance)
        self.paper_risk_percent.set(initial_config.risk_percent)
        self.paper_payout_percent.set(initial_config.payout_percent)
        self._on_paper_config_change()
        self.on_mode_change()

    def start_ui_updater(self):
        self.after(100, self.update_ui_from_state)

    def update_ui_from_state(self):
        state = self.controller.get_app_state()
        
        if state["market_data"]:
            self._update_dashboard(state["market_data"])
            self._update_price_chart(state["market_data"].candle_history, state["last_prediction"])
        
        self._update_trade_history_tree(state["trade_history"])
        self._update_performance_summary(state["performance_summary"])
        self._update_api_status_ui(state["ai_source"])
        self._update_prediction_tracker(state["last_prediction"])
        
        if self.controller.automation_active.is_set():
            self.status_var.set(f"🟢 {self.operating_mode.get()} | Last Update: {datetime.now().strftime('%H:%M:%S')}")

        self.after(100, self.update_ui_from_state)

    def _update_dashboard(self, data):
        price_color = Style.PROFIT_COLOR if data.price >= data.open else Style.LOSS_COLOR
        self.dashboard_widgets['price_label'].config(text=f"${data.price:,.2f}", foreground=price_color)
        self.dashboard_widgets['change_label'].config(text=f"Change: ${data.price - data.open:+,.2f}", foreground=price_color)
        self.dashboard_widgets['rsi_label'].config(text=f"{data.rsi:.1f}"); self.dashboard_widgets['rsi_bar']['value'] = data.rsi
        self.dashboard_widgets['adx_label'].config(text=f"{data.adx:.1f}"); self.dashboard_widgets['adx_bar']['value'] = data.adx
        macd_status = "Bullish 🟢" if data.macd > data.macd_signal else "Bearish 🔴"
        self.dashboard_widgets['macd_label'].config(text=f"{macd_status} ({data.macd:.2f})")
        self.dashboard_widgets['ma_short_label'].config(text=f"${data.ma_short:,.2f}")
        self.dashboard_widgets['ma_long_label'].config(text=f"${data.ma_long:,.2f}")

    def _update_price_chart(self, candles: list[Candle], prediction: Optional[PredictionInfo]):
        canvas = self.chart_widgets['chart_canvas']
        canvas.delete("all")
        
        if not candles: return
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 10 or h < 10: return

        max_p = max(c.high for c in candles); min_p = min(c.low for c in candles)
        price_range = max_p - min_p if max_p > min_p else 1
        def p_to_y(price): return h - ((price - min_p) / price_range * (h - 40)) - 20

        candle_width = w / (len(candles) + 2); body_width = candle_width * 0.8
        for i, candle in enumerate(candles):
            x = (i + 1) * candle_width
            y_open, y_close = p_to_y(candle.open), p_to_y(candle.close)
            y_high, y_low = p_to_y(candle.high), p_to_y(candle.low)
            color = Style.PROFIT_COLOR if candle.close >= candle.open else Style.LOSS_COLOR
            canvas.create_line(x, y_high, x, y_low, fill=color, width=1)
            canvas.create_rectangle(x - body_width/2, y_close, x + body_width/2, y_open, fill=color, outline=color)
        
        if prediction and prediction.status == PredictionStatus.PENDING.value:
            self._draw_prediction_marker(prediction)

    def _update_trade_history_tree(self, history: list[PredictionInfo]):
        tree = self.ai_widgets['history_tree']
        tree.delete(*tree.get_children())
        
        tree.tag_configure("profit", foreground=Style.PROFIT_COLOR)
        tree.tag_configure("loss", foreground=Style.LOSS_COLOR)
        tree.tag_configure("white", foreground=Style.TEXT_COLOR)

        for info in reversed(history):
            change = info.final_price - info.price_at_prediction if info.final_price else 0
            result_text = f"${info.final_price:,.2f} ({change:+.2f})" if info.final_price else "--"
            pnl_text = f"{info.pnl:+.2f}" if info.pnl is not None else "--"
            pnl_color = "profit" if info.pnl and info.pnl > 0 else "loss" if info.pnl and info.pnl < 0 else "white"
            values = (info.timestamp.strftime('%H:%M:%S'), info.signal, f"${info.price_at_prediction:,.2f}", result_text, info.status, pnl_text)
            tree.insert("", 0, iid=info.trade_id, values=values, tags=(pnl_color,))

    def _update_performance_summary(self, summary: dict):
        self.ai_widgets['wins_label'].config(text=str(summary.get("wins", 0)))
        self.ai_widgets['losses_label'].config(text=str(summary.get("losses", 0)))
        self.ai_widgets['win_rate_label'].config(text=f"{summary.get('win_rate', 0.0):.1f}%")
        net_pnl = summary.get("net_pnl", 0.0)
        self.ai_widgets['net_pnl_label'].config(
            text=f"${net_pnl:,.2f}",
            foreground=Style.PROFIT_COLOR if net_pnl >= 0 else Style.LOSS_COLOR
        )

    def toggle_automation(self):
        if self.controller.automation_active.is_set():
            self.controller.stop_automation()
            self.dashboard_widgets['automation_button'].config(text="▶️ Start Automation")
        else:
            self.controller.start_automation()
            mode_text = self.operating_mode.get()
            self.dashboard_widgets['automation_button'].config(text=f"⏹️ Stop {mode_text}")
    
    def on_mode_change(self, *args):
        selected_mode = OperatingMode(self.operating_mode.get())
        self.controller.set_operating_mode(selected_mode)

        paper_frame = self.dashboard_widgets['paper_trading_frame']
        if selected_mode == OperatingMode.PAPER_TRADING:
            paper_frame.pack(fill='x', pady=(0, 15), before=self.dashboard_widgets['price_label'])
        else:
            paper_frame.pack_forget()

    def _on_paper_config_change(self, event=None):
        try:
            config = PaperTradingConfig(
                balance=self.paper_balance.get(),
                risk_percent=self.paper_risk_percent.get(),
                payout_percent=self.paper_payout_percent.get()
            )
            self.controller.trade_manager.update_paper_config(config)
        except (ValueError, tk.TclError):
            pass

    def on_new_prediction(self, info: PredictionInfo):
        self.ai_widgets['prediction_label'].config(text=info.signal.replace(" ", "\n"))
        self.ai_widgets['confidence_label'].config(text=f"Confidence: {info.confidence:.0%}")
        
        tip = info.reasoning
        if info.trade_amount is not None:
            payout = info.trade_amount * (self.paper_payout_percent.get() / 100.0)
            tip += f"\n\nPAPER TRADING: Risking ${info.trade_amount:,.2f} to win ${payout:,.2f}."
        self._update_coach_tip(tip)

    def show_api_config(self):
        dialog = APIKeyDialog(self, self.controller.api_manager)
        self.wait_window(dialog)
        self.on_mode_change()

    def show_about(self):
        messagebox.showinfo("About", f"Pro AI Trading Terminal v{APP_VERSION}\nA simulated trading terminal.")

    def export_trade_history(self):
        if not os.path.exists(TRADE_LOG_FILE) or os.path.getsize(TRADE_LOG_FILE) == 0:
            messagebox.showinfo("Export Empty", "The master trade log is empty.")
            return
        
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=f"trade_log_export_{datetime.now().strftime('%Y-%m-%d')}.csv",
                title="Save Full Trade History"
            )
            if not filepath: return
            pd.read_csv(TRADE_LOG_FILE).to_csv(filepath, index=False)
            messagebox.showinfo("Export Successful", f"Full trade history saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred: {e}")

    def on_closing(self):
        self.controller.shutdown()
        self.destroy()

    def _draw_prediction_marker(self, info: PredictionInfo):
        pass

    def _update_coach_tip(self, msg: str):
        text_widget = self.ai_widgets['coach_tip_text']
        text_widget.config(state="normal")
        text_widget.delete(1.0, tk.END)
        text_widget.insert(1.0, msg)
        text_widget.config(state="disabled")

    def _update_api_status_ui(self, ai_source: str):
        label = self.status_bar_widgets['api_status_label']
        if "Gemini" in ai_source:
            label.config(text="API: Gemini (Sim) 🟢", foreground=Style.PROFIT_COLOR)
        elif "Fallback" in ai_source:
            label.config(text="API: Rules Engine (Limit) 🟡", foreground=Style.WARNING_COLOR)
        else:
            label.config(text="API: Rules Engine 🔵", foreground=Style.INFO_COLOR)
    
    # THIS IS THE CORRECTED METHOD
    def _update_prediction_tracker(self, last_prediction: Optional[PredictionInfo]):
        label = self.ai_widgets['countdown_label']
        if last_prediction and last_prediction.status == PredictionStatus.PENDING.value:
            time_left = last_prediction.expiry_time - datetime.now()
            if time_left.total_seconds() > 0:
                label.config(text=f"⏱️ Expires in {int(time_left.total_seconds())}s")
            else:
                label.config(text="⏰ Evaluating...")
        else:
            label.config(text="")

    def _show_message(self, title: str, message: str, mtype: str):
        if mtype == 'info': messagebox.showinfo(title, message)
        elif mtype == 'warning': messagebox.showwarning(title, message)
        elif mtype == 'error': messagebox.showerror(title, message)

    def update_clock(self):
        self.status_bar_widgets['clock_label'].config(text=f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        self.after(1000, self.update_clock)