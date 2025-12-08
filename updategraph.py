import csv
import sys
from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import QLabel, QLineEdit

import dynamic_data


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, csv_file="pressure_test_data.csv"):
        super().__init__()

        self.setWindowTitle("PyQtGraph Dynamic Graph")
        self.resize(800, 600)  # Set window size
        self.csv_file = csv_file
        self.last_row_count = 0

        # QProcess for running data collection script
        self.process = QProcess(self)

        # Create central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Create horizontal layouts
        input_layout = QtWidgets.QHBoxLayout()
        buttons_layout = QtWidgets.QHBoxLayout()

        # Add label and line edit
        self.label1 = QLabel("Data file name:")
        input_layout.addWidget(self.label1)

        self.data_line_edit = QLineEdit()
        self.data_line_edit.setPlaceholderText("Enter data file name")
        input_layout.addWidget(self.data_line_edit)

        self.data_save_button = QtWidgets.QPushButton("Save Data File Name")
        self.data_save_button.clicked.connect(self.save_data_file_name)
        input_layout.addWidget(self.data_save_button)

        layout.addLayout(input_layout)

        # Add button
        self.collect_button = QtWidgets.QPushButton("Start Data Collection")
        self.collect_button.clicked.connect(self.run_data_collection)
        buttons_layout.addWidget(self.collect_button)

        # Stop button
        self.stop_button = QtWidgets.QPushButton("Stop Data Collection")
        self.stop_button.clicked.connect(self.stop_data_collection)
        self.stop_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_button)

        layout.addLayout(buttons_layout)

        # Pressure vs time dynamic plot
        self.plot_graph = pg.PlotWidget()
        layout.addWidget(self.plot_graph)
        self.plot_graph.setBackground("black")
        self.plot_graph.setTitle("DIGITEL SPCe (Live Pressure CSV Data)", color="w", size="20pt")
        styles = {"color": "white", "font-size": "14px"}
        self.plot_graph.setLabel("left", "Pressure (Pa)", **styles)
        self.plot_graph.setLabel("bottom", "Time (min)", **styles)
        self.plot_graph.addLegend()
        self.plot_graph.showGrid(x=True, y=True)
        #self.plot_graph.setYRange(20, 40)

        # Data storage - keeps ALL data
        self.time = []
        self.pressure = []
        self.time_labels = []

        # Get a line reference
        self.line = self.plot_graph.plot(
            self.time,
            self.pressure,
            name="Pressure",
            pen=pg.mkPen(color='orange', width=2)
        )

        # Load initial data from CSV
        #self.load_csv_data()

        # Add a timer to check for new data in CSV
        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)  # Check every 500ms
        self.timer.timeout.connect(self.update_plot)
        self.timer.start()

    def save_data_file_name(self):
        csv_file = self.data_line_edit.text()
        if csv_file:
            self.csv_file = csv_file
            print(f"CSV file set to: {csv_file}")

            # Clear existing data
            self.time = []
            self.pressure = []
            self.time_labels = []
            self.last_row_count = 0

            # Try to load the new file
            #self.load_csv_data()
        else:
            print("Please enter a filename")

    def run_data_collection(self):
        if self.process.state() == QProcess.NotRunning:
            self.process.start(sys.executable, ["dynamic_data.py", self.csv_file])
            self.collect_button.setEnabled(False)
            self.stop_button.setEnabled(True)

    def stop_data_collection(self):
        if self.process.state() == QProcess.Running:
            self.process.kill()
            self.collect_button.setEnabled(True)
            self.stop_button.setEnabled(False)

    def load_csv_data(self):
        """Load all data from CSV file"""
        try:
            with open(self.csv_file, 'r') as f:
                reader = csv.reader(f)
                next(reader)
                rows = list(reader)

                if rows:
                    # Read data assuming no header (just time, temperature columns)
                    for row in rows:
                        if len(row) >= 2:
                            try:
                                self.time.append(len(self.time))
                                self.pressure.append(float(row[0]))
                                self.time_labels.append(row[1])
                            except ValueError:
                                continue  # Skip rows with invalid data

                    self.last_row_count = len(rows)

                    if self.time and self.pressure:
                        self.line.setData(self.time, self.pressure)
                        # Auto-adjust x-axis range to show all data
                        self.plot_graph.setXRange(min(self.time), max(self.time))
                        # Set up custom x-axis labels with time strings
                        # Show every nth label to avoid overcrowding
                        step = max(1, len(self.time_labels) // 10)
                        ticks = []
                        for i in range(0, len(self.time_labels), step):
                            ticks.append((i, self.time_labels[i]))

                        ax = self.plot_graph.getAxis('bottom')
                        ax.setTicks([ticks])

                        # Disable auto SI prefix and format as scientific notation
                        left_axis = self.plot_graph.getAxis('left')
                        left_axis.enableAutoSIPrefix(False)

                        # Override the tick string method to show scientific notation
                        class ScientificAxis(pg.AxisItem):
                            def tickStrings(self, values, scale, spacing):
                                return [f'{val:.1e}' for val in values]

                        # Replace the left axis
                        self.plot_graph.setAxisItems({'left': ScientificAxis(orientation='left')})
                        print(f"Loaded {len(self.time)} data points from CSV")

                        # Set ranges
                        self.plot_graph.setXRange(0, len(self.time) - 1)
                        if self.pressure:
                            min_pressure = min(self.pressure)
                            max_pressure = max(self.pressure)
                            margin = (max_pressure - min_pressure) * 0.1
                            self.plot_graph.setYRange(min_pressure - margin, max_pressure + margin)
        except FileNotFoundError:
            print(f"CSV file '{self.csv_file}' not found")
        except Exception as e:
            print(f"Error loading CSV: {e}")

    def update_plot(self):
        """Check for new data in CSV and update plot"""
        try:
            with open(self.csv_file, 'r') as f:
                reader = csv.reader(f)
                try:
                    next(reader) # Skip header
                except StopIteration:
                    return # File is empty

                rows = list(reader)

                # Skip if no data rows
                if not rows:
                    return

                current_row_count = len(rows)

                # Only update if new rows were added
                if current_row_count > self.last_row_count:
                    # Get only the new rows
                    new_rows = rows[self.last_row_count:]

                    for row in new_rows:
                        if len(row) >= 2:
                            try:
                                self.time.append(len(self.time))
                                self.pressure.append(float(row[0]))
                                self.time_labels.append(row[1])
                            except ValueError:
                                continue  # Skip rows with invalid data

                    self.last_row_count = current_row_count

                    # Update the plot with ALL data (old + new)
                    self.line.setData(self.time, self.pressure)
                    step = max(1, len(self.time_labels) // 10)
                    ticks = []
                    for i in range(0, len(self.time_labels), step):
                        ticks.append((i, self.time_labels[i]))

                    ax = self.plot_graph.getAxis('bottom')
                    ax.setTicks([ticks])

                    # Auto-adjust x-axis range to show all data
                    #if self.time:
                    #    self.plot_graph.setXRange(min(self.time), max(self.time))

                    print(f"Updated plot: Total data points = {len(self.time)}")
                    # Set ranges
                    #self.plot_graph.setXRange(0, len(self.time) - 1)
                    # if self.pressure:
                    #     min_pressure = min(self.pressure)
                    #     max_pressure = max(self.pressure)
                    #     margin = (max_pressure - min_pressure) * 0.1
                    #     self.plot_graph.setYRange(min_pressure - margin, max_pressure + margin)

        except FileNotFoundError:
            #print(f"CSV file '{self.csv_file}' not found")
            pass
        except Exception as e:
            pass
            #print(f"Error updating plot: {e}")

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    main = MainWindow("pressure_test_data.csv")
    main.show()
    app.exec()