import base64
import os
import time
import shlex
from datetime import datetime

from openai import OpenAI

from config import MODEL, MAX_TURNS, DISPLAY

client = OpenAI()

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


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


def capture_screenshot(runtime, step: int = 0):
    png_bytes = runtime.exec(
        f"DISPLAY={DISPLAY} import -window root png:-",
        decode=False,
    )
    if not png_bytes:
        print("  [screenshot] Warning: empty screenshot.", flush=True)
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SCREENSHOT_DIR}/step_{step:03d}_{timestamp}.png"
    with open(filename, "wb") as f:
        f.write(png_bytes)
    print(f"  [screenshot] Saved: {filename}", flush=True)

    return base64.b64encode(png_bytes).decode("utf-8")


# ── Action helpers 

def describe_action(action):
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


def execute_action(runtime, action):
    t = action.type

    if t == "click":
        x, y = action.x, action.y
        button = getattr(action, "button", "left")
        btn_num = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
        result = runtime.exec(f"DISPLAY={DISPLAY} xdotool mousemove {x} {y} click {btn_num}")
        return result is not None

    elif t == "double_click":
        x, y = action.x, action.y
        result = runtime.exec(
            f"DISPLAY={DISPLAY} xdotool mousemove {x} {y} click --repeat 2 --delay 100 1"
        )
        return result is not None

    elif t == "type":
        safe_text = shlex.quote(action.text)
        result = runtime.exec(
            f"DISPLAY={DISPLAY} xdotool type --clearmodifiers --delay 0 {safe_text}"
        )
        return result is not None

    elif t == "keypress":
        keys = action.keys
        mapped = [KEY_MAP.get(k.lower(), k) for k in keys]
        combo = "+".join(mapped)
        result = runtime.exec(f"DISPLAY={DISPLAY} xdotool key --clearmodifiers {combo}")
        return result is not None

    elif t == "scroll":
        x, y = action.x, action.y
        scroll_y = getattr(action, "scrollY", 0)
        btn = "4" if scroll_y < 0 else "5"
        clicks = max(1, abs(round(scroll_y / 100)))
        runtime.exec(f"DISPLAY={DISPLAY} xdotool mousemove {x} {y}")
        for _ in range(clicks):
            runtime.exec(f"DISPLAY={DISPLAY} xdotool click {btn}")
        return True

    elif t == "drag":
        path = action.path
        if len(path) >= 2:
            start = path[0]
            end = path[-1]
            runtime.exec(
                f"DISPLAY={DISPLAY} xdotool mousemove {start['x']} {start['y']} "
                f"mousedown 1 mousemove {end['x']} {end['y']} mouseup 1"
            )
        return True

    elif t == "move":
        result = runtime.exec(f"DISPLAY={DISPLAY} xdotool mousemove {action.x} {action.y}")
        return result is not None

    elif t == "screenshot":
        return True

    elif t == "wait":
        ms = getattr(action, "ms", 2000)
        time.sleep(ms / 1000)
        return True

    return False


def handle_actions(runtime, actions):
    print(f"\n  [gpt] Requested {len(actions)} action(s):", flush=True)
    for i, action in enumerate(actions, 1):
        print(f"          {i}. {describe_action(action)}", flush=True)

    print(f"\n  [exec] Executing actions ...", flush=True)
    for action in actions:
        desc = describe_action(action)
        padding = "." * max(1, 45 - len(desc))
        result = execute_action(runtime, action)
        status = "ok" if result else "FAIL"
        print(f"           {desc} {padding} {status}", flush=True)


# Agent loop

def run_agent(runtime, message: str):
    print(f"\n{'='*60}", flush=True)
    print(f"  Computer-Use Agent", flush=True)
    print(f"  Model: {MODEL}", flush=True)
    print(f"{'='*60}", flush=True)

    print(f'\n[task] "{message}"', flush=True)
    print(f"[agent] Sending task to {MODEL} ...\n", flush=True)

    response = client.responses.create(
        model=MODEL,
        tools=[{"type": "computer"}],
        input=message,
        truncation="auto",
    )

    turn = 0
    while turn < MAX_TURNS:
        turn += 1
        print(f"\n── Turn {turn}/{MAX_TURNS} {'─'*44}", flush=True)

        computer_call = None
        for item in response.output:
            if item.type == "computer_call":
                computer_call = item
            elif item.type == "message":
                for part in item.content:
                    if hasattr(part, "text"):
                        print(f'\n  [gpt] "{part.text}"', flush=True)

        if computer_call is None:
            print(f"\n  [done] Task complete — no more actions.", flush=True)
            break

        handle_actions(runtime, computer_call.actions)

        time.sleep(0.5)

        screenshot_b64 = capture_screenshot(runtime, step=turn)

        if not screenshot_b64:
            print("  [agent] Empty screenshot — retrying in 2s ...", flush=True)
            time.sleep(2)
            screenshot_b64 = capture_screenshot(runtime, step=turn)

        if not screenshot_b64:
            print("  [agent] Still empty — skipping this turn.", flush=True)
            continue

        print("  [agent] Sending screenshot to GPT ...", flush=True)
        response = client.responses.create(
            model=MODEL,
            tools=[{"type": "computer"}],
            previous_response_id=response.id,
            input=[{
                "type": "computer_call_output",
                "call_id": computer_call.call_id,
                "output": {
                    "type": "computer_screenshot",
                    "image_url": f"data:image/png;base64,{screenshot_b64}",
                    "detail": "original",
                },
            }],
            truncation="auto",
        )

    if turn >= MAX_TURNS:
        print(f"\n  [agent] Hit max turns limit ({MAX_TURNS}) — stopping.", flush=True)

    print(f"\n{'='*60}", flush=True)
    print(f"  DONE — completed in {turn} turns", flush=True)
    print(f"  Screenshots saved to: {SCREENSHOT_DIR}/", flush=True)
    print(f"{'='*60}\n", flush=True)

if __name__ == "__main__":
    import argparse
    from local_runtime import LocalRuntime

    parser = argparse.ArgumentParser()
    parser.add_argument("--message", "-m", required=True)
    args = parser.parse_args()

    runtime = LocalRuntime()
    runtime.start()
    run_agent(runtime, args.message)