import subprocess
import sys
import base64
import time
import shlex
import os
from datetime import datetime
from config import CONTAINER_NAME, IMAGE_NAME, DISPLAY, VNC_PORT
SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

from config import CONTAINER_NAME, DISPLAY

def docker_exec(cmd: str, decode: bool = True):
    result = subprocess.run(
        ["docker", "exec", CONTAINER_NAME, "bash", "-c", cmd],
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        print(f"[docker] command failed: {cmd}\n  stderr: {stderr}", file=sys.stderr)
    if decode:
        return result.stdout.decode("utf-8", errors="replace")
    return result.stdout


def capture_screenshot(step: int = 0):
    png_bytes = docker_exec(
        f"DISPLAY={DISPLAY} import -window root png:-",
        decode=False,
    )
    if not png_bytes:
        print("[screenshot] Warning: empty screenshot.", file=sys.stderr)
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SCREENSHOT_DIR}/step_{step:03d}_{timestamp}.png"

    with open(filename, "wb") as f:
        f.write(png_bytes)
    print(f"[screenshot] Saved: {filename}")

    return base64.b64encode(png_bytes).decode("utf-8")

KEY_MAP = {
    "enter": "Return",
    "return": "Return",
    "tab": "Tab",
    "space": "space",
    "backspace": "BackSpace",
    "delete": "Delete",
    "escape": "Escape",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "pagedown": "Next",
    "ctrl": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "super": "super",
    "f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4",
    "f5": "F5", "f6": "F6", "f7": "F7", "f8": "F8",
    "f9": "F9", "f10": "F10", "f11": "F11", "f12": "F12",
}



def handle_actions(actions):
    for action in actions:
        action_type = action.type
        print(f"  [action] {action_type}", end="")

        if action_type == "click":
            x, y = action.x, action.y
            button = getattr(action, "button", "left")
            btn_num = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
            print(f" @ ({x}, {y}) button={button}")
            docker_exec(f"DISPLAY={DISPLAY} xdotool mousemove {x} {y} click {btn_num}")

        elif action_type == "double_click":
            x, y = action.x, action.y
            print(f" @ ({x}, {y})")
            docker_exec(
                f"DISPLAY={DISPLAY} xdotool mousemove {x} {y} click --repeat 2 --delay 100 1"
            )

        elif action_type == "type":
            text = action.text
            print(f" text={text!r}")
            safe_text = shlex.quote(text)
            docker_exec(f"DISPLAY={DISPLAY} xdotool type --clearmodifiers --delay 0 {safe_text}")

        elif action_type == "keypress":
            keys = action.keys
            mapped = [KEY_MAP.get(k.lower(), k) for k in keys]
            combo = "+".join(mapped)
            print(f" keys={combo}")
            docker_exec(f"DISPLAY={DISPLAY} xdotool key --clearmodifiers {combo}")

        elif action_type == "scroll":
            x, y = action.x, action.y
            scroll_y = getattr(action, "scrollY", 0)
            btn = "4" if scroll_y < 0 else "5"
            clicks = max(1, abs(round(scroll_y / 100)))
            print(f" @ ({x}, {y}) scrollY={scroll_y}")
            docker_exec(f"DISPLAY={DISPLAY} xdotool mousemove {x} {y}")
            for _ in range(clicks):
                docker_exec(f"DISPLAY={DISPLAY} xdotool click {btn}")

        elif action_type == "drag":
            path = action.path
            if len(path) >= 2:
                start = path[0]
                end = path[-1]
                print(f" from ({start['x']}, {start['y']}) to ({end['x']}, {end['y']})")
                docker_exec(
                    f"DISPLAY={DISPLAY} xdotool mousemove {start['x']} {start['y']} "
                    f"mousedown 1 mousemove {end['x']} {end['y']} mouseup 1"
                )

        elif action_type == "move":
            x, y = action.x, action.y
            print(f" @ ({x}, {y})")
            docker_exec(f"DISPLAY={DISPLAY} xdotool mousemove {x} {y}")

        elif action_type == "screenshot":
            print(" (will capture after all actions)")

        elif action_type == "wait":
            ms = getattr(action, "ms", 2000)
            secs = ms / 1000
            print(f" {secs}s")
            time.sleep(secs)

        else:
            print(f" (unknown: {action_type})")


def start_container():
    check = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME],
        capture_output=True, text=True,
    )
    if check.returncode == 0 and check.stdout.strip() == "true":
        print(f"[container] {CONTAINER_NAME} already running.")
        return

    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)

    print(f"[container] Starting {CONTAINER_NAME} ...")
    subprocess.run([
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "-p", f"{VNC_PORT}:{VNC_PORT}",
        IMAGE_NAME,
    ], check=True)

    print("[container] Waiting for desktop ...")
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
        print("[container] Warning: desktop may not be fully ready.", file=sys.stderr)

    print(f"[container] Ready. VNC -> localhost:{VNC_PORT}")


def stop_container():
    print(f"[container] Stopping {CONTAINER_NAME} ...")
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    print("[container] Stopped.")