import subprocess
import sys
import time

from runtime import Runtime
from config import CONTAINER_NAME, IMAGE_NAME, DISPLAY, VNC_PORT


class DockerRuntime(Runtime):
    """Run commands via docker exec."""

    def exec(self, cmd: str, decode: bool = True):
        result = subprocess.run(
            ["docker", "exec", CONTAINER_NAME, "bash", "-c", cmd],
            capture_output=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            print(f"  [error] command failed: {cmd}\n           {stderr}", file=sys.stderr)
            return None if decode else b""
        if decode:
            return result.stdout.decode("utf-8", errors="replace")
        return result.stdout

    def start(self):
        check = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
            capture_output=True, text=True,
        )
        if check.returncode == 0 and check.stdout.strip() == "true":
            print(f"[startup] Container {CONTAINER_NAME} already running.")
            return

        subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)

        print(f"[startup] Starting {CONTAINER_NAME} ...")
        subprocess.run([
            "docker", "run", "-d",
            "--name", CONTAINER_NAME,
            "-p", f"{VNC_PORT}:{VNC_PORT}",
            IMAGE_NAME,
        ], check=True)

        print("[startup] Waiting for desktop ...")
        for _ in range(30):
            probe = subprocess.run(
                ["docker", "exec", CONTAINER_NAME, "bash", "-c",
                 f"DISPLAY={DISPLAY} xdotool getactivewindow"],
                capture_output=True,
            )
            if probe.returncode == 0:
                break
            time.sleep(1)
        else:
            print("[startup] Warning: desktop may not be fully ready.", file=sys.stderr)

        print(f"[startup] Ready. VNC -> localhost:{VNC_PORT}")

    def stop(self):
        print(f"\n[cleanup] Stopping {CONTAINER_NAME} ...")
        subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
        print("[cleanup] Stopped.")