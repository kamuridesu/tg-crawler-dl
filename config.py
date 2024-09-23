import os
from pathlib import Path

from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer


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
TELEGRAM_API_BASE = os.getenv("API_HOST")

TELEGRAM_API_SERVER = None
if TELEGRAM_API_BASE:
    print(f"[INFO] Using {TELEGRAM_API_BASE} as api server")
    TELEGRAM_API_SERVER = AiohttpSession(
        api=TelegramAPIServer.from_base(TELEGRAM_API_BASE)
    )
