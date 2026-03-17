FROM cua-desktop

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip3 install openai

COPY agent.py /app/agent.py
COPY runtime.py /app/runtime.py
COPY local_runtime.py /app/local_runtime.py
COPY config.py /app/config.py

CMD ["/bin/bash", "-c", "/start.sh & sleep 4 && cd /app && python3 agent.py --message \"$TASK_MESSAGE\""]