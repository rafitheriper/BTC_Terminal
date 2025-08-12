# Pro AI Trading Terminal v14.0

A next-generation desktop trading terminal built with Python and Tkinter, delivering real-time market simulation, AI-powered trading signals, and advanced technical analysis tools — all in a sleek, modern interface.

---

## Key Features

### Real-Time Market Simulation

* Dynamic candlestick chart with smooth animations
* Realistic, wave-based market data simulation
* OHLC (Open, High, Low, Close) data display
* Volume tracking in real time

### AI Trading Signals

* BUY CALL – Bullish prediction
* BUY PUT – Bearish prediction
* HOLD – Neutral recommendation
* Confidence score for every signal
* Automated signal generation with countdown timer

### Technical Indicators

* RSI (Relative Strength Index) – Momentum analysis
* ADX (Average Directional Index) – Trend strength
* MACD – Trend direction & momentum
* 20 & 100-period Moving Averages
* Visual indicator bars for quick insights

### AI Coach

* Real-time market reasoning
* Educational trading tips
* Trade rationale explanations

### Performance Tracking

* Full trade history with timestamps
* Win/Loss tracking (HIT/MISS/NEUTRAL)
* Entry & exit price logging
* Analytics for performance review

### Modern Dark Theme

* Professional, minimalistic dark mode
* Responsive panels & tabbed navigation
* Real-time status & clock

---

## Screenshots



<img width="1918" height="1031" alt="Image" src="https://github.com/user-attachments/assets/48a39d5d-f6c0-4b11-9fb2-cff923bf5fa1" />
<img width="1919" height="1032" alt="Image" src="https://github.com/user-attachments/assets/b965409e-ae74-4fd2-b560-d3a5c7878350" />

---

## Requirements

**Python Dependencies:**

```bash
pip install pandas numpy
```

**System Requirements:**

* Python 3.7+
* Windows, macOS, or Linux
* Minimum resolution: 1200x800

---

## Installation

1. Clone or Download this repository.
2. Install dependencies:

   ```bash
   pip install pandas numpy
   ```
3. Run the application:

   ```bash
   python trading_terminal.py
   ```

---

## Usage Guide

### Getting Started

1. Launch the application.
2. Click Start Automation.
3. Monitor live price movements and AI trading signals.
4. Review performance in the History tab.

### Interface Overview

**Left Panel:**

* Live Chart
* AI Signal Tab
* AI Coach Tab
* Performance Tab

**Right Panel:**

* Market Dashboard (Live OHLC & Indicators)
* Automation Controls
* Status Bar

### Signal Types

* BUY CALL → Price expected to rise
* BUY PUT → Price expected to fall
* HOLD → Sideways movement

### Indicator Reference

* RSI > 70 → Overbought, < 30 → Oversold
* ADX > 25 → Strong trend
* MACD crossover → Bullish/Bearish

---

## Configuration

* Refresh Rate: 2 seconds
* Prediction Expiry: 1 minute

---

## How It Works

**Market Simulation:**

* Wave functions + random noise = realistic price action
* Historical data used for indicator calculations

**AI Signal Generation:**

* MACD crossovers
* RSI conditions
* Moving average relationships
* Momentum analysis

**Performance Tracking:**

* Automatic trade logging to `trade_log.csv`
* Result classification: HIT / MISS / NEUTRAL

---

## Data Logging

Trade logs include:

* Trade ID
* Timestamp
* Signal type
* Confidence score
* Entry/Exit prices
* Final status

---

## Troubleshooting

**App won’t start:**

* Check Python version (3.7+)
* Install dependencies: `pip install pandas numpy`

**Chart not displaying:**

* Resize window to refresh chart
* Restart automation

**CSV file issues:**

* Delete `trade_log.csv`
* Ensure write permissions

---

## Educational Use Only

This application is for learning purposes only — not for real-world trading.

**Disclaimer:** Not financial advice. Market data is simulated.

---

## Future Roadmap

* Multi-timeframe analysis
* Additional indicators
* Exportable trade reports
* Custom alert system
* Portfolio management tools

---

## Contributing

Contributions are welcome. Fork the repository, make improvements, and submit a pull request.

---

## License

MIT License — Free to use and modify for educational purposes.
