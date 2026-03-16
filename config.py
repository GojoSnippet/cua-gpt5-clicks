import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-5.4"

# Docker container
CONTAINER_NAME = "cua-desktop"
IMAGE_NAME = "cua-desktop"
DISPLAY = ":98"

# VNC
VNC_PORT = 5901

# Agent
MAX_TURNS = 30