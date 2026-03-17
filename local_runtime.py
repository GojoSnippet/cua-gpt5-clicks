import os
import subprocess
import sys

from runtime import Runtime
from config import DISPLAY


class LocalRuntime(Runtime):
    """Run commands locally via subprocess. Used inside the K8s pod."""

    def exec(self, cmd: str, decode: bool = True):
        result = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            env={**os.environ, "DISPLAY": DISPLAY},
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            print(f"  [error] command failed: {cmd}\n           {stderr}", file=sys.stderr)
            return None if decode else b""
        if decode:
            return result.stdout.decode("utf-8", errors="replace")
        return result.stdout

    def start(self):
        # desktop is already running via k8s/start.sh
        print("[startup] Running inside K8s pod. Desktop already up.")

    def stop(self):
        # nothing to stop — Job handles cleanup
        print("[cleanup] Running inside K8s pod. Job will clean up.")