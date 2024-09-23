import time
from dataclasses import dataclass
from random import randint
from typing import List

import filetype
from aiogram.types import Message, MessageEntity
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import InputMediaAudio, InputMediaPhoto, InputMediaDocument, InputMediaVideo
from aiohttp import ClientSession

@dataclass
class FileInfo:
    filename: str
    content: bytes
    mime: str
    size: int
    origin: str | None = None


class Progress:
    """Updates the message with the percentage downloaded"""

    def __init__(self, message: Message, total: int = 0):
        self.message = message
        self.enabled = True
        self.message_to_send = "Downloading... "
        self.start_time = time.perf_counter()
        self.__last_message = ""
        self.counter = 0
        self.total = total

    async def progress(self, count: int | float, total: int | float, message: str = ""):
        if message == "":
            message = self.message_to_send
        """Updates the message with the download percentage every 10 seconds"""
        total_time = time.perf_counter() - self.start_time
        if total_time > 10 or total_time < 1:
            if total_time > 10:
                self.start_time = time.perf_counter()
            percents = round(100 * count / float(total), 1)
            message = f"{message} {percents:.1f}%"
            if message != self.__last_message:
                await self.message.edit_text(message)
                self.__last_message = message

    async def update(self, message: str = ""):
        self.counter += 1
        await self.progress(self.counter, self.total, message)


    async def finish(self):
        await self.message.delete()


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


class MediaBuilder(MediaGroupBuilder):
    def __init__(self, media: List[InputMediaAudio | InputMediaPhoto | InputMediaVideo | InputMediaDocument] | None = None, caption: str | None = None, caption_entities: List[MessageEntity] | None = None) -> None:
        super().__init__(media, caption, caption_entities)

    def clear(self):
        self._media.clear()

    def __len__(self):
        return len(self._media)