import asyncio
from dataclasses import dataclass
from random import randint
from typing import List

import filetype
from aiogram.types import (
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
    MessageEntity,
)
from aiogram.utils.media_group import MediaGroupBuilder
from aiohttp import ClientSession


@dataclass
class FileInfo:
    filename: str
    content: bytes
    mime: str
    size: int
    origin: str | None = None


@dataclass
class ProgressData:
    id: int
    progress: int = 0

    def update(self, count: int, total_size: int):
        self.progress = 100 * count / float(total_size)


class Progress:
    def __init__(self, message: Message):
        self.message = message
        self.__last_message_body = ""
        self.progress_data: list[ProgressData] = []
        self.task = None

    def register(self, id: int):
        pd = ProgressData(id)
        self.progress_data.append(pd)
        return pd

    async def generate(self):
        body = ""
        for file in self.progress_data:
            if file.progress == 100:
                continue
            body += f"File {file.id}: {file.progress:.1f}%\n"
        if self.__last_message_body != body:
            await self.message.edit_text(body)
            self.__last_message_body = body

    async def __start(self):
        while True:
            await self.generate()
            await asyncio.sleep(10)

    async def start(self):
        self.task = asyncio.Task(self.__start())

    async def finish(self):
        await self.message.delete()
        self.task.cancel()


def generate_random_id(digits: str = 6):
    _id = ""
    for _ in range(digits):
        _id += str(randint(0, 9))
    return _id


async def fetch_url(url: str, progress=None):
    async with ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"[WARN] Erro fetching URL {url}, status is {response.status}")
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
                async for chunk in response.content.iter_chunked(10192):
                    content += chunk
                    progress(len(content), size)
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
    def __init__(
        self,
        media: (
            List[
                InputMediaAudio | InputMediaPhoto | InputMediaVideo | InputMediaDocument
            ]
            | None
        ) = None,
        caption: str | None = None,
        caption_entities: List[MessageEntity] | None = None,
    ) -> None:
        super().__init__(media, caption, caption_entities)

    def clear(self):
        self._media.clear()

    def __len__(self):
        return len(self._media)
