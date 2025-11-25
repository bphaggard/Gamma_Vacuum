import csv
import os
import time
import serial


class SPCe:
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
        return f"~ {self.addr:02X} {cmd:02X} {data}\r".encode("ascii")

    def send(self, cmd: int, data: str = "00") -> str:
        packet = self._build_cmd(cmd, data)
        self.ser.reset_input_buffer()
        self.ser.write(packet)
        resp = self.ser.read_until(b"\r").decode("ascii", errors="ignore").strip()
        return resp

    def get_model(self) -> str:
        # command 0x01 = GET CONTROLLER MODEL
        resp = self.send(0x01)
        # e.g.: "05 OK 00 DIGITEL SPCe 4C"
        parts = resp.split()
        return " ".join(parts[3:-1]) if len(parts) >= 4 else resp

    def get_pressure(self):
        resp = self.send(0x0B)
        pressure_resp = resp[9:17]
        return pressure_resp

    def save_to_csv(self, filename):
        try:
            while True:
                file_exists = os.path.exists(filename)
                pressure = self.get_pressure()
                fields = ["pressure", "time"]

                record = {
                    "pressure": pressure,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                with open(filename, "a", newline="", encoding="utf-8") as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fields)
                    if not file_exists or os.path.getsize(filename) == 0:
                        writer.writeheader()
                    writer.writerow(record)
                time.sleep(0.5)

        except KeyboardInterrupt:
            print("User stopped script")
        except Exception as e:
            print("Error:", e)

    def close(self):
        self.ser.close()

if __name__ == "__main__":
    spce = SPCe("COM5", addr=0x05, baud=9600)
    print("RAW:", spce.send(0x01))
    print("Model:", spce.get_model())
    print("Pressure:", spce.get_pressure())
    spce.save_to_csv(filename="spce_pressure.csv")
    spce.close()