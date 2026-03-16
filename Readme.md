# computer-use-agent

GPT-5.4 controls a desktop inside a Docker container. You give it a task, it looks at the screen, clicks around, and gets it done.

## setup

need python 3.10+, docker, and an openai api key

```bash
pip install openai python-dotenv
```

make a `.env` file:
```
OPENAI_API_KEY=sk-...
```

build the docker image:
```bash
docker build -t cua-desktop .
```

## run

```bash
python main.py --message "open Firefox and search for weather in San Francisco"
```

this starts the container, runs the agent loop, and prints what GPT is doing each turn. screenshots get saved to `screenshots/`.

to keep the container running after:
```bash
python main.py --message "open Firefox and search for weather in SF" --no-stop
```

## vnc

connect to `localhost:5901` with any vnc client to watch the agent work. password is `secret`.

## how it works

1. docker container runs ubuntu + xfce desktop + vnc
2. agent takes a screenshot and sends it to gpt-5.4
3. gpt returns actions (click, type, scroll, etc)
4. agent executes them with xdotool
5. new screenshot, send it back, repeat until done

uses the openai responses api with the built-in `computer` tool.

## files

- `main.py` — cli + agent loop
- `docker_helpers.py` — docker exec, screenshots, action execution
- `config.py` — settings (model, max turns, ports)
- `Dockerfile` — ubuntu + xfce + vnc + firefox
- `start.sh` — container startup script