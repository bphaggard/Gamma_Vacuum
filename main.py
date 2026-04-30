"""
Spouštěcí skript pro Gamma Vacuum Monitor
"""
import sys
import logging
from PyQt5.QtWidgets import QApplication
from gui.main_window_load import PressureViewer
from logging_setup import setup_logging


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    try:
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        window = PressureViewer()
        window.show()
        sys.exit(app.exec_())
    except Exception:
        logger.exception("Fatal error in main")
        raise


if __name__ == '__main__':
    main()