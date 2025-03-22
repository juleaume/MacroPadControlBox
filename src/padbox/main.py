import argparse
import json
import os
import shlex
import subprocess
import sys
import time

from comm import Box


class Boxer:
    def __init__(self, tty: str, config_file: str, title: str, verbose: bool, no_stdout: bool, no_stderr: bool) -> None:
        self.box = Box(tty, verbose)
        with open(os.path.expanduser(config_file)) as j:
            self.configs = json.load(j)
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
            subprocess.run(
                shlex.split(f"{action} {value}"),
                stdout=subprocess.DEVNULL if self.supress_stdout else sys.stdout,
                stderr=subprocess.DEVNULL if self.supress_stderr else sys.stderr,
            )
        except FileNotFoundError as e:
            if self.verbose:
                print(f"Error, no such program or file: {e}")


if __name__ == "__main__":
    ttys = [f"/dev/{_d}" for _d in os.listdir("/dev") if _d.startswith("ttyACM")]
    if not ttys:
        print("No device detected")
        sys.exit(1)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tty",
        "-p",
        help="TTY path of your device",
        choices=ttys,
        default=ttys[0] if len(ttys) == 1 else None,
    )
    parser.add_argument("--config-file", "-c", help="Path of the config file")
    parser.add_argument("--title", "-t", help="Title of the config to use")
    parser.add_argument("--verbose", "-v", help="print verbose", action="store_true")
    parser.add_argument("--no-stdout", "-O", help="don't suppress stdout of subprocesses", action="store_false")
    parser.add_argument("--no-stderr", "-E", help="don't suppress stderr of subprocesses", action="store_false")
    args = parser.parse_args()
    b = Boxer(**vars(args))
    sys.exit(b.run())
