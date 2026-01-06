"""
Spouštěcí skript pro Gamma Vacuum Monitor
"""
import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import PressureViewer


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = PressureViewer()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()