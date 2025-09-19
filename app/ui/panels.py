# app/ui/panels.py
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Callable

from ..utils.config import Style
from ..core.data_models import OperatingMode

def create_menu_bar(parent_window: tk.Tk, callbacks: Dict[str, Callable]) -> None:
    """Creates and attaches the main menu bar to the root window."""
    menubar = tk.Menu(parent_window)
    parent_window.config(menu=menubar)

    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Settings", menu=settings_menu)
    settings_menu.add_command(label="🔑 Configure Gemini AI API", command=callbacks.get('show_api_config'))

    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="❓ About", command=callbacks.get('show_about'))

def create_chart_panel(parent: ttk.Frame) -> Dict[str, Any]:
    """Builds the main chart panel."""
    ttk.Label(parent, text="📈 Live Candlestick Chart (BTC/USDT)", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 10))
    chart_canvas = tk.Canvas(parent, background="#1e1e1e", highlightthickness=0)
    chart_canvas.pack(fill=tk.BOTH, expand=True)
    return {'chart_canvas': chart_canvas}

def create_dashboard_panel(parent: ttk.Frame, variables: Dict[str, Any], callbacks: Dict[str, Callable]) -> Dict[str, Any]:
    """Builds the right-hand dashboard panel with market info and controls."""
    widgets = {}
    
    ttk.Label(parent, text="📊 Market Dashboard", style="SubHeader.TLabel").pack(anchor="w", pady=(0, 15))

    # --- Operating Mode Frame ---
    mode_frame = ttk.LabelFrame(parent, text="Operating Mode", style="Card.TFrame", padding=10)
    mode_frame.pack(fill='x', pady=(0, 10))
    for mode in OperatingMode:
        rb = ttk.Radiobutton(
            mode_frame, text=mode.value, variable=variables['operating_mode'],
            value=mode.value, command=callbacks.get('on_mode_change')
        )
        rb.pack(side=tk.LEFT, padx=10, expand=True)
    widgets['mode_frame'] = mode_frame
    
    # --- Automation Button ---
    widgets['automation_button'] = ttk.Button(parent, text="▶️ Start Automation", command=callbacks.get('toggle_automation'))
    widgets['automation_button'].pack(fill='x', ipady=5, pady=(5, 15))

    # --- Paper Trading Panel ---
    paper_frame = ttk.LabelFrame(parent, text="💰 Paper Trading Controls", style="Card.TFrame", padding=10)
    
    ttk.Label(paper_frame, text="Paper Balance ($):", font=Style.FONTS["bold"]).grid(row=0, column=0, sticky='w', pady=3, padx=5)
    balance_entry = ttk.Entry(paper_frame, textvariable=variables['paper_balance'])
    balance_entry.grid(row=0, column=1, sticky='ew', padx=5, pady=3)
    balance_entry.bind("<KeyRelease>", callbacks.get('on_paper_config_change'))

    ttk.Label(paper_frame, text="Risk Per Trade (%):", font=Style.FONTS["bold"]).grid(row=1, column=0, sticky='w', pady=3, padx=5)
    risk_entry = ttk.Entry(paper_frame, textvariable=variables['paper_risk_percent'])
    risk_entry.grid(row=1, column=1, sticky='ew', padx=5, pady=3)
    risk_entry.bind("<KeyRelease>", callbacks.get('on_paper_config_change'))

    ttk.Label(paper_frame, text="Win Payout (%):", font=Style.FONTS["bold"]).grid(row=2, column=0, sticky='w', pady=3, padx=5)
    payout_entry = ttk.Entry(paper_frame, textvariable=variables['paper_payout_percent'])
    payout_entry.grid(row=2, column=1, sticky='ew', padx=5, pady=3)
    payout_entry.bind("<KeyRelease>", callbacks.get('on_paper_config_change'))

    paper_frame.columnconfigure(1, weight=1)
    widgets['paper_trading_frame'] = paper_frame
    widgets['balance_entry'] = balance_entry
    widgets['risk_entry'] = risk_entry
    widgets['payout_entry'] = payout_entry

    # --- Price Display ---
    widgets['price_label'] = ttk.Label(parent, text="$ --.--", style="Price.TLabel")
    widgets['price_label'].pack(pady=(10, 0))
    widgets['change_label'] = ttk.Label(parent, text="Change: --", font=Style.FONTS["h2"])
    widgets['change_label'].pack(pady=5)

    # --- Indicators ---
    indicators_frame = ttk.Frame(parent, style="Card.TFrame")
    indicators_frame.pack(fill=tk.X, pady=15, expand=True)
    indicators_frame.columnconfigure(1, weight=1)

    def _create_indicator_row(p, row, label_text):
        ttk.Label(p, text=label_text, font=Style.FONTS["bold"]).grid(row=row, column=0, sticky='w', padx=5, pady=5)
        value_label = ttk.Label(p, text="--", font=Style.FONTS["default"])
        value_label.grid(row=row, column=1, sticky='e', padx=5, pady=5)
        progress_bar = ttk.Progressbar(p, orient="horizontal", length=100, mode="determinate")
        progress_bar.grid(row=row, column=2, sticky='e', padx=5, pady=5)
        return value_label, progress_bar

    widgets['rsi_label'], widgets['rsi_bar'] = _create_indicator_row(indicators_frame, 0, "RSI (14):")
    widgets['adx_label'], widgets['adx_bar'] = _create_indicator_row(indicators_frame, 1, "ADX (14):")

    def _create_dashboard_row(p, row, label_text):
        ttk.Label(p, text=label_text, font=Style.FONTS["bold"]).grid(row=row, column=0, sticky='w', padx=5, pady=2)
        value_label = ttk.Label(p, text="--", font=Style.FONTS["default"])
        value_label.grid(row=row, column=1, columnspan=2, sticky='e', padx=5, pady=2)
        return value_label
    
    widgets['macd_label'] = _create_dashboard_row(indicators_frame, 2, "MACD:")
    widgets['ma_short_label'] = _create_dashboard_row(indicators_frame, 3, "MA (20):")
    widgets['ma_long_label'] = _create_dashboard_row(indicators_frame, 4, "MA (100):")
    
    return widgets

def create_ai_panel(parent: ttk.Frame, callbacks: Dict[str, Callable]) -> Dict[str, Any]:
    """Builds the bottom-left AI panel with its notebook tabs."""
    widgets = {}
    notebook = ttk.Notebook(parent)
    notebook.pack(fill=tk.BOTH, expand=True)

    # --- AI Signal Tab ---
    signal_tab = ttk.Frame(notebook, style="Card.TFrame")
    widgets['prediction_label'] = ttk.Label(signal_tab, text="STANDBY", font=Style.FONTS["h1"], anchor="center", background=Style.LIGHT_BG, foreground="white")
    widgets['prediction_label'].pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    widgets['confidence_label'] = ttk.Label(signal_tab, text="Confidence: --", font=Style.FONTS["bold"])
    widgets['confidence_label'].pack()
    widgets['countdown_label'] = ttk.Label(signal_tab, text="", font=Style.FONTS["h2"], foreground=Style.WARNING_COLOR)
    widgets['countdown_label'].pack(pady=10)
    notebook.add(signal_tab, text="🎯 AI Signal")

    # --- AI Coach Tab ---
    coach_tab = ttk.Frame(notebook, style="Card.TFrame", padding=10)
    coach_text = tk.Text(coach_tab, wrap=tk.WORD, height=4, font=Style.FONTS["default"], bg=Style.DARK_BG, fg=Style.TEXT_COLOR, relief="flat", state="disabled", bd=0, highlightthickness=0)
    coach_text.pack(fill=tk.BOTH, expand=True)
    widgets['coach_tip_text'] = coach_text
    notebook.add(coach_tab, text="🧠 AI Coach")

    # --- Performance Tab ---
    history_tab = ttk.Frame(notebook, style="Card.TFrame")
    cols = ("Time", "Signal", "Entry", "Result", "Status", "P&L ($)")
    tree = ttk.Treeview(history_tab, columns=cols, show='headings')
    for col in cols: tree.heading(col, text=col)
    tree.column("Time", width=120, anchor=tk.CENTER)
    tree.column("Signal", width=80, anchor=tk.CENTER)
    tree.column("Entry", width=100, anchor=tk.E)
    tree.column("Result", width=100, anchor=tk.E)
    tree.column("Status", width=80, anchor=tk.CENTER)
    tree.column("P&L ($)", width=100, anchor=tk.E)
    tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    widgets['history_tree'] = tree
    
    export_button = ttk.Button(history_tab, text="📄 Download Full History (CSV)", command=callbacks.get('export_trade_history'))
    export_button.pack(side=tk.BOTTOM, pady=5, anchor='e', padx=5)

    summary_frame = ttk.Frame(history_tab, style="Card.TFrame", padding=5)
    summary_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))

    def _create_summary_item(p, text, col):
        ttk.Label(p, text=text, font=("Segoe UI", 9), anchor='e').grid(row=0, column=col, sticky='ew', padx=(10,2))
        value_label = ttk.Label(p, text="--", font=("Segoe UI", 9, "bold"), anchor='w')
        value_label.grid(row=0, column=col + 1, sticky='ew', padx=(2,10))
        return value_label
    
    for i in range(8): summary_frame.columnconfigure(i, weight=1)
    widgets['wins_label'] = _create_summary_item(summary_frame, "Wins:", 0)
    widgets['losses_label'] = _create_summary_item(summary_frame, "Losses:", 2)
    widgets['win_rate_label'] = _create_summary_item(summary_frame, "Win Rate:", 4)
    widgets['net_pnl_label'] = _create_summary_item(summary_frame, "Net P&L:", 6)
    
    notebook.add(history_tab, text="📜 Performance (Live Session)")
    return widgets

def create_status_bar(parent: tk.Tk, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Builds the status bar at the bottom of the window."""
    widgets = {}
    frame = ttk.Frame(parent, style="Card.TFrame")
    frame.pack(side=tk.BOTTOM, fill=tk.X)
    
    ttk.Label(frame, textvariable=variables['status_var'], anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    widgets['api_status_label'] = ttk.Label(frame, text="API: --", font=Style.FONTS["bold"], anchor="e")
    widgets['api_status_label'].pack(side=tk.RIGHT, padx=10)

    widgets['clock_label'] = ttk.Label(frame, text="", font=Style.FONTS["default"])
    widgets['clock_label'].pack(side=tk.RIGHT, padx=5)

    return widgets