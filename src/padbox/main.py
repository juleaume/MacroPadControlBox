import argparse
import json
import os
import sys
import time

from comm import Box


class Boxer:
    def __init__(self, tty: str, config_file: str, title: str) -> None:
        self.box = Box(tty)
        with open(os.path.expanduser(config_file)) as j:
            self.configs = json.load(j)
        if title not in self.configs:
            raise ValueError("Title is not in config file")
        self.title = title
        self.config = self.configs.get(self.title)

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
        print(
            f"Key pressed: {self.config["keys"][key_index]} "
            f"-> setting {self.config["actions"][key_index]}({self.config["values"][key_index]})"
        )


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
    args = parser.parse_args()
    b = Boxer(**vars(args))
    sys.exit(b.run())
