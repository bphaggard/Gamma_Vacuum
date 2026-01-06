"""
Komunikace s DIGITEL SPCe
"""
import serial

class SPCe:
    """Rozhraní pro DIGITEL SPCe Controller"""

    def __init__(self, port: str, addr: int = 0x05, baud: int = 9600):
        self.addr = addr
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
        """Pošle příkaz a vrátí odpověď"""
        packet = self._build_cmd(cmd, data)
        self.ser.reset_input_buffer()
        self.ser.write(packet)
        resp = self.ser.read_until(b"\r").decode("ascii", errors="ignore").strip()
        return resp

    def get_model(self) -> str:
        """Vrátí model controlleru"""
        resp = self.send(0x01)
        parts = resp.split()
        return " ".join(parts[3:-1]) if len(parts) >= 4 else resp

    def get_pressure(self) -> str:
        """Vrátí aktuální tlak"""
        resp = self.send(0x0B)
        return resp[9:16]

    def is_connected(self) -> bool:
        """Zkontroluje připojení"""
        try:
            response = self.send(0x01)
            return "DIGITEL SPCe" in response
        except Exception:
            return False

    def close(self):
        """Uzavře sériové spojení"""
        if self.ser.is_open:
            self.ser.close()