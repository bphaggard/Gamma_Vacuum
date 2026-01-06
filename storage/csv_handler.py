"""
Ukládání a načítání dat z CSV
"""
import csv
import os
from datetime import datetime
from typing import List, Tuple, Optional
from hardware.spce import SPCe
from config import DEFAULT_PORT, DEFAULT_ADDR, DEFAULT_BAUD


class CSVHandler:
    """Správa CSV souborů s tlakovými daty"""

    def __init__(self, filename: str):
        self.filename = filename
        self.fields = ["pressure", "time"]

        # ✅ Vytvoř adresář při inicializaci
        os.makedirs(os.path.dirname(filename), exist_ok=True)

    def save_record(self):
        """Uloží jeden záznam do CSV"""
        file_exists = os.path.exists(self.filename)
        spce = SPCe(DEFAULT_PORT, DEFAULT_ADDR, DEFAULT_BAUD)
        pressure = spce.get_pressure()

        record = {
            "pressure": pressure,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(self.filename, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fields)
            if not file_exists or os.path.getsize(self.filename) == 0:
                writer.writeheader()
            writer.writerow(record)

    def load_data(self) -> Tuple[List[float], List[float], List[str]]:
        """
        Načte data z CSV

        Returns:
            (timestamps, pressures, time_strings)
        """
        timestamps = []
        pressures = []
        time_strings = []

        if not os.path.exists(self.filename):
            return timestamps, pressures, time_strings

        try:
            with open(self.filename, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        time_str = row["time"]
                        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                        timestamp = dt.timestamp()

                        timestamps.append(timestamp)
                        pressures.append(float(row["pressure"].strip()))
                        time_strings.append(time_str)
                    except (ValueError, KeyError) as e:
                        print(f"Skipping invalid row: {row} | Error: {e}")
                        continue

        except Exception as e:
            print(f"Error loading CSV: {e}")

        return timestamps, pressures, time_strings

    def get_stats(self, pressures: List[float]) -> Optional[dict]:
        """Vrátí statistiky dat"""
        if not pressures:
            return None

        return {
            'min': min(pressures),
            'max': max(pressures),
            'avg': sum(pressures) / len(pressures),
            'count': len(pressures)
        }