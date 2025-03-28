import json
import os
import shlex
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

import pyudev
from pyudev import Device
from serial.serialutil import SerialException

from .comm import Box

MACROPAD_PID = "8108"
MACROPAD_VID = "239a"


@dataclass
class BoxAction:
    name: str
    action: str
    args: str


class Boxer:
    def __init__(self, config_file: str, verbose: bool, no_stdout: bool, no_stderr: bool) -> None:
        self.verbose = verbose
        self.supress_stdout = no_stdout
        self.supress_stderr = no_stderr
        self.context = pyudev.Context()
        for dev in self.context.list_devices(subsystem="tty", ID_VENDOR_ID=MACROPAD_VID):
            self.port = dev.device_node
            if self.verbose:
                print("Device detected")
            break
        else:
            if self.verbose:
                print("No device detected")
            self.port = None
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem="tty")

        with open(os.path.expanduser(config_file)) as j:
            configs = json.load(j)

        self.configs = {title: [BoxAction(**box_action) for box_action in config] for title, config in configs.items()}
        self._start_observer()

    def _start_observer(self) -> None:
        self._observer = pyudev.MonitorObserver(self.monitor, self.event_handler)
        self._observer.start()

    def event_handler(self, action: str, device: Device) -> None:
        if action == "add":
            print("Device detected", device)
            self.port = device.device_node
            self._observer.stop()
        elif action == "remove":
            print("Device removed", device)
            self.port = None
            self._start_observer()

    def run(self) -> int:
        keys = {title: [box_action.name for box_action in config] for title, config in self.configs.items()}
        while True:
            if self.port is None:
                time.sleep(0.1)
                continue
            try:
                box = Box(self.port, keys, self.verbose)
            except SerialException:
                continue
            box.set_page()
            try:
                exit_normally = box.run(self.callback)
            finally:
                box.exit()
            time.sleep(0.1)
            del box
            if exit_normally:
                break

    def callback(self, title: str, key: bytes) -> None:
        key_index = int.from_bytes(key)
        page = self.configs[title]
        if key_index >= len(page):
            print(f"Error, key not attributed: {key}")
            return
        action = page[key_index].action
        value = page[key_index].args
        if self.verbose:
            print(f"Key {key_index} pressed: {page[key_index].name} " f"-> setting {action}({value})")
        try:
            threading.Thread(
                target=subprocess.run,
                args=[shlex.split(f"{action} {value}")],
                kwargs={
                    "stdout": subprocess.DEVNULL if self.supress_stdout else sys.stdout,
                    "stderr": subprocess.DEVNULL if self.supress_stderr else sys.stderr,
                },
                daemon=True,
            ).start()
        except FileNotFoundError as e:
            if self.verbose:
                print(f"Error, no such program or file: {e}")
