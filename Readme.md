# CUA — Computer Use Agent (GPT-5.4)

An AI agent that controls a full Linux desktop inside a Docker container. Give it a task in plain English — it sees the screen, clicks, types, scrolls, and gets it done autonomously using OpenAI's GPT-5.4 `computer` tool.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Docker](https://img.shields.io/badge/Docker-Required-blue)
![Model](https://img.shields.io/badge/Model-GPT--5.4-green)

---

## How It Works

```
You ──▶ "Search weather in SF"
          │
          ▼
   ┌──────────────┐
   │  Agent Loop   │──── screenshot ───▶ GPT-5.4
   │  (main.py)    │◀── actions ────────┘
   └──────┬───────┘
          │  click / type / scroll
          ▼
   ┌──────────────┐
   │   Docker      │  Ubuntu 22.04 + XFCE Desktop
   │   Container   │  Firefox · xdotool · VNC
   └──────────────┘
```

1. A Docker container spins up an Ubuntu desktop with XFCE, Firefox, and a VNC server
2. The agent takes a screenshot and sends it to GPT-5.4 via the OpenAI Responses API
3. GPT-5.4 returns actions — click, type, scroll, drag, keypress, etc.
4. The agent executes each action inside the container using `xdotool`
5. A new screenshot is captured and sent back — the loop repeats until the task is complete (up to 30 turns)

---

## Prerequisites

- **Python 3.10+**
- **Docker** (running)
- **OpenAI API key** with access to GPT-5.4

---

## Quick Start

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

The agent will start the container, run the task, and save screenshots to `screenshots/`.

To keep the container running after the task finishes:

```bash
python main.py --message "open Firefox and search for weather in SF" --no-stop
```

---

## Watch It Live (VNC)

Connect to `localhost:5901` with any VNC client (e.g., RealVNC, TigerVNC) to watch the agent work in real time.

---

## Kubernetes (Optional)

A pod manifest is included to run the desktop container on a local K8s cluster:

```bash
kubectl apply -f k8s/pod.yaml
kubectl port-forward pod/cua-desktop 5901:5901
```

---

## Project Structure

```
├── main.py              # CLI entry point + agent loop
├── docker_helpers.py    # Docker exec, screenshots, action execution
├── config.py            # Settings (model, max turns, ports)
├── Dockerfile           # Ubuntu 22.04 + XFCE + VNC + Firefox
├── start.sh             # Container startup script (Xvfb → VNC → XFCE)
├── requirements.txt     # Python dependencies
├── k8s/
│   └── pod.yaml         # Kubernetes pod manifest
└── screenshots/         # Auto-saved screenshots from each turn
```

---

## Configuration

Edit [`config.py`](config.py) to change defaults:

| Setting          | Default        | Description                    |
|------------------|----------------|--------------------------------|
| `MODEL`          | `gpt-5.4`     | OpenAI model to use            |
| `MAX_TURNS`      | `30`           | Max screenshot→action cycles   |
| `CONTAINER_NAME` | `cua-desktop`  | Docker container name          |
| `VNC_PORT`       | `5901`         | VNC server port                |

