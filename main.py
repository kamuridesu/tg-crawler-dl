import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from io import BytesIO
from random import randint
from typing import Any, Callable
from urllib.parse import urlparse

import filetype
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, InputFile, Message
from aiohttp import ClientSession

from parser import parse_find_url
from config import TOKEN

dp = Dispatcher()


@dataclass
class FileInfo:
    filename: str
    content: bytes
    mime: str
    size: int
WAITING_REPLY_ID: dict[str, FileInfo] = {}

def generate_random_id(digits: str = 6):
    _id = ""
    for _ in range(digits):
        _id += str(randint(0, 9))
    return _id


async def fetch_url(url: str, progress=None):
    async with ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise TypeError("Can't fetch URL")
            filename = f"{generate_random_id()}"
            size = 0
            ctype = ""
            content = b""
            if "Content-Disposition" in response.headers:
                filename = (
                    response.headers["Content-Disposition"]
                    .split("filename=")[1]
                    .strip('"')
                )
            if "Content-Length" in response.headers:
                size = int(response.headers["Content-Length"])
                while True:
                    chunk = await response.content.read(2048)
                    if not chunk:
                        break
                    content += chunk
                    if progress is not None:
                        await progress(len(content), size)
            else:
                print("Warn, file doesn't support progress")
                content = await response.read()
            if "Content-Type" in response.headers:
                ctype = response.headers.get("Content-Type").split("/")[1]
                if ";" in ctype:
                    ctype = ctype.split(";")[0]
            ext = filetype.guess_extension(content)
            mime = filetype.guess_mime(content)
            if mime is None:
                mime = ""
            if not ext:
                ext = ""
            return FileInfo(
                filename
                + (
                    ("." + ext)
                    if ext is None and not filename.endswith(ext)
                    else ("." + ctype) if not filename.endswith(ctype) else ""
                ),
                content,
                mime,
                size,
            )


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Hello, {html.bold(message.from_user.full_name)}! Send me a URL and I'll download it for you!"
    )


class Progress:
    """Updates the message with the percentage downloaded"""

    def __init__(self, message: Message):
        self.message = message
        self.enabled = True
        self.message_to_send = "Downloading... "
        self.start_time = time.perf_counter()
        self.__last_message = ""

    async def update(self, count: int | float, total: int | float, message: str = ""):
        if message == "":
            message = self.message_to_send
        """Updates the message with the download percentage every 10 seconds"""
        total_time = time.perf_counter() - self.start_time
        if total_time > 10 or total_time < 1:
            if total_time > 10:
                self.start_time = time.perf_counter()
            percents = round(100 * count / float(total), 1)
            message = f"{message} {percents}%"
            if message != self.__last_message:
                await self.message.edit_text(message)
                self.__last_message = message

    async def finish(self):
        await self.message.delete()


@dp.message()
async def main_handler(message: Message) -> None:
    urls = []
    if (data := WAITING_REPLY_ID.get(f"{message.chat.id}:{message.from_user.id}")):
        WAITING_REPLY_ID.pop(f"{message.chat.id}:{message.from_user.id}")
        extensions = [x.strip() for x in message.text.split(",")]
        urls = parse_find_url(data.content, extensions)

    else:
        parsed = urlparse(message.text)
        if not all([parsed.scheme, parsed.netloc]):
            return await message.answer("Received message is not a valid URL. Try again.")
        urls = [message.text]
    
    if len(urls) < 1:
        return await message.answer("No files found for download.")

    for index, url in enumerate(urls):
        try:
            msg = await message.reply(f"Downloading file {index + 1}, please wait...")
            progress = Progress(msg)
            file = await fetch_url(url, progress.update)

            if file.filename.endswith(".html"):
                await msg.edit_text("Looks like you've sent a HTML page. Please, type the extensions to download (use , as delimiter): ")
                WAITING_REPLY_ID[f"{message.chat.id}:{message.from_user.id}"] = file
                return

            func: Callable[[BufferedInputFile, str], Any] = message.answer_document

            if "image" in file.mime:
                func = message.answer_photo
            elif "video" in file.mime:
                func = message.answer_video
            if (len(file.content)) == 0:
                await message.answer("Error: Could not download media from URL: " + url)
                continue
            await msg.edit_text("Trying to send file...")
            for i in range(1):
                try:
                    await func(
                        BufferedInputFile(file.content, file.filename),
                        caption=file.filename,
                    )
                    await progress.finish()
                    continue
                except Exception:
                    await msg.edit_text(f"Failed to send file! Retrying {i + 1}/3...")
            await message.answer("Fail to send media, try again.")
        except TypeError:
            await message.answer("URL not recognized! Try other one.")


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
