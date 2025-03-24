import argparse
import os
import sys

from .main import Boxer

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
parser.add_argument("--config-file", "-c", help="Path of the config file", required=True)
parser.add_argument("--title", "-t", help="Title of the config to use")
parser.add_argument("--verbose", "-v", help="print verbose", action="store_true")
parser.add_argument("--no-stdout", "-O", help="don't suppress stdout of subprocesses", action="store_false")
parser.add_argument("--no-stderr", "-E", help="don't suppress stderr of subprocesses", action="store_false")


def main():
    args = parser.parse_args()
    b = Boxer(**vars(args))
    sys.exit(b.run())
