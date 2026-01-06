"""
Hlavní okno aplikace
"""
import time
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from storage.csv_handler import CSVHandler
from gui.custom_axes import TimeAxisItem, ScientificAxisItem

class PressureViewer(QtWidgets.QMainWindow):
    """Hlavní okno pro monitoring tlaku"""

    def __init__(self):
        super().__init__()

        # Data
        self.data_x = []
        self.data_y = []
        self.time_labels = []
        self.csv_handler = None

        # Setup UI
        self._setup_ui()
        self._setup_plot()
        self._setup_timer()

    def _setup_ui(self):
        """Inicializace UI komponent"""
        self.setWindowTitle('DIGITEL SPCe Pressure Monitor')
        self.setGeometry(100, 100, 1200, 700)

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QtWidgets.QVBoxLayout(central_widget)

        # Info panel
        self._create_info_panel()

    def _create_info_panel(self):
        """Vytvoří horní info panel s tlačítky"""
        info_layout = QtWidgets.QHBoxLayout()

        # Labels
        self.label_info = QtWidgets.QLabel("Set filename to start...")
        self.label_stats = QtWidgets.QLabel("")
        info_layout.addWidget(self.label_info)
        info_layout.addWidget(self.label_stats)
        info_layout.addStretch()

        # Filename input
        self.file_label = QtWidgets.QLabel("File Name:")
        self.filename_input = QtWidgets.QLineEdit()
        self.filename_input.returnPressed.connect(self.update_filename)
        info_layout.addWidget(self.file_label)
        info_layout.addWidget(self.filename_input)

        # Buttons
        self.btn_start = QtWidgets.QPushButton("Start Monitoring")
        self.btn_start.clicked.connect(self.start_monitor)
        self.btn_start.setEnabled(False)

        self.btn_stop = QtWidgets.QPushButton("Stop Monitoring")
        self.btn_stop.clicked.connect(self.stop_monitor)
        self.btn_stop.setEnabled(False)

        self.btn_reset = QtWidgets.QPushButton("Reset Zoom")
        self.btn_reset.clicked.connect(self.reset_zoom)

        info_layout.addWidget(self.btn_start)
        info_layout.addWidget(self.btn_stop)
        info_layout.addWidget(self.btn_reset)

        self.layout.addLayout(info_layout)

    def _setup_plot(self):
        """Vytvoří graf"""
        self.plot_widget = pg.PlotWidget(
            axisItems={
                'bottom': TimeAxisItem(orientation='bottom'),
                'left': ScientificAxisItem(orientation='left')
            }
        )
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Pressure', units='Pa')
        self.plot_widget.setLabel('bottom', 'Time')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        self.plot_widget.setMouseEnabled(x=True, y=True)

        # Crosshair
        self.crosshair_v = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen('r', width=1, style=QtCore.Qt.DashLine)
        )
        self.crosshair_h = pg.InfiniteLine(
            angle=0, movable=False,
            pen=pg.mkPen('r', width=1, style=QtCore.Qt.DashLine)
        )
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_h, ignoreBounds=True)

        # Mouse events
        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self.mouse_moved
        )

        self.layout.addWidget(self.plot_widget)

        # Curve
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color=(75, 192, 192), width=4),
            name='Pressure'
        )

    def _setup_timer(self):
        """Nastaví timer pro refresh"""
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.load_data)

    def update_filename(self):
        """Nastaví CSV soubor"""
        name = self.filename_input.text().strip()
        csv_time = time.strftime("%Y-%m-%d")
        if not name:
            self.label_info.setText("❌ Filename is empty")
            return

        filename = f"data/spce_pressure_{name}_{csv_time}.csv"
        self.csv_handler = CSVHandler(filename)
        self.label_info.setText(f"📁 CSV: {filename}")
        self.btn_start.setEnabled(True)

    def start_monitor(self):
        """Spustí monitoring"""
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.timer.start(1000)  # refresh každou sekundu
        self.label_info.setText("✅ Monitoring active...")

    def stop_monitor(self):
        """Zastaví monitoring"""
        self.timer.stop()

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.label_info.setText("⏸️ Monitoring stopped")

    def load_data(self):
        """Načte a zobrazí data"""
        if not self.csv_handler:
            return

        self.csv_handler.save_record()

        timestamps, pressures, time_strings = self.csv_handler.load_data()

        if not timestamps:
            self.label_info.setText("No data yet...")
            return

        # Aktualizuj graf
        self.data_x = timestamps
        self.data_y = pressures
        self.time_labels = time_strings
        self.curve.setData(self.data_x, self.data_y)

        # Statistiky
        stats = self.csv_handler.get_stats(pressures)
        if stats:
            self.label_info.setText(f"Points: {stats['count']}")
            self.label_stats.setText(
                f"Min: {stats['min']:.2e} | Max: {stats['max']:.2e}"
            )

    def reset_zoom(self):
        """Reset zoom"""
        self.plot_widget.autoRange()

    def mouse_moved(self, evt):
        """Zobraz crosshair při pohybu myši"""
        pos = evt[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)

            self.crosshair_v.setPos(mouse_point.x())
            self.crosshair_h.setPos(mouse_point.y())

            if self.data_x and self.data_y:
                distances = [abs(x - mouse_point.x()) for x in self.data_x]
                idx = distances.index(min(distances))

                if 0 <= idx < len(self.data_y):
                    time_str = self.time_labels[idx]
                    pressure = self.data_y[idx]
                    self.plot_widget.setTitle(
                        f"Time: {time_str} | Pressure: {pressure:.2e} Pa"
                    )

    def _show_error(self, message: str):
        """Zobraz error dialog"""
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Error")
        dlg.setText(message)
        dlg.exec()