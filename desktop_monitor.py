import sys
import csv
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from datetime import datetime


class TimeAxisItem(pg.AxisItem):
    """Custom axis pro zobrazení datetime"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        """Převede timestamp na čitelný formát"""
        strings = []
        for v in values:
            try:
                dt = datetime.fromtimestamp(v)
                # Formát podle rozsahu
                if spacing < 60:  # méně než minuta
                    s = dt.strftime('%H:%M:%S')
                elif spacing < 3600:  # méně než hodina
                    s = dt.strftime('%H:%M')
                elif spacing < 86400:  # méně než den
                    s = dt.strftime('%m-%d %H:%M')
                else:
                    s = dt.strftime('%Y-%m-%d')
                strings.append(s)
            except:
                strings.append('')
        return strings


class ScientificAxisItem(pg.AxisItem):
    """Custom axis pro vědeckou notaci"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        """Zobraz čísla ve vědecké notaci"""
        strings = []
        for v in values:
            if v == 0:
                strings.append('0')
            else:
                strings.append(f'{v:.2e}')
        return strings


class PressureViewer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.filename = "spce_pressure.csv"
        self.data_x = []  # timestamps
        self.data_y = []  # pressure values

        # Nastavení okna
        self.setWindowTitle('DIGITEL SPCe Pressure Monitor')
        self.setGeometry(100, 100, 1200, 700)

        # Vytvoř centrální widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Info panel
        info_layout = QtWidgets.QHBoxLayout()
        self.label_info = QtWidgets.QLabel("Loading data...")
        self.label_stats = QtWidgets.QLabel("")
        info_layout.addWidget(self.label_info)
        info_layout.addWidget(self.label_stats)
        info_layout.addStretch()

        # Tlačítka
        #self.btn_refresh = QtWidgets.QPushButton("Refresh")
        #self.btn_refresh.clicked.connect(self.load_data)
        #info_layout.addWidget(self.btn_refresh)

        self.btn_reset_zoom = QtWidgets.QPushButton("Reset Zoom")
        self.btn_reset_zoom.clicked.connect(self.reset_zoom)
        info_layout.addWidget(self.btn_reset_zoom)

        layout.addLayout(info_layout)

        # Graf s custom osami
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

        # Aktivuj zoom a pan
        self.plot_widget.setMouseEnabled(x=True, y=True)

        # Křížový kurzor
        self.crosshair_v = pg.InfiniteLine(angle=90, movable=False,
                                           pen=pg.mkPen('r', width=1, style=QtCore.Qt.DashLine))
        self.crosshair_h = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('r', width=1, style=QtCore.Qt.DashLine))
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)
        self.plot_widget.addItem(self.crosshair_h, ignoreBounds=True)

        # Připoj mouse events
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved)

        layout.addWidget(self.plot_widget)

        # Křivka
        self.curve = self.plot_widget.plot(
            pen=pg.mkPen(color=(75, 192, 192), width=4),
            name='Pressure'
        )

        # Načti data
        self.load_data()

        # Auto-refresh timer (každých 1 sekund)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.load_data)
        self.timer.start(1000)  # 1 sekund

    def load_data(self):
        """Načte data z CSV"""
        try:
            timestamps = []
            pressures = []
            time_strings = []

            with open(self.filename, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        # Převeď timestamp string na unix timestamp
                        time_str = row["time"]
                        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        timestamp = dt.timestamp()

                        timestamps.append(timestamp)
                        pressures.append(float(row["pressure"].strip()))
                        time_strings.append(time_str)
                    except (ValueError, KeyError) as e:
                        print(f"Skipping invalid row: {row} | Error: {e}")
                        continue

            if not timestamps:
                self.label_info.setText("No data found")
                return

            # Ulož data
            self.data_x = timestamps
            self.data_y = pressures
            self.time_labels = time_strings

            # Aktualizuj graf
            self.curve.setData(self.data_x, self.data_y)

            # Statistiky
            min_p = min(pressures)
            max_p = max(pressures)
            #avg_p = sum(pressures) / len(pressures)

            self.label_info.setText(f"Points: {len(pressures)}   | ")
            self.label_stats.setText(f"Min: {min_p:.2e} | Max: {max_p:.2e}")

            #print(f"Loaded {len(pressures)} data points")

        except FileNotFoundError:
            self.label_info.setText(f"File not found: {self.filename}")
        except Exception as e:
            self.label_info.setText(f"Error: {str(e)}")
            print(f"Error loading data: {e}")

    def reset_zoom(self):
        """Reset zoom na celá data"""
        self.plot_widget.autoRange()

    def mouse_moved(self, evt):
        """Zobraz crosshair a hodnoty při pohybu myši"""
        pos = evt[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)

            self.crosshair_v.setPos(mouse_point.x())
            self.crosshair_h.setPos(mouse_point.y())

            # Najdi nejbližší bod
            if self.data_x and self.data_y:
                # Najdi index nejbližšího bodu
                distances = [abs(x - mouse_point.x()) for x in self.data_x]
                idx = distances.index(min(distances))

                if 0 <= idx < len(self.data_y):
                    time_str = self.time_labels[idx] if idx < len(self.time_labels) else "N/A"
                    pressure = self.data_y[idx]
                    self.plot_widget.setTitle(f"Time: {time_str} | Pressure: {pressure:.2e} Pa")


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Nastav styl
    app.setStyle('Fusion')

    window = PressureViewer()
    window.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()