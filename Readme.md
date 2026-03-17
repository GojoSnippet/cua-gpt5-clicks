# CUA — Computer Use Agent (GPT-5.4)

An AI agent that controls a full Linux desktop inside Docker or Kubernetes. Give it a task in plain English — it sees the screen, clicks, types, scrolls, and gets it done autonomously using OpenAI's GPT-5.4 `computer` tool.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Docker](https://img.shields.io/badge/Docker-Required-blue)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Supported-blue)
![Model](https://img.shields.io/badge/Model-GPT--5.4-green)

---

## How It Works

```
You ──▶ "open chrome and google weather in SF"
          │
          ▼
   ┌──────────────┐
   │  Agent Loop   │──── screenshot ───▶ GPT-5.4
   │  (agent.py)   │◀── actions ────────┘
   └──────┬───────┘
          │  click / type / scroll / drag / keypress
          ▼
   ┌──────────────┐
   │  Runtime      │  DockerRuntime  (local laptop)
   │               │  LocalRuntime   (inside K8s pod)
   └──────┬───────┘
          ▼
   ┌──────────────┐
   │  Desktop      │  Ubuntu 22.04 + XFCE + Firefox
   │  Container    │  Xvfb · x11vnc · xdotool
   └──────────────┘
```

1. A desktop environment starts inside a container (Docker or K8s pod)
2. The agent takes a screenshot and sends it to GPT-5.4 via the OpenAI Responses API
3. GPT-5.4 returns actions — click, type, scroll, drag, keypress, etc.
4. The agent executes each action using `xdotool`
5. A new screenshot is captured — the loop repeats until the task is complete (up to 30 turns)

---

## Prerequisites

- **Python 3.10+**
- **Docker** (running)
- **OpenAI API key** with access to GPT-5.4
- **Kubernetes** (optional — for `--kube` mode; e.g. Docker Desktop K8s, minikube, kind)

---

## Quick Start (Local Docker)

### 1. Clone the repo

```bash
git clone https://github.com/GojoSnippet/cua-gpt5-clicks.git
cd cua-gpt5-clicks
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your API key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
```

### 4. Build the Docker image

```bash
docker build -t cua-desktop .
```

### 5. Run the agent

```bash
python main.py --message "open Firefox and search for weather in San Francisco"
```

The agent starts the container, runs the task, and saves screenshots to `screenshots/`.

To keep the container running after the task finishes:

```bash
python main.py --message "open Firefox and search for weather in SF" --no-stop
```

**VNC:** Connect to `localhost:5901` with any VNC client to watch the agent work in real time.

---

## Kubernetes Mode

Run the agent entirely inside a Kubernetes cluster. The desktop + agent run in a single pod within the `cua` namespace.

### 1. Build both images

```bash
docker build -t cua-desktop .
docker build -t cua-agent-k8s -f k8s/Dockerfile .
```

### 2. Run with `--kube`

```bash
python main.py --message "open Firefox and search who won oscar recently" --kube
```

This will:
- Create the `cua` namespace
- Inject your API key as a K8s Secret
- Deploy a Job + NodePort Service
- Stream agent logs to your terminal
- Clean up all resources when done

**VNC:** Connect to `localhost:30501` to watch the agent inside the pod.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  main.py  (CLI entry point)                         │
│  ├── --message "task"          (required)            │
│  ├── --no-stop                 (local: keep running) │
│  └── --kube                    (run on Kubernetes)   │
└──────────┬──────────────────────┬───────────────────┘
           │ Local mode           │ Kube mode
           ▼                      ▼
   ┌──────────────┐      ┌────────────────┐
   │DockerRuntime  │      │ kubectl apply  │
   │(docker exec)  │      │ Job + Service  │
   └──────┬───────┘      │ in namespace   │
          │               │ "cua"          │
          │               └───────┬────────┘
          │                       │
          ▼                       ▼
   ┌──────────────────────────────────────┐
   │         agent.py (agent loop)        │
   │  runtime.exec() ← runtime agnostic  │
   └──────────────────────────────────────┘
```

| Class | How it runs commands |
|-------|---------------------|
| `DockerRuntime` | `docker exec` into the container from your laptop |
| `LocalRuntime` | `subprocess.run` directly — used inside the K8s pod |

---

## Project Structure

```
├── main.py              # CLI — local Docker or Kubernetes mode
├── agent.py             # GPT-5.4 agent loop (runtime-agnostic)
├── runtime.py           # Abstract base class for runtimes
├── docker_runtime.py    # DockerRuntime — runs via docker exec
├── local_runtime.py     # LocalRuntime — runs inside K8s pod
├── config.py            # Settings (model, max turns, ports)
├── Dockerfile           # Ubuntu 22.04 + XFCE + VNC + Firefox
├── start.sh             # Container startup (Xvfb → VNC → XFCE)
├── requirements.txt     # Python dependencies
├── k8s/
│   ├── namespace.yaml   # "cua" namespace
│   ├── Dockerfile       # Extends cua-desktop with Python + agent
│   ├── job.yaml         # K8s Job — runs agent as one-shot task
│   └── service.yaml     # NodePort service — VNC on port 30501
└── screenshots/         # Auto-saved screenshots from each turn
```

---

## Configuration

Edit `config.py` to change defaults:

| Setting          | Default        | Description                    |
|------------------|----------------|--------------------------------|
| `MODEL`          | `gpt-5.4`     | OpenAI model to use            |
| `MAX_TURNS`      | `30`           | Max screenshot→action cycles   |
| `CONTAINER_NAME` | `cua-desktop`  | Docker container name          |
| `VNC_PORT`       | `5901`         | VNC server port (local mode)   |

---


