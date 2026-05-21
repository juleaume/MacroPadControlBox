import subprocess
import sys
import threading
from abc import ABCMeta, abstractmethod
import shlex
from typing import Any

import requests


class Action(metaclass=ABCMeta):
    @abstractmethod
    def callback(self, *args: Any, **kwargs: Any) -> None: ...


class System(Action):
    def callback(self, args: str, supress_stdout: bool, supress_stderr: bool, verbose: bool) -> None:
        try:
            threading.Thread(
                target=subprocess.run,
                args=[shlex.split(args)],
                kwargs={
                    "stdout": subprocess.DEVNULL if supress_stdout else sys.stdout,
                    "stderr": subprocess.DEVNULL if supress_stderr else sys.stderr,
                },
                daemon=True,
            ).start()
        except FileNotFoundError as e:
            if verbose:
                print(f"Error, no such program or file: {e}")


class PyCharm(Action):
    def __init__(self) -> None:
        self._hostname = "localhost"
        self.session = requests.Session()
        self._port = self._find_port()

    def call(
        self,
        endpoint: str,
        *,
        port: int | None = None,
    ) -> str:
        return f"http://{self._hostname}:{port or self._port}/api/action/{endpoint}"

    def _find_port(self) -> int:
        for i in range(63342, 63352, 1):
            try:
                self.session.get(self.call("", port=i))
                return i
            except requests.exceptions.ConnectionError:
                continue
        raise RuntimeError("No port found")

    def callback(self, endpoint: str, supress_stdout: bool, supress_stderr: bool, verbose: bool) -> None:
        try:
            self.session.get(self.call(endpoint))
        except requests.exceptions.ConnectionError:
            if verbose and not supress_stderr:
                print(f"Error while calling endpoint {endpoint}", file=sys.stderr)
