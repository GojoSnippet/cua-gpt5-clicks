import argparse
import subprocess
import sys
import time
import os

from config import CONTAINER_NAME, VNC_PORT


def run_local(message: str, no_stop: bool):
    """Local Docker mode — agent runs on your laptop."""
    from docker_runtime import DockerRuntime
    from agent import run_agent

    runtime = DockerRuntime()
    runtime.start()
    try:
        run_agent(runtime, message)
    finally:
        if not no_stop:
            runtime.stop()


def run_kube(message: str):
    """Kubernetes mode — agent runs inside the pod."""

    # 0. Create namespace
    subprocess.run(["kubectl", "apply", "-f", "k8s/namespace.yaml"], check=True)
    print("[kube] Namespace 'cua' ready.")

    # 1. Create secret if it doesn't exist
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[error] OPENAI_API_KEY not found in .env", file=sys.stderr)
        sys.exit(1)

    subprocess.run(
        ["kubectl", "delete", "secret", "openai-api-key", "-n", "cua", "--ignore-not-found"],
        capture_output=True,
    )
    subprocess.run(
        ["kubectl", "create", "secret", "generic", "openai-api-key",
         f"--from-literal=OPENAI_API_KEY={api_key}", "-n", "cua"],
        capture_output=True, check=True,
    )
    print("[kube] Secret created.")

    # 2. Apply service
    subprocess.run(["kubectl", "apply", "-f", "k8s/service.yaml"], check=True)
    print(f"[kube] VNC -> localhost:30501")

    # 3. Apply job with task message injected
    subprocess.run(
        ["kubectl", "delete", "job", "cua-agent", "-n", "cua", "--ignore-not-found"],
        capture_output=True,
    )
    time.sleep(2)

    # Read job yaml and inject task message
    with open("k8s/job.yaml", "r") as f:
        job_yaml = f.read()
    job_yaml = job_yaml.replace("__TASK_MESSAGE__", message.replace('"', '\\"'))

    subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=job_yaml.encode(),
        check=True,
    )
    print("[kube] Job created.")

    # 4. Wait for pod to start
    print("[kube] Waiting for pod ...")
    pod_name = None
    for _ in range(60):
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", "cua", "-l", "job-name=cua-agent",
             "-o", "jsonpath={.items[0].metadata.name}"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            pod_name = result.stdout.strip()
            # Check if running
            phase = subprocess.run(
                ["kubectl", "get", "pod", pod_name, "-n", "cua", "-o", "jsonpath={.status.phase}"],
                capture_output=True, text=True,
            )
            if phase.stdout.strip() in ("Running", "Succeeded"):
                break
        time.sleep(2)
    else:
        print("[kube] Warning: pod may not be ready.", file=sys.stderr)

    if not pod_name:
        print("[error] Could not find pod.", file=sys.stderr)
        sys.exit(1)

    print(f"[kube] Pod: {pod_name}")
    print(f"[kube] Streaming logs ...\n")

    # 5. Stream logs until job completes
    try:
        subprocess.run(
            ["kubectl", "logs", "-f", pod_name, "-n", "cua"],
        )
    except KeyboardInterrupt:
        print("\n[kube] Interrupted.")

    # 6. Cleanup
    print("\n[kube] Cleaning up ...")
    subprocess.run(["kubectl", "delete", "-f", "k8s/job.yaml", "--ignore-not-found"], capture_output=True)
    subprocess.run(["kubectl", "delete", "-f", "k8s/service.yaml", "--ignore-not-found"], capture_output=True)
    subprocess.run(["kubectl", "delete", "secret", "openai-api-key", "-n", "cua", "--ignore-not-found"], capture_output=True)
    print("[kube] Done.")


def main():
    parser = argparse.ArgumentParser(
        description="Computer-Use Agent — control a desktop via GPT-5.4"
    )
    parser.add_argument(
        "--message", "-m",
        required=True,
        help='The task for the agent',
    )
    parser.add_argument(
        "--no-stop",
        action="store_true",
        help="Keep the container running after the agent finishes (local mode only)",
    )
    parser.add_argument(
        "--kube",
        action="store_true",
        help="Run on Kubernetes instead of local Docker",
    )
    args = parser.parse_args()

    if args.kube:
        run_kube(args.message)
    else:
        run_local(args.message, args.no_stop)


if __name__ == "__main__":
    main()