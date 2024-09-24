import asyncio
import logging
import sys
from parser import fetch_links, parse_find_url, parse_url
from typing import Any, Callable
from urllib.parse import urlparse

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, Message

from browser import fetch_page
from config import TELEGRAM_API_SERVER, TOKEN
from utils import FileInfo, MediaBuilder, Progress, Request

dp = Dispatcher()
TASKS: set[asyncio.Task] = set()
LOCK = asyncio.Lock()


WAITING_REPLY_ID: dict[str, FileInfo] = {}

REQUESTER: Request


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Hello, {html.bold(message.from_user.full_name)}! Send me a URL and I'll download it for you!"
    )


@dp.message(Command("help"))
async def help_command_handler(message: Message) -> None:
    await message.answer(
        f"Hello, {html.bold(message.from_user.full_name)}! Send me a URL and I'll download it for you!"
        + "\n"
        + "If you send me an HTML page, I will fetch all links for you than ask you what should I do with those URLs.\n"
        + "If you type file extensions like mp4,jpg (use , to delimit extensions) then I'll try to downlaod for those and send it to you.\n"
        + "You can also reply with `link` for me to send all the URLs that I've found!\n"
        + "Or include +selenium on the reply so I'll use Selenium to search and download for the files!"
    )


@dp.message()
async def main_handler(message: Message) -> None:
    urls = []
    if data := WAITING_REPLY_ID.get(f"{message.chat.id}:{message.from_user.id}"):
        WAITING_REPLY_ID.pop(f"{message.chat.id}:{message.from_user.id}")
        MESSAGE_TEXT = message.text
        USE_SELENIUM = False

        if "+selenium" in MESSAGE_TEXT:
            sent_msg = await message.reply("Fetching content with Selenium")
            print(f"[INFO] Using Selenium as default")
            USE_SELENIUM = True
            MESSAGE_TEXT = MESSAGE_TEXT.replace("+selenium", "")

        if MESSAGE_TEXT.lower() == "links":
            return await fetch_links(message, data)

        extensions = [x.strip().lower() for x in MESSAGE_TEXT.split(",")]
        urls = []
        if not USE_SELENIUM:
            urls = [
                parse_url(data.origin, x)
                for x in parse_find_url(data.content, extensions)
            ]

        if len(urls) < 1:
            if not USE_SELENIUM:
                sent_msg = await message.reply(
                    "Oopsie, looks like I wasn't able to find any matches! I'll try again this time with more effort 😚"
                )
            new_content, cookies = fetch_page(data.origin)
            REQUESTER.set_cookies(cookies)
            urls = [
                parse_url(data.origin, x)
                for x in parse_find_url(new_content, extensions)
            ]
            if len(urls) < 1:
                return await message.edit_text(
                    "Sorry, I did my best but couldn't find the stuff you're looking for :("
                )
            await sent_msg.delete()

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
    TASKS.clear()
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
        try:
            file = await REQUESTER.fetch_url(url, pd.update)
        except Exception as e:
            pd.failed = True
            return message.reply(f"Failed to fetch {url}, error is {e}")
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
        pd.failed = True
        print(f"Error: {e}, URL: {url}")
        await message.reply(f"Failed to download from {url}")


async def send_media_group(message, media_group):
    try:
        await message.answer_media_group(media_group.build())
    except Exception as e:
        print(e)
        await message.answer("Failed to send media!")


async def main() -> None:
    global REQUESTER
    async with Request() as REQUESTER:
        bot = Bot(
            token=TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            session=TELEGRAM_API_SERVER,
        )
        await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
