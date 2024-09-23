import asyncio
import logging
import sys
from parser import parse_find_url, parse_url
from typing import Any, Callable
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, Message

from browser import fetch_page
from config import TELEGRAM_API_SERVER, TOKEN
from utils import FileInfo, MediaBuilder, Progress, fetch_url

dp = Dispatcher()
TASKS: set[asyncio.Task] = set()
LOCK = asyncio.Lock()


WAITING_REPLY_ID: dict[str, FileInfo] = {}


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Hello, {html.bold(message.from_user.full_name)}! Send me a URL and I'll download it for you!"
    )


@dp.message()
async def main_handler(message: Message) -> None:
    urls = []
    if data := WAITING_REPLY_ID.get(f"{message.chat.id}:{message.from_user.id}"):
        WAITING_REPLY_ID.pop(f"{message.chat.id}:{message.from_user.id}")
        extensions = [x.strip().lower() for x in message.text.split(",")]
        urls = [
            parse_url(data.origin, x) for x in parse_find_url(data.content, extensions)
        ]
        if len(urls) < 1:
            message = await message.reply(
                "Oopsie, looks like I wasn't able to find any matches! I'll try again this time with more effort 😚"
            )
            new_content = fetch_page(data.origin)
            urls = [
                parse_url(data.origin, x)
                for x in parse_find_url(new_content, extensions)
            ]
            if len(urls) < 1:
                return await message.edit_text(
                    "Sorry, I did my best but couldn't find the stuff you're looking for :("
                )
            await message.delete()

    else:
        print(f"[INFO] New message from {message.from_user.username}: {message.text}")
        parsed = urlparse(message.text)
        if not all([parsed.scheme, parsed.netloc]):
            return await message.answer(
                "Received message is not a valid URL. Try again."
            )
        urls = [message.text]

    if len(urls) < 1:
        return await message.answer("No files found for download.")

    return await process_all_urls(message, urls)


async def process_all_urls(message: Message, urls: list[str]):
    media_group = MediaBuilder()
    msg = await message.reply(f"Downloading...")
    pg = Progress(msg)
    await pg.start()
    for index, url in enumerate(urls):
        task = asyncio.create_task(process_url(message, index, url, media_group, pg))
        task.add_done_callback(lambda t: TASKS.remove(t))
        TASKS.add(task)
    await asyncio.gather(*TASKS)
    if len(media_group) > 0:
        await send_media_group(message, media_group)
        media_group.clear()
    await pg.finish()


async def process_url(
    message: Message,
    index: int,
    url: str,
    media_group: MediaBuilder,
    progress: Progress,
):
    pd = progress.register(index)
    try:
        file = await fetch_url(url, pd.update)
        pd.progress = 100
        if (len(file.content)) == 0:
            return

        if file.filename.endswith(".html"):
            await message.answer(
                "Looks like you've sent a HTML page. Please, type the extensions to download (use , as delimiter): "
            )
            file.origin = url
            WAITING_REPLY_ID[f"{message.chat.id}:{message.from_user.id}"] = file
            return

        func: Callable[[BufferedInputFile], Any] = media_group.add_document

        if "image" in file.mime:
            func = media_group.add_photo
        elif "video" in file.mime:
            func = media_group.add_video

        async with LOCK:
            func(media=BufferedInputFile(file.content, file.filename))
            if len(media_group) == 10:
                await send_media_group(message, media_group)
                media_group.clear()

    except TypeError as e:
        print(f"Error: {e}, URL: {url}")
        await message.reply(f"Failed to download from {url}")


async def send_media_group(message, media_group):
    try:
        await message.answer_media_group(media_group.build())
    except Exception as e:
        print(e)
        await message.answer("Failed to send media!")


async def main() -> None:
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=TELEGRAM_API_SERVER,
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
