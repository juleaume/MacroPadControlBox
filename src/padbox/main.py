import json
import os
import shlex
import subprocess
import sys
import threading
import time

from .comm import Box


class Boxer:
    def __init__(self, tty: str, config_file: str, title: str, verbose: bool, no_stdout: bool, no_stderr: bool) -> None:
        self.box = Box(tty, verbose)
        with open(os.path.expanduser(config_file)) as j:
            self.configs = json.load(j)
        if title is None:
            title = list(self.configs.keys())[0]
        if title not in self.configs:
            raise ValueError("Title is not in config file")
        self.title = title
        self.config = self.configs.get(self.title)
        self.verbose = verbose
        self.supress_stdout = no_stdout
        self.supress_stderr = no_stderr

    def run(self) -> int:
        keys = self.config.get("keys")
        self.box.set_names(self.title, *keys)
        try:
            self.box.run(self.callback)
        finally:
            self.box.exit()
        time.sleep(0.1)
        del self.box
        return 0

    def callback(self, key: bytes) -> None:
        key_index = int.from_bytes(key)
        action = self.config["actions"][key_index]
        value = self.config["values"][key_index]
        if self.verbose:
            print(f"Key pressed: {self.config["keys"][key_index]} " f"-> setting {action}({value})")
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
