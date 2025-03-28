from pathlib import Path
from typing import Callable

from serial import Serial
from serial.serialutil import SerialException


class Box:
    def __init__(self, tty: str | Path, configs: dict[str, list[str]], verbose: bool) -> None:
        self.serial = Serial(tty)
        self.configs = configs
        self.verbose = verbose
        self.titles = tuple(configs.keys())
        self.title_index = 0

    @property
    def title(self) -> str:
        return self.titles[self.title_index]

    def set_names(self) -> None:
        payload = "\x05" + ",".join((self.title, *self.configs[self.title]))
        if self.verbose:
            print(f"sending payload {payload}")
        self.serial.write(payload.encode())

    def set_next_page(self) -> None:
        self.title_index += 1
        self.set_page()

    def set_previous_page(self) -> None:
        self.title_index -= 1
        self.set_page()

    def set_page(self) -> None:
        self.title_index %= len(self.titles)
        self.set_names()

    def run(self, callback: Callable[[str, bytes], ...] | None) -> bool:
        while True:
            try:
                key = self.serial.read(1)
            except KeyboardInterrupt:
                return True
            except SerialException:
                return False
            if key == b">":
                self.set_next_page()
            elif key == b"<":
                self.set_previous_page()
            elif key == b".":
                self.title_index = 0
                self.set_names()
            elif callback is not None:
                callback(self.title, key)
            else:
                if self.verbose:
                    print(f"Key pressed: {int.from_bytes(key)}")
        return False

    def exit(self):
        try:
            self.serial.write(b"\x18")
        except SerialException:
            if self.verbose:
                print("Unable to reset device, might be disconnected")
