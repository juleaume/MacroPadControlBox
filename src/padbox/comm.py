from pathlib import Path
from typing import Callable

from serial import Serial
from serial.serialutil import SerialException


class Box:
    def __init__(self, tty: str | Path, verbose: bool) -> None:
        self.serial = Serial(tty)
        self.verbose = verbose

    def set_names(self, title: str, *names: str) -> None:
        payload = ",".join((title, *names))
        if self.verbose:
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
                if self.verbose:
                    print(f"Key pressed: {int.from_bytes(key)}")

    def exit(self):
        try:
            self.serial.write(b"\x18")
        except SerialException:
            if self.verbose:
                print("Unable to reset device, might be disconnected")
