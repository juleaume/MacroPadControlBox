import argparse
import sys

from .main import Boxer

parser = argparse.ArgumentParser()
parser.add_argument("--config-file", "-c", help="Path of the config file", default="~/.local/share/padbox.json")
parser.add_argument("--verbose", "-v", help="print verbose", action="store_true")
parser.add_argument("--no-stdout", "-O", help="don't suppress stdout of subprocesses", action="store_false")
parser.add_argument("--no-stderr", "-E", help="don't suppress stderr of subprocesses", action="store_false")


def main():
    args = parser.parse_args()
    b = Boxer(**vars(args))
    sys.exit(b.run())


if __name__ == '__main__':
    main()