from pathlib import Path
from typing import Callable

from serial import Serial
from serial.serialutil import SerialException


class Box:
    def __init__(self, tty: str | Path) -> None:
        self.serial = Serial(tty)

    def set_names(self, title: str, *names: str) -> None:
        payload = ",".join((title, *names))
        print(f"sending payload {payload}")
        self.serial.write(payload.encode())

    def run(self, callback: Callable[[bytes], ...] | None) -> None:
        while True:
            try:
                key = self.serial.read(1)
            except (KeyboardInterrupt, SerialException):
                return
            if callback is not None:
                callback(key)
            else:
                print(f"Key pressed: {int.from_bytes(key)}")

    def exit(self):
        try:
            self.serial.write(b"\x18")
        except SerialException:
            print("Unable to reset device, might be disconnected")
