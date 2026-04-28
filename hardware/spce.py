"""
Komunikace s DIGITEL SPCe
"""
import re
import serial


class SPCe:
    """Rozhraní pro DIGITEL SPCe Controller"""

    # Regex pro vědeckou notaci nebo desetinné číslo
    _PRESSURE_RE = re.compile(r'[+-]?\d+\.?\d*[eE][+-]?\d+|[+-]?\d+\.\d+')

    def __init__(self, port: str, addr: int = 0x05, baud: int = 9600):
        self.addr = addr
        self.port = port
        self.ser = serial.Serial(
            port=port,
            baudrate=baud,
            timeout=0.5,
            parity=serial.PARITY_NONE,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
        )

    def _build_cmd(self, cmd: int, data: str = "00") -> bytes:
        """Sestaví příkaz pro SPCe"""
        return f"~ {self.addr:02X} {cmd:02X} {data}\r".encode("ascii")

    def send(self, cmd: int, data: str = "00") -> str:
        """
        Pošle příkaz a vrátí odpověď.
        Raises:
            ConnectionError - port není otevřen
            TimeoutError    - žádná odpověď ve stanoveném timeoutu
        """
        if not self.ser or not self.ser.is_open:
            raise ConnectionError(f"Serial port {self.port} is not open")

        packet = self._build_cmd(cmd, data)
        try:
            self.ser.reset_input_buffer()
            self.ser.write(packet)
            resp = self.ser.read_until(b"\r").decode("ascii", errors="ignore").strip()
        except serial.SerialException as e:
            # Zařízení odpojeno za běhu apod.
            raise ConnectionError(f"Serial communication failed: {e}") from e

        if not resp:
            raise TimeoutError("No response from SPCe within timeout")
        return resp

    def get_model(self) -> str:
        """Vrátí model controlleru"""
        resp = self.send(0x01)
        parts = resp.split()
        return " ".join(parts[3:-1]) if len(parts) >= 4 else resp

    def get_pressure(self) -> float:
        """
        Vrátí aktuální tlak v Pa jako float.

        Robustně parsuje odpověď regexem místo pevného slicování,
        které selhalo u jakékoliv změny délky odpovědi.
        Raises:
            ValueError     - odpověď neobsahuje validní číslo
            TimeoutError   - propaguje z send()
            ConnectionError - propaguje z send()
        """
        resp = self.send(0x0B)
        match = self._PRESSURE_RE.search(resp)
        if not match:
            raise ValueError(f"Cannot parse pressure from response: {resp!r}")
        try:
            return float(match.group())
        except ValueError as e:
            raise ValueError(f"Invalid pressure value in {resp!r}: {e}") from e

    def get_voltage(self) -> int:
        """
        Vrátí aktuální HV napětí ve voltech (formát odpovědi xxxx).
        Když je HV vypnuté, vrací typicky 0; při běhu řádově kV.
        Raises:
            ValueError - odpověď neobsahuje validní 4-ciferné číslo
            TimeoutError - propaguje z send()
            ConnectionError - propaguje z send()
        """
        resp = self.send(0x0C)
        # 4 číslice — addr je 2 číslice, cmd 0C má písmeno, takže
        # první match \b\d{4}\b spolehlivě padne na hodnotu.

        match = re.search(r'\b\d{4}\b', resp)
        if not match:
            raise ValueError(f"Cannot parse voltage from response: {resp!r}")
        return int(match.group())

    def is_hv_on(self) -> bool:
        """
        Vrátí True pokud je HV zapnuté.
        Používá dedikovaný status příkaz 0x61 — odpověď obsahuje
        token "YES" (zapnuté) nebo "NO" (vypnuté).
        Raises:
            ValueError - odpověď neobsahuje YES/NO
            TimeoutError - propaguje z send()
            ConnectionError - propaguje z send()
        """
        resp = self.send(0x61)
        tokens = resp.upper().split()
        if "YES" in tokens:
            return True
        if "NO" in tokens:
            return False

    def is_connected(self) -> bool:
        """Zkontroluje připojení (best-effort, nikdy nevyhazuje)"""
        try:
            response = self.send(0x01)
            return "DIGITEL SPCe" in response
        except Exception:
            return False

    def close(self):
        """Bezpečně uzavře sériové spojení"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass

    # Context manager pro pohodlné použití
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()