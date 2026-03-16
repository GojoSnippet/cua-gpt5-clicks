import subprocess
import sys
import base64
import time
import shlex
import os
from datetime import datetime

from config import CONTAINER_NAME, IMAGE_NAME, DISPLAY, VNC_PORT

# ── Screenshot saving ────────────────────────────────────────

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ── Docker exec ──────────────────────────────────────────────

def docker_exec(cmd: str, decode: bool = True):
    """Run a command inside the Docker container."""
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


# ── Screenshot ───────────────────────────────────────────────

def capture_screenshot(step: int = 0):
    """Take a screenshot, save it locally, return as base64 string."""
    png_bytes = docker_exec(
        f"DISPLAY={DISPLAY} import -window root png:-",
        decode=False,
    )
    if not png_bytes:
        print("  [screenshot] Warning: empty screenshot.", file=sys.stderr)
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SCREENSHOT_DIR}/step_{step:03d}_{timestamp}.png"
    with open(filename, "wb") as f:
        f.write(png_bytes)
    print(f"  [screenshot] Saved: {filename}")

    return base64.b64encode(png_bytes).decode("utf-8")


# ── Key mapping ──────────────────────────────────────────────

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


# ── Action helpers ───────────────────────────────────────────

def describe_action(action):
    """Return a short description of an action for logging."""
    t = action.type
    if t == "click":
        button = getattr(action, "button", "left")
        return f"click     ({action.x}, {action.y}) button={button}"
    elif t == "double_click":
        return f"dbl_click ({action.x}, {action.y})"
    elif t == "type":
        return f'type      text="{action.text}"'
    elif t == "keypress":
        keys = action.keys
        mapped = [KEY_MAP.get(k.lower(), k) for k in keys]
        return f"keypress  keys={'+'.join(mapped)}"
    elif t == "scroll":
        scroll_y = getattr(action, "scrollY", 0)
        return f"scroll    ({action.x}, {action.y}) scrollY={scroll_y}"
    elif t == "drag":
        path = action.path
        if len(path) >= 2:
            return f"drag      ({path[0]['x']}, {path[0]['y']}) -> ({path[-1]['x']}, {path[-1]['y']})"
        return "drag"
    elif t == "move":
        return f"move      ({action.x}, {action.y})"
    elif t == "screenshot":
        return "screenshot"
    elif t == "wait":
        ms = getattr(action, "ms", 2000)
        return f"wait      {ms/1000}s"
    return f"unknown   ({t})"


def execute_action(action):
    """Execute a single action inside the container. Returns True if success."""
    t = action.type

    if t == "click":
        x, y = action.x, action.y
        button = getattr(action, "button", "left")
        btn_num = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
        result = docker_exec(f"DISPLAY={DISPLAY} xdotool mousemove {x} {y} click {btn_num}")
        return result is not None

    elif t == "double_click":
        x, y = action.x, action.y
        result = docker_exec(
            f"DISPLAY={DISPLAY} xdotool mousemove {x} {y} click --repeat 2 --delay 100 1"
        )
        return result is not None

    elif t == "type":
        safe_text = shlex.quote(action.text)
        result = docker_exec(
            f"DISPLAY={DISPLAY} xdotool type --clearmodifiers --delay 0 {safe_text}"
        )
        return result is not None

    elif t == "keypress":
        keys = action.keys
        mapped = [KEY_MAP.get(k.lower(), k) for k in keys]
        combo = "+".join(mapped)
        result = docker_exec(f"DISPLAY={DISPLAY} xdotool key --clearmodifiers {combo}")
        return result is not None

    elif t == "scroll":
        x, y = action.x, action.y
        scroll_y = getattr(action, "scrollY", 0)
        btn = "4" if scroll_y < 0 else "5"
        clicks = max(1, abs(round(scroll_y / 100)))
        docker_exec(f"DISPLAY={DISPLAY} xdotool mousemove {x} {y}")
        for _ in range(clicks):
            docker_exec(f"DISPLAY={DISPLAY} xdotool click {btn}")
        return True

    elif t == "drag":
        path = action.path
        if len(path) >= 2:
            start = path[0]
            end = path[-1]
            docker_exec(
                f"DISPLAY={DISPLAY} xdotool mousemove {start['x']} {start['y']} "
                f"mousedown 1 mousemove {end['x']} {end['y']} mouseup 1"
            )
        return True

    elif t == "move":
        result = docker_exec(f"DISPLAY={DISPLAY} xdotool mousemove {action.x} {action.y}")
        return result is not None

    elif t == "screenshot":
        return True  # handled in main loop

    elif t == "wait":
        ms = getattr(action, "ms", 2000)
        time.sleep(ms / 1000)
        return True

    return False


def handle_actions(actions):
    """Execute all actions and print formatted log."""
    print(f"\n  [gpt] Requested {len(actions)} action(s):")
    for i, action in enumerate(actions, 1):
        print(f"          {i}. {describe_action(action)}")

    print(f"\n  [exec] Executing actions ...")
    for action in actions:
        desc = describe_action(action)
        # Pad with dots for alignment
        padding = "." * max(1, 45 - len(desc))
        result = execute_action(action)
        status = "ok" if result else "FAIL"
        print(f"           {desc} {padding} {status}")


# ── Container lifecycle ──────────────────────────────────────

def start_container():
    """Start the Docker container if it isn't already running."""
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


def stop_container():
    """Stop and remove the container."""
    print(f"\n[cleanup] Stopping {CONTAINER_NAME} ...")
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)
    print("[cleanup] Stopped.")