"""
Ukládání a načítání dat z CSV.

Tento handler se stará POUZE o CSV. SPCe instanci vlastní worker thread
(viz worker_helper.py); tady jen appendujeme hodnoty, které dostaneme.
"""
import csv
import logging
import os
from datetime import datetime
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class CSVHandler:
    """Správa CSV souborů s tlakovými daty"""

    def __init__(self, filename: str):
        self.filename = filename
        self.fields = ["pressure", "time"]

        # Vytvoř adresář jen pokud cesta nějaký obsahuje
        # (jinak by makedirs("") spadlo)
        dir_part = os.path.dirname(filename)
        if dir_part:
            os.makedirs(dir_part, exist_ok=True)

    def append_record(self, pressure: float, when: Optional[datetime] = None):
        """
        Uloží jeden záznam do CSV.

        Args:
            pressure: tlak jako float (Pa)
            when: časová značka (default = now); předáme ji explicitně,
                  abychom v UI měli stejnou časovou značku jako v souboru.
        """
        if when is None:
            when = datetime.now()

        file_exists = os.path.exists(self.filename)
        is_empty = not file_exists or os.path.getsize(self.filename) == 0

        record = {
            "pressure": pressure,
            "time": when.strftime("%Y-%m-%d %H:%M:%S"),
        }

        with open(self.filename, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fields)
            if is_empty:
                writer.writeheader()
            writer.writerow(record)

    def load_data(self) -> Tuple[List[float], List[float], List[str]]:
        """
        Načte VŠECHNA data z CSV (full reload).

        Používá se jen pro úvodní načtení (recovery) nebo View Old Data.
        Při běžném monitoringu data v paměti udržuje GUI a jen appenduje
        nové body — soubor se nečte celý každou sekundu.

        Returns:
            (timestamps, pressures, time_strings)
        """
        timestamps: List[float] = []
        pressures: List[float] = []
        time_strings: List[str] = []

        if not os.path.exists(self.filename):
            return timestamps, pressures, time_strings

        try:
            with open(self.filename, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    parsed = self._parse_row(row)
                    if parsed is None:
                        continue
                    ts, p, s = parsed
                    timestamps.append(ts)
                    pressures.append(p)
                    time_strings.append(s)
        except OSError as e:
            logger.error("Error loading CSV %s: %s", self.filename, e, exc_info=True)

        return timestamps, pressures, time_strings

    @staticmethod
    def _parse_row(row: dict):
        """Zparsuje jeden řádek; vrací None pro nevalidní řádek."""
        try:
            time_str = row["time"]
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            timestamp = dt.timestamp()
            pressure = float(str(row["pressure"]).strip())
            return timestamp, pressure, time_str
        except (ValueError, KeyError, TypeError) as e:
            logger.warning("Skipping invalid CSV row: %r | %s", row, e)
            return None

    def get_stats(self, pressures: List[float]) -> Optional[dict]:
        """Vrátí základní statistiky"""
        if not pressures:
            return None
        return {
            "min": min(pressures),
            "max": max(pressures),
            "avg": sum(pressures) / len(pressures),
            "count": len(pressures),
        }

    def get_24h_stats(
        self, pressures: List[float], timestamps: List[float]
    ) -> Optional[dict]:
        """Vrátí statistiky za posledních 24 hodin"""
        if not pressures or not timestamps:
            return None

        last_time = timestamps[-1]
        cutoff = last_time - 24 * 3600

        filtered = [p for t, p in zip(timestamps, pressures) if t >= cutoff]
        if not filtered:
            return None

        avg = sum(filtered) / len(filtered)
        variance = sum((x - avg) ** 2 for x in filtered) / len(filtered)
        std = variance ** 0.5

        threshold_ref = 3.0e-05
        threshold_base = 2.0e-05

        return {
            "min": min(filtered),
            "max": max(filtered),
            "avg": avg,
            "std": std,
            "count": len(filtered),
            "above_reference": sum(1 for p in filtered if p > threshold_ref),
            "above_base": sum(1 for p in filtered if p > threshold_base),
        }
