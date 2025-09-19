# Pro AI Trading Terminal

A sophisticated, GUI-based paper trading terminal for simulating cryptocurrency (BTC/USDT) trading strategies. This application leverages a local AI engine with an advanced rule-based system and offers the capability to integrate with Google's Gemini AI for generating trading signals.

![Pro AI Trading Terminal Screenshot](https://i.imgur.com/your-screenshot.png) *(Note: Replace with an actual screenshot of the application)*

## 🚀 Features

*   **Multiple Operating Modes**:
    *   **Data Collection**: Gathers and logs simulated market data for analysis.
    *   **AI Prediction**: Generates real-time trading signals (BUY CALL/BUY PUT/HOLD) without executing trades.
    *   **Paper Trading**: Automatically executes simulated trades based on AI signals, managing a virtual portfolio.
*   **Advanced AI Engine**:
    *   **Sophisticated Rules Engine**: A built-in, score-based system that analyzes multiple technical indicators (MACD, RSI, ADX, Moving Averages) to produce high-quality trading signals.
    *   **Gemini AI Integration (Simulated)**: Features a robust simulation of calls to the Gemini AI, complete with dynamically generated, expert-level prompts. It is designed for easy integration with a real Gemini API key.
*   **Comprehensive GUI**:
    *   **Live Candlestick Chart**: Visualizes simulated BTC/USDT price action.
    *   **Real-time Market Dashboard**: Displays the current price, price change, and key technical indicator values.
    *   **AI Signal Panel**: Clearly shows the latest AI-generated signal, confidence level, and reasoning.
    *   **Live Performance Tracking**: Monitors and displays session-based trading performance, including wins, losses, win rate, and net P&L.
*   **Paper Trading and Risk Management**:
    *   Configure your virtual balance, risk-per-trade percentage, and asset payout percentage.
    *   Automatic calculation of trade size and potential profit/loss.
*   **Data Logging and Export**:
    *   Automatically logs all generated market data and trade history to CSV files.
    *   Functionality to export the complete trade history for external analysis.
*   **Secure API Key Management**:
    *   A secure, user-friendly interface for managing your Google Gemini API key, which is stored locally in an encoded format.

## 🛠️ Getting Started

### Prerequisites

*   Python 3.8 or higher
*   Required Python libraries:
    *   pandas
    *   numpy

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/pro-ai-trading-terminal.git
    cd pro-ai-trading-terminal
    ```

2.  **Install the required libraries:**
    ```bash
    pip install pandas numpy
    ```

3.  **Run the application:**
    ```bash
    python your_script_name.py
    ```
    *(Note: Replace `your_script_name.py` with the actual name of the Python file.)*

### Configuration

*   **Gemini AI API Key (Optional)**:
    1.  On the application's top menu, navigate to `Settings > Configure Gemini AI API`.
    2.  A dialog box will appear with instructions on how to obtain a free Google Gemini API key.
    3.  Paste your key into the provided field and click "Save & Close".
    4.  If no API key is provided, the terminal will default to using its advanced internal Rules Engine.

## 🕹️ How to Use

1.  **Launch the Application**: Run the main Python script.

2.  **Select an Operating Mode**:
    *   **Data Collection**: To simply observe and log the simulated market data.
    *   **AI Prediction**: To see the AI signals and reasoning without any financial impact.
    *   **Paper Trading**: To have the application automatically execute trades on a virtual balance based on the AI signals.

3.  **Configure Paper Trading (if applicable)**:
    *   In the "Paper Trading Controls" panel, set your desired starting balance, risk percentage per trade, and the payout percentage for a winning trade.

4.  **Start the Automation**:
    *   Click the "▶️ Start Automation" button to begin the market simulation and AI analysis. The button will change to "⏹️ Stop..." indicating that the simulation is active.

5.  **Monitor Performance**:
    *   Observe the live chart, dashboard, and AI signals.
    *   Track the results of your trading session in the "Performance" tab.

6.  **Stop the Automation**:
    *   Click the "⏹️ Stop..." button to pause the simulation. Session trade data will be automatically appended to the `trade_log.csv` file upon closing the application.

## Operating Modes Explained

*   ### **Data Collection**
    In this mode, the terminal focuses solely on generating and logging simulated market data and technical indicators into `market_data_log.csv`. No AI predictions are made, making it ideal for data gathering and analysis.

*   ### **AI Prediction**
    This mode activates the AI Engine to analyze the market data in real-time. It will display "BUY CALL", "BUY PUT", or "HOLD" signals along with the reasoning and confidence level, but will not execute any trades. This is useful for evaluating the AI's performance without risk.

*   ### **Paper Trading**
    The most advanced mode. It uses the AI's signals to automatically execute trades against a virtual account balance. The system uses your predefined risk management settings to calculate trade sizes and tracks the profit and loss from each trade, providing a realistic simulation of automated trading.

## Technical Details

*   **Market Data Simulation**: The application does not connect to a live market feed. Instead, it generates a continuous stream of simulated price data using a combination of sine waves and random noise to create realistic-seeming market movements. All technical indicators are calculated based on this simulated data.
*   **AI Engine Logic**:
    *   The **Rules Engine** uses a scoring system. It evaluates conditions across MACD, RSI, ADX, and Moving Averages. Bullish or bearish points are awarded for each condition met. A signal is generated only if a cumulative score threshold is passed, ensuring higher-quality signals.
    *   The **Gemini AI Simulation** constructs a detailed, expert-level prompt containing the latest market data and technical indicators. While the provided code simulates the response for demonstration, it is designed to be a plug-and-play component for a real API call.

---

*This project is for educational and simulation purposes only and should not be used for live trading with real money.*
