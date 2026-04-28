"""
Hlavní okno aplikace
"""
import time
from datetime import datetime, timedelta
from pathlib import Path

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from storage.csv_handler import CSVHandler
from gui.custom_axes import ScientificAxisItem, TimeAxisItem
from gui.worker_helper import PressureWorker
from config import DEFAULT_PORT, DEFAULT_ADDR, DEFAULT_BAUD


class PressureViewer(QtWidgets.QMainWindow):
    """Hlavní okno pro monitoring tlaku"""

    def __init__(self):
        super().__init__()

        # In-memory data pro graf (worker appenduje přes signál)
        self.data_x: list = []
        self.data_y: list = []
        self.time_labels: list = []

        # Soubor & monitoring
        self.csv_handler = None
        self.active_file = None

        # Thread + worker (vytvoří se až při startu monitoringu)
        self.thread: QThread | None = None
        self.worker: PressureWorker | None = None

        # Reference & base lines (lazy init)
        self.reference_line = None
        self.base_line = None

        # Setup UI
        self._setup_ui()
        self._setup_plot()

    # --------------------------------------------------------------- UI ----

    def _setup_ui(self):
        """Inicializace UI komponent"""
        self.setWindowTitle('DIGITEL SPCe Pressure Monitor')
        self.setGeometry(100, 100, 1200, 700)
        self.setWindowIcon(QtGui.QIcon('gui/logo1.jpg'))

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QtWidgets.QVBoxLayout(central_widget)

        self._create_info_panel()

    def _create_info_panel(self):
        """Vytvoří horní info panel s tlačítky"""
        info_layout = QtWidgets.QHBoxLayout()
        stats_layout = QtWidgets.QHBoxLayout()

        # Labels
        self.label_info = QtWidgets.QLabel("Set filename to start...")
        self.label_stats = QtWidgets.QLabel("")
        info_layout.addWidget(self.label_info)
        info_layout.addWidget(self.label_stats)
        info_layout.addStretch()

        # Stats
        self.label_stats_info = QtWidgets.QLabel("Statistics: ")
        self.label_stats_stats = QtWidgets.QLabel("")
        stats_layout.addWidget(self.label_stats_info)
        stats_layout.addWidget(self.label_stats_stats)
        stats_layout.addStretch()

        # Filename input
        self.file_label = QtWidgets.QLabel("File Name:")
        self.filename_input = QtWidgets.QLineEdit()
        self.filename_input.returnPressed.connect(self.update_filename)
        info_layout.addWidget(self.file_label)
        info_layout.addWidget(self.filename_input)

        # Buttons / checkbox
        self.check_target = QtWidgets.QCheckBox(text="Reference/Base")
        self.check_target.stateChanged.connect(self.target_pressure)

        self.btn_view = QtWidgets.QPushButton("View Old Data")
        self.btn_view.clicked.connect(self.view_old_data)

        self.btn_start = QtWidgets.QPushButton("Start Monitoring")
        self.btn_start.clicked.connect(self.start_monitor)
        self.btn_start.setEnabled(False)

        self.btn_stop = QtWidgets.QPushButton("Stop Monitoring")
        self.btn_stop.clicked.connect(self.stop_monitor)
        self.btn_stop.setEnabled(False)

        self.btn_reset = QtWidgets.QPushButton("Reset Zoom")
        self.btn_reset.clicked.connect(self.reset_zoom)

        info_layout.addWidget(self.check_target)
        info_layout.addWidget(self.btn_view)
        info_layout.addWidget(self.btn_start)
        info_layout.addWidget(self.btn_stop)
        info_layout.addWidget(self.btn_reset)

        self.layout.addLayout(info_layout)
        self.layout.addLayout(stats_layout)

    def _setup_plot(self):
        """Vytvoří graf"""
        self.plot_widget = pg.PlotWidget(
            axisItems={
                'bottom': TimeAxisItem(orientation='bottom'),
                'left': ScientificAxisItem(orientation='left'),
            }
        )
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Pressure', units='Pa')
        self.plot_widget.setLabel('bottom', 'Time')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.legend = self.plot_widget.addLegend()
        self.legend.anchor((1, 0), (1, 0), offset=(-10, 10))

        # Crosshair
        self.crosshair_v = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(234, 81, 205, width=1, style=QtCore.Qt.DashLine)
        )
        self.crosshair_h = pg.InfiniteLine(
            angle=0, movable=False,
            pen=pg.mkPen(234, 81, 205, width=1, style=QtCore.Qt.DashLine)
        )
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_h, ignoreBounds=True)

        # Mouse events
        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self.mouse_moved,
        )

        self.layout.addWidget(self.plot_widget)

        # Curve
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color=(75, 192, 192), width=4),
            name='Pressure',
        )

    # ---------------------------------------------- File / monitoring ------

    def update_filename(self):
        """Nastaví CSV soubor"""
        if self._is_monitoring():
            self._show_error("Stop monitoring before changing the filename.")
            return

        name = self.filename_input.text().strip()
        if not name:
            self._show_error("Filename is empty")
            return

        csv_time = time.strftime("%Y-%m-%d")
        self._clear_plot()

        filename = f"data/gpz_{name}_{csv_time}.csv"
        self.active_file = filename
        self.csv_handler = CSVHandler(filename)

        # Recovery: pokud soubor pro dnešek už existuje (např. po pádu),
        # načteme dosavadní obsah, abychom mohli plynule pokračovat.
        timestamps, pressures, time_strings = self.csv_handler.load_data()
        if timestamps:
            self.data_x = list(timestamps)
            self.data_y = list(pressures)
            self.time_labels = list(time_strings)
            self.curve.setData(self.data_x, self.data_y)
            self.plot_widget.autoRange()

        self.label_info.setText(f"📁 CSV: {filename}")
        self.btn_start.setEnabled(True)

    def view_old_data(self):
        """Zobrazí data ze starého CSV souboru"""
        if self._is_monitoring():
            ans = QMessageBox.question(
                self, "Monitoring active",
                "Stop monitoring and view old data?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                return
            self.stop_monitor()

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV File to View",
            "data/",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not filename:
            return

        temp_handler = CSVHandler(filename)
        timestamps, pressures, time_strings = temp_handler.load_data()

        if not timestamps:
            self._show_error("No data found in selected file")
            return

        # Deaktivace monitoring režimu
        self.csv_handler = None
        self.active_file = None
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)

        self.data_x = timestamps
        self.data_y = pressures
        self.time_labels = time_strings
        self.curve.setData(self.data_x, self.data_y)

        stats = temp_handler.get_stats(pressures)
        stats_24h = temp_handler.get_24h_stats(pressures, timestamps)
        duration_seconds = timestamps[-1] - timestamps[0]
        duration_str = str(timedelta(seconds=int(duration_seconds)))
        gpz_name = Path(filename).name

        if stats and stats_24h:
            whole_dataset = (
                f"Duration: {duration_str} | Points: {stats['count']} | "
                f"Min: {stats['min']:.2e} | Max: {stats['max']:.2e}"
            )
            last_24h_dataset = (
                f"Min: {stats_24h['min']:.2e} | Max: {stats_24h['max']:.2e}"
            )
            above_limit = (
                f"Period peaks above 3.0e-05 Pa: {stats_24h['above_reference']}x | "
                f"Above 2.0e-05 Pa: {stats_24h['above_base']}x"
            )
            self.label_info.setText(f"Dataset loaded: {gpz_name}")
            self.label_stats_stats.setText(
                f"{whole_dataset} ●● Last 24h: {last_24h_dataset} | {above_limit}"
            )

        self.plot_widget.autoRange()

    def start_monitor(self):
        """Spustí monitoring v samostatném vlákně"""
        if not self.csv_handler:
            self._show_error("Set filename first")
            return
        if self._is_monitoring():
            return

        # Vytvoř thread a worker
        self.thread = QThread(self)
        self.worker = PressureWorker(
            DEFAULT_PORT, DEFAULT_ADDR, DEFAULT_BAUD,
            self.csv_handler,
        )
        self.worker.moveToThread(self.thread)

        # Životní cyklus: started → worker.start; stopped → thread.quit;
        # finished → cleanup, deleteLater workera i threadu.
        self.thread.started.connect(self.worker.start)
        self.worker.stopped.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._on_thread_finished)

        # Funkční signály
        self.worker.started.connect(self._on_monitor_started)
        self.worker.new_record.connect(self._on_new_record)
        self.worker.error.connect(self._on_worker_error)
        self.worker.connection_lost.connect(self._on_connection_lost)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.label_info.setText("Connecting to SPCe...")

        self.thread.start()

    def stop_monitor(self):
        """Pošle workerovi pokyn k zastavení (asynchronně)."""
        if not self._is_monitoring():
            return

        # Disable rovnou, ať uživatel nemůže klikat víckrát
        self.btn_stop.setEnabled(False)

        # Zavoláme stop ve workerově threadu — queued connection,
        # protože worker žije v jiném threadu.
        QtCore.QMetaObject.invokeMethod(
            self.worker, "stop", Qt.QueuedConnection
        )
        # Zbytek úklidu řeší _on_thread_finished

    # -- worker callbacks (běží v GUI threadu) ------------------------------

    def _on_monitor_started(self):
        self.label_info.setText("Monitoring active...")
        print("Monitoring active...")

    def _on_thread_finished(self):
        """Thread skončil — definitivní úklid."""
        # deleteLater už volaly slot connections; jen vynulujeme reference
        if self.thread is not None:
            self.thread.deleteLater()
        self.thread = None
        self.worker = None

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        # Pokud nebyl error, nastavíme generický "stopped" text;
        # pokud byl, nepřepisujeme zprávu z _on_connection_lost.
        if self.label_info.text() not in ("",):
            # nech původní text, pokud obsahuje error info
            pass
        self.label_info.setText("Monitoring stopped")
        print("Monitoring stopped")

    def _on_new_record(self, pressure: float, time_str: str):
        """Worker zaslal nový záznam — appendni ho do paměti a do grafu."""
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            timestamp = dt.timestamp()
        except ValueError:
            return

        self.data_x.append(timestamp)
        self.data_y.append(pressure)
        self.time_labels.append(time_str)
        self.curve.setData(self.data_x, self.data_y)

    def _on_worker_error(self, message: str):
        """Recoverable chyba (timeout, špatný řádek atp.)"""
        self.label_info.setText(message)

    def _on_connection_lost(self, message: str):
        """Fatální chyba — worker se zastavil sám, jen ukážeme dialog."""
        self._show_error(f"SPCE controller error:\n{message}")
        # Worker už zavolal cleanup_and_emit_stopped → thread.quit() proběhl,
        # _on_thread_finished se postará o tlačítka.

    def _is_monitoring(self) -> bool:
        return self.thread is not None and self.thread.isRunning()

    # ----------------------------------------------------- Plot helpers ----

    def target_pressure(self):
        """Toggle reference & base lines (idempotentní)"""
        checked = self.check_target.isChecked()

        if checked:
            if self.reference_line is None:
                self.reference_line = pg.InfiniteLine(
                    pos=3.0e-05,
                    angle=0,
                    pen=pg.mkPen(color=(73, 10, 117), width=2,
                                 style=QtCore.Qt.DashLine),
                    label='Reference: 3.0e-05 Pa',
                    labelOpts={'position': 0.94, 'color': (73, 10, 117),
                               'fill': (200, 200, 200, 50)},
                )
            if self.base_line is None:
                self.base_line = pg.InfiniteLine(
                    pos=2.0e-05,
                    angle=0,
                    pen=pg.mkPen(color=(234, 81, 205), width=2,
                                 style=QtCore.Qt.DashLine),
                    label='Base min: 2.0e-05 Pa',
                    labelOpts={'position': 0.94, 'color': (234, 81, 205),
                               'fill': (200, 200, 200, 50)},
                )
            self.plot_widget.addItem(self.reference_line)
            self.plot_widget.addItem(self.base_line)
        else:
            if self.reference_line is not None:
                self.plot_widget.removeItem(self.reference_line)
            if self.base_line is not None:
                self.plot_widget.removeItem(self.base_line)

    def reset_zoom(self):
        self.plot_widget.autoRange()

    def mouse_moved(self, evt):
        """Crosshair + tooltip s nejbližším bodem"""
        pos = evt[0]
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            return
        mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        self.crosshair_v.setPos(mouse_point.x())
        self.crosshair_h.setPos(mouse_point.y())

        if not self.data_x or not self.data_y:
            return

        # Najdi nejbližší index — jednoduchý lineární průchod stačí pro
        # běžné velikosti datasetu (řádky se přidávají sekundu po sekundě).
        mx = mouse_point.x()
        best_idx = 0
        best_dist = abs(self.data_x[0] - mx)
        for i in range(1, len(self.data_x)):
            d = abs(self.data_x[i] - mx)
            if d < best_dist:
                best_dist = d
                best_idx = i

        if 0 <= best_idx < len(self.data_y):
            self.plot_widget.setTitle(
                f"Time: {self.time_labels[best_idx]} | "
                f"Pressure: {self.data_y[best_idx]:.2e} Pa"
            )

    def _clear_plot(self):
        self.data_x = []
        self.data_y = []
        self.time_labels = []
        self.curve.setData([], [])
        self.label_stats.setText("")
        self.label_stats_stats.setText("")

    # ---------------------------------------------- Dialogs / cleanup ------

    def _show_error(self, message: str):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Error")
        dlg.setText(message)
        dlg.exec_()

    def _show_stats(self, message: str):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Statistics")
        dlg.setText(message)
        dlg.exec_()

    def closeEvent(self, event):
        """
        Při zavření okna ukončit thread a uzavřít sériový port.

        Použijeme BlockingQueuedConnection, aby main vlákno počkalo,
        než worker řádně zavře port (jinak by zůstal v OS otevřený).
        """
        if self._is_monitoring():
            try:
                QtCore.QMetaObject.invokeMethod(
                    self.worker, "stop", Qt.BlockingQueuedConnection
                )
            except Exception as e:
                print(f"Error stopping worker on close: {e}")

            self.thread.quit()
            if not self.thread.wait(3000):
                # Nouzová varianta — port by měl být zavřený díky stop() výše
                print("Thread did not finish in time, terminating.")
                self.thread.terminate()
                self.thread.wait(1000)

        event.accept()