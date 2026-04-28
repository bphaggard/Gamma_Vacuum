"""
Worker pro měření tlaku v separátním vlákně.

Worker VLASTNÍ SPCe spojení — port se otevírá jednou (start) a zavírá jednou
(stop). Komunikace s GUI probíhá výhradně přes signály.
"""
from datetime import datetime
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from hardware.spce import SPCe


class PressureWorker(QObject):
    """
    Worker, který v samostatném vlákně:
      - drží SPCe spojení (jeden port otevřený celou dobu monitoringu)
      - každou sekundu načte tlak a zapíše záznam do CSV
      - emituje signály do GUI vlákna

    Signály:
        new_record(pressure: float, time_str: str) — nový měřený bod
        error(message: str)                        — recoverable chyba (timeout)
        connection_lost(message: str)              — fatální chyba; worker se sám zastaví
        started()                                  — port otevřen, měření běží
        stopped()                                  — port uzavřen, vlákno může končit
    """

    new_record = pyqtSignal(float, str)
    error = pyqtSignal(str)
    connection_lost = pyqtSignal(str)
    started = pyqtSignal()
    stopped = pyqtSignal()

    # Po kolika po sobě jdoucích timeoutech považujeme zařízení za odpojené
    MAX_CONSECUTIVE_TIMEOUTS = 5

    def __init__(self, port: str, addr: int, baud: int, csv_handler):
        super().__init__()
        self.port = port
        self.addr = addr
        self.baud = baud
        self.csv_handler = csv_handler

        self.spce = None
        self._timer = None
        self._consecutive_timeouts = 0
        self._stopped = False  # idempotence guard

    @pyqtSlot()
    def start(self):
        """
        Spuštěno z workerova threadu (signal thread.started → start).
        Otevře port a nastartuje periodické měření.
        """
        try:
            self.spce = SPCe(self.port, self.addr, self.baud)
            if not self.spce.is_connected():
                raise ConnectionError("SPCe controller did not respond on init")

            # Kontrola HV — když je vypnuté, monitoring nemá smysl spouštět
            if not self.spce.is_hv_on():
                self.connection_lost.emit(
                    "High voltage is OFF — turn on HV before starting monitoring."
                )
                self._cleanup_and_emit_stopped()
                return
        except Exception as e:
            # Fatal už při startu
            self.connection_lost.emit(f"Cannot connect to SPCe: {e}")
            self._cleanup_and_emit_stopped()
            return

        # Timer MUSÍ být vytvořený až tady (v cílovém threadu),
        # aby jeho timeout sloty běžely v workerově event loopu.
        self._timer = QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._measure)
        self._timer.start()

        self._consecutive_timeouts = 0
        self.started.emit()

    @pyqtSlot()
    def stop(self):
        """
        Zastaví měření a uzavře port.
        Idempotentní — bezpečné volat opakovaně.
        """
        self._cleanup_and_emit_stopped()

    def _cleanup_and_emit_stopped(self):
        if self._stopped:
            return
        self._stopped = True

        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None

        if self.spce is not None:
            self.spce.close()
            self.spce = None

        self.stopped.emit()

    def _measure(self):
        """Jeden měřicí tik. Běží v workerově threadu."""
        if self.spce is None:  # už jsme se zastavili
            return

        try:
            pressure = self.spce.get_pressure()
        except TimeoutError:
            self._consecutive_timeouts += 1
            if self._consecutive_timeouts >= self.MAX_CONSECUTIVE_TIMEOUTS:
                self.connection_lost.emit(
                    f"SPCe not responding ({self.MAX_CONSECUTIVE_TIMEOUTS} timeouts in a row)"
                )
                self._cleanup_and_emit_stopped()
            else:
                self.error.emit("Device not responding...")
            return
        except (ConnectionError, OSError) as e:
            # Hard fault — odpojený port, vypnuté zařízení atd.
            self.connection_lost.emit(f"SPCe disconnected: {e}")
            self._cleanup_and_emit_stopped()
            return
        except ValueError as e:
            # Nezvalidní odpověď — spíš jednorázová chyba; nereportujeme
            # to jako fatální, ale jako recoverable.
            self.error.emit(f"Bad response: {e}")
            return
        except Exception as e:
            self.connection_lost.emit(f"Unexpected error: {e}")
            self._cleanup_and_emit_stopped()
            return

        self._consecutive_timeouts = 0
        now = datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")

        try:
            self.csv_handler.append_record(pressure, when=now)
        except OSError as e:
            self.error.emit(f"CSV write failed: {e}")
            return

        self.new_record.emit(pressure, time_str)