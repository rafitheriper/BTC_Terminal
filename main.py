import sys
import logging
from app.ui.main_window import ProAITradingTerminal
from app.app_controller import AppController

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)

def main():
    """Initializes and runs the Pro AI Trading Terminal application."""
    try:
        app_controller = AppController()
        app = ProAITradingTerminal(app_controller)
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        logging.critical(f"A critical error occurred: {e}", exc_info=True)
        # Optionally, show an error dialog to the user
        # messagebox.showerror("Fatal Error", f"A critical error occurred and the application must close:\n{e}")

if __name__ == "__main__":
    main()