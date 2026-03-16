import argparse
import time
from openai import OpenAI

from config import MODEL, MAX_TURNS, VNC_PORT, CONTAINER_NAME
from docker_helpers import (
    start_container,
    stop_container,
    capture_screenshot,
    handle_actions,
    SCREENSHOT_DIR,
)

client = OpenAI()


def run_agent(message: str):
    """The core agent loop: task -> actions -> screenshot -> repeat."""

    print(f"\n{'='*60}")
    print(f"  Computer-Use Agent")
    print(f"  Model: {MODEL} | Container: {CONTAINER_NAME} | VNC: localhost:{VNC_PORT}")
    print(f"{'='*60}")

    print(f'\n[task] "{message}"')
    print(f"[agent] Sending task to GPT-5.4 ...\n")

    response = client.responses.create(
        model=MODEL,
        tools=[{"type": "computer"}],
        input=message,
        truncation="auto",
    )

    turn = 0
    while turn < MAX_TURNS:
        turn += 1
        print(f"\n── Turn {turn}/{MAX_TURNS} {'─'*44}")

        # Find computer_call and messages in response
        computer_call = None
        for item in response.output:
            if item.type == "computer_call":
                computer_call = item
            elif item.type == "message":
                for part in item.content:
                    if hasattr(part, "text"):
                        print(f'\n  [gpt] "{part.text}"')

        # No computer_call means GPT is done
        if computer_call is None:
            print(f"\n  [done] Task complete — no more actions.")
            break

        # Execute actions (prints its own formatted log)
        handle_actions(computer_call.actions)

        # Brief pause for screen to update
        time.sleep(0.5)

        # Take screenshot
        screenshot_b64 = capture_screenshot(step=turn)

        if not screenshot_b64:
            print("  [agent] Empty screenshot — retrying in 2s ...")
            time.sleep(2)
            screenshot_b64 = capture_screenshot(step=turn)

        if not screenshot_b64:
            print("  [agent] Still empty — skipping this turn.")
            continue

        # Send screenshot to GPT
        print("  [agent] Sending screenshot to GPT ...")
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
                },
            }],
            truncation="auto",
        )

    if turn >= MAX_TURNS:
        print(f"\n  [agent] Hit max turns limit ({MAX_TURNS}) — stopping.")

    print(f"\n{'='*60}")
    print(f"  DONE — completed in {turn} turns")
    print(f"  Screenshots saved to: {SCREENSHOT_DIR}/")
    container_status = "running"
    print(f"  Container: {container_status} (VNC -> localhost:{VNC_PORT})")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Computer-Use Agent — control a desktop via GPT-5.4"
    )
    parser.add_argument(
        "--message", "-m",
        required=True,
        help='The task for the agent (e.g. "open Firefox and search weather in SF")',
    )
    parser.add_argument(
        "--no-stop",
        action="store_true",
        help="Keep the container running after the agent finishes",
    )
    args = parser.parse_args()

    start_container()
    try:
        run_agent(args.message)
    finally:
        if not args.no_stop:
            stop_container()


if __name__ == "__main__":
    main()