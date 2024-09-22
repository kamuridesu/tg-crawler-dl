import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file():
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("#"):
                continue
            tmp = line.split("=")
            k = tmp[0]
            v = "=".join(tmp[1:])
            os.environ[k] = v


load_env_file()


TOKEN = os.getenv("BOT_TOKEN")
