import json
import os
import threading
import time

import pyudev  # type: ignore[import-untyped]
from pyudev import Device
from serial.serialutil import SerialException

from .actions import PyCharm, System
from .comm import Box, BoxAction, Action

MACROPAD_PID = "8108"
MACROPAD_VID = "239a"


class Boxer:
    def __init__(self, config_file: str, verbose: bool, no_stdout: bool, no_stderr: bool) -> None:
        self.verbose = verbose
        self.supress_stdout = no_stdout
        self.supress_stderr = no_stderr
        self.context = pyudev.Context()
        self.boxes: dict[str, Box] = dict()
        self.known_ports = list()
        for dev in self.context.list_devices(subsystem="tty", ID_VENDOR_ID=MACROPAD_VID):
            self.known_ports.append(dev.device_node)
            if self.verbose:
                print(f"Device detected: {dev.device_node}")
        else:
            if self.verbose:
                print("No device detected")
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem="tty")

        with open(os.path.expanduser(config_file)) as j:
            configs = json.load(j)

        self.configs = {title: [BoxAction(**box_action) for box_action in config] for title, config in configs.items()}
        self._start_observer()
        self.system = System()
        self.extensions = {"PyCharm": PyCharm()}

    def _start_observer(self) -> None:
        self._observer = pyudev.MonitorObserver(self.monitor, self.event_handler)
        self._observer.start()

    def event_handler(self, action: str, device: Device) -> None:
        if action == "add":
            print("Device detected", device)
            self.known_ports.append(device.device_node)
        elif action == "remove":
            print("Device removed", device)
            self.known_ports.remove(device.device_node)
            del self.boxes[device.device_node]

    def run(self) -> int:
        while True:
            try:
                for port in self.known_ports:
                    if port in self.boxes.keys():
                        time.sleep(0.1)
                        continue
                    try:
                        box = self.boxes[port] = Box(port, self.configs, self.verbose)
                    except SerialException:
                        continue
                    threading.Thread(target=box.run, args=[self.callback, port], daemon=True).start()
                    time.sleep(0.1)
                time.sleep(0.5)
            except (KeyboardInterrupt, EOFError, RuntimeError):
                for box in self.boxes.values():
                    if box is not None:
                        box.exit()
                return 0

    def callback(self, title: str, key: bytes, port: str) -> None:
        key_index = int.from_bytes(key)
        page = self.configs[title]
        if key_index >= len(page):
            print(f"Error, key not attributed: {key_index}")
            return
        action = page[key_index].action
        arguments = page[key_index].args
        if action == Action.SYSTEM.name:
            self.system.callback(arguments, self.supress_stdout, self.supress_stderr, self.verbose)
        elif action == Action.GOTO.name:
            self.boxes[port].set_specific_page(arguments)
        elif action == Action.KEY.name or action == Action.CONSUMER.name:
            if self.verbose:
                print("Key or consumer handled on device side")
        elif action in self.extensions.keys():
            self.extensions[action].callback(arguments, self.supress_stdout, self.supress_stderr, self.verbose)
        else:
            if self.verbose:
                print(f"Unknown action: {action}")
            return
