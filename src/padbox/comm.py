from dataclasses import dataclass
from enum import auto, StrEnum
from typing import Callable

from serial import Serial
from serial.serialutil import SerialException


@dataclass
class BoxAction:
    name: str
    action: str
    args: str


class Action(StrEnum):
    SYSTEM = auto()
    KEY = auto()
    CONSUMER = auto()
    GOTO = auto()


class Box:
    def __init__(self, tty: str, configs: dict[str, list[BoxAction]], verbose: bool) -> None:
        self.serial = Serial(tty)
        self.configs = configs
        self.verbose = verbose
        self.titles = tuple(configs.keys())
        self.title_index = 0

    @property
    def title(self) -> str:
        return self.titles[self.title_index]

    def set_names(self) -> None:
        payload = f"\x01{self.title}\x02"
        for box_action in self.configs[self.title]:
            if box_action.action == Action.KEY.name:
                keys = "\x11".join(box_action.args.split(":"))
                payload += f"{box_action.name}\x11{keys}\x17"
            elif box_action.action == Action.CONSUMER.name:
                payload += f"{box_action.name}\x12{box_action.args}\x17"
            else:
                payload += f"{box_action.name}\x17"
        if self.verbose:
            print(f"sending payload {payload!r}")
        self.serial.write(payload.encode())

    def set_next_page(self) -> None:
        self.title_index += 1
        self.set_page()

    def set_previous_page(self) -> None:
        self.title_index -= 1
        self.set_page()

    def set_specific_page(self, page_title: str) -> None:
        self.title_index = self.titles.index(page_title)
        self.set_page()

    def set_page(self) -> None:
        self.title_index %= len(self.titles)
        self.set_names()

    def run(self, callback: Callable[[str, bytes, str], None], port: str) -> None:
        if self.verbose:
            print(f"Starting new Box control at port {port}")
        self.set_page()
        while True:
            try:
                key = self.serial.read(1)
            except (KeyboardInterrupt, SerialException):
                if self.verbose:
                    print(f"Broke")
                break
            if self.verbose:
                print(f"Gotten {key!r}")
            callback(self.title, key, port)
        self.exit()

    def exit(self) -> None:
        try:
            self.serial.write(b"\x18")
        except SerialException:
            if self.verbose:
                print("Unable to reset device, might be disconnected")
