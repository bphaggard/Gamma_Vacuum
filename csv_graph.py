import sys
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QFileDialog, QLabel)
from PyQt5.QtCore import Qt
import pyqtgraph as pg


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt CSV Graph Viewer")
        self.setGeometry(100, 100, 900, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Info label
        self.info_label = QLabel("Click 'Load CSV' to select a CSV file")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

        # Load button
        self.load_btn = QPushButton("Load CSV File")
        self.load_btn.clicked.connect(self.load_csv)
        layout.addWidget(self.load_btn)

        # Create plot widget
        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)

        # Configure plot
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()
        self.plot_widget.setLabel('left', 'Pressure', units='Pa')
        self.plot_widget.setLabel('bottom', 'Time')

        # Initialize crosshair elements (will be created after loading data)
        self.vLine = None
        self.hLine = None
        self.crosshair_label = None
        self.crosshair_visible = False

        # Data storage for crosshair
        self.time_data = []
        self.pressure_data = []
        self.time_labels = []

        # Connect mouse click event
        self.plot_widget.scene().sigMouseClicked.connect(self.mouse_clicked)

    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            try:
                self.time_data = []
                self.pressure_data = []
                self.time_labels = []

                with open(file_path, 'r') as file:
                    csv_reader = csv.reader(file)
                    headers = next(csv_reader)  # Read headers

                    for i, row in enumerate(csv_reader):
                        if len(row) >= 2:
                            try:
                                # Parse pressure
                                pressure = float(row[0])
                                self.pressure_data.append(pressure)

                                # Store time string for labels
                                self.time_labels.append(row[1])

                                # Use index for x-axis positioning
                                self.time_data.append(i)

                            except ValueError:
                                continue

                if self.time_data and self.pressure_data:
                    # Clear previous plot
                    self.plot_widget.clear()

                    # Create crosshair elements after clearing
                    self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('w', width=1))
                    self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('w', width=1))
                    self.crosshair_label = pg.TextItem(anchor=(0, 1), color='w')

                    self.plot_widget.addItem(self.vLine, ignoreBounds=True)
                    self.plot_widget.addItem(self.hLine, ignoreBounds=True)
                    self.plot_widget.addItem(self.crosshair_label)

                    # Hide crosshair initially
                    self.vLine.setVisible(False)
                    self.hLine.setVisible(False)
                    self.crosshair_label.setVisible(False)
                    self.crosshair_visible = False

                    # Plot the data
                    self.plot_widget.plot(
                        self.time_data,
                        self.pressure_data,
                        pen=pg.mkPen(color='orange', width=2),
                        symbol='o',
                        symbolPen='orange',
                        symbolBrush='orange',
                        symbolSize=6
                    )

                    # Set up custom x-axis labels with time strings
                    # Show every nth label to avoid overcrowding
                    step = max(1, len(self.time_labels) // 10)
                    ticks = []
                    for i in range(0, len(self.time_labels), step):
                        ticks.append((i, self.time_labels[i]))

                    ax = self.plot_widget.getAxis('bottom')
                    ax.setTicks([ticks])

                    # Disable auto SI prefix and format as scientific notation
                    left_axis = self.plot_widget.getAxis('left')
                    left_axis.enableAutoSIPrefix(False)

                    # Override the tick string method to show scientific notation
                    class ScientificAxis(pg.AxisItem):
                        def tickStrings(self, values, scale, spacing):
                            return [f'{val:.1e}' for val in values]

                    # Replace the left axis
                    self.plot_widget.setAxisItems({'left': ScientificAxis(orientation='left')})

                    # Update window title and info
                    self.plot_widget.setTitle(f'Data from {file_path.split("/")[-1]}')
                    self.info_label.setText(
                        f"Loaded {len(self.pressure_data)} data points from {file_path.split('/')[-1]}")

                    # Set ranges
                    self.plot_widget.setXRange(0, len(self.time_data) - 1)
                    if self.pressure_data:
                        min_pressure = min(self.pressure_data)
                        max_pressure = max(self.pressure_data)
                        margin = (max_pressure - min_pressure) * 0.1
                        self.plot_widget.setYRange(min_pressure - margin, max_pressure + margin)
                else:
                    self.info_label.setText("No valid data found in CSV")

            except Exception as e:
                self.info_label.setText(f"Error loading CSV: {str(e)}")

    def mouse_clicked(self, event):
        """Show crosshair and values when user clicks on the plot"""
        # Only show crosshair if data has been loaded
        if not self.vLine or not self.hLine or not self.crosshair_label:
            return

        pos = event.scenePos()

        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()

            # Find nearest data point and display values
            if self.time_data and self.pressure_data:
                # Find the closest index
                closest_idx = min(range(len(self.time_data)),
                                  key=lambda i: abs(self.time_data[i] - x))

                if 0 <= closest_idx < len(self.time_data):
                    closest_x = self.time_data[closest_idx]
                    closest_pressure = self.pressure_data[closest_idx]
                    closest_time_label = self.time_labels[closest_idx]

                    # Update crosshair position to nearest point
                    self.vLine.setPos(closest_x)
                    self.hLine.setPos(closest_pressure)

                    # Update label text
                    self.crosshair_label.setText(
                        f"Pressure: {closest_pressure:.2e} Pa\nTime: {closest_time_label}"
                    )
                    self.crosshair_label.setPos(closest_x, closest_pressure)

                    # Show crosshair
                    self.vLine.setVisible(True)
                    self.hLine.setVisible(True)
                    self.crosshair_label.setVisible(True)
                    self.crosshair_visible = True


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())