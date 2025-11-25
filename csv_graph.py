import csv
import sys
import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QFileDialog, QLabel)


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

    def load_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            try:
                time_data = []
                pressure_data = []
                time_labels = []

                with open(file_path, 'r') as file:
                    csv_reader = csv.reader(file)
                    headers = next(csv_reader)  # Read headers

                    for i, row in enumerate(csv_reader):
                        if len(row) >= 2:
                            try:
                                # Parse pressure
                                pressure = float(row[0])
                                pressure_data.append(pressure)

                                # Store time string for labels
                                time_labels.append(row[1])

                                # Use index for x-axis positioning
                                time_data.append(i)

                            except ValueError:
                                continue

                if time_data and pressure_data:
                    # Clear previous plot
                    self.plot_widget.clear()

                    # Plot the data
                    self.plot_widget.plot(
                        time_data,
                        pressure_data,
                        pen=pg.mkPen(color='g', width=2),
                        symbol='o',
                        symbolPen='g',
                        symbolBrush=(0, 255, 0, 100),
                        symbolSize=8,
                        name='Pressure'
                    )

                    # Set up custom x-axis labels with time strings
                    # Show every nth label to avoid overcrowding
                    step = max(1, len(time_labels) // 10)
                    ticks = []
                    for i in range(0, len(time_labels), step):
                        ticks.append((i, time_labels[i]))

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
                    self.info_label.setText(f"Loaded {len(pressure_data)} data points from {file_path.split('/')[-1]}")

                    # Set ranges
                    self.plot_widget.setXRange(0, len(time_data) - 1)
                    if pressure_data:
                        min_pressure = min(pressure_data)
                        max_pressure = max(pressure_data)
                        margin = (max_pressure - min_pressure) * 0.1
                        self.plot_widget.setYRange(min_pressure - margin, max_pressure + margin)
                else:
                    self.info_label.setText("No valid data found in CSV")

            except Exception as e:
                self.info_label.setText(f"Error loading CSV: {str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())