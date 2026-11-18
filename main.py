import asyncio
import logging
import os
from datetime import datetime
from functools import cache
from io import BytesIO
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.types import BufferedInputFile, InlineQuery, InlineQueryResultCachedGif
from PIL import Image, ImageDraw, ImageFont, ImageSequence

HERE = Path(__file__).parent
FONT = str(HERE / "Roboto-Black.ttf")
WIDTH = 350
MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)

dp = Dispatcher()
_file_ids: dict[str, str] = {}  # подпись -> file_id уже загруженной гифки
_upload_lock = asyncio.Lock()


@cache
def _source() -> tuple[list[Image.Image], Image.Image, int]:
    with Image.open(HERE / "shelby.gif") as gif:
        palette = gif.copy()  # первый кадр несёт общую палитру гифки
        size = (WIDTH, WIDTH * gif.height // gif.width)
        frames = [f.convert("RGB").resize(size) for f in ImageSequence.Iterator(gif)]
        return frames, palette, gif.info["duration"]


def render(text: str) -> bytes:
    frames, palette, duration = _source()
    width, height = frames[0].size
    # Ширина текста растёт линейно с кеглем: одного замера хватает, чтобы занять 80% кадра.
    font = ImageFont.truetype(FONT, int(80 * width / ImageFont.truetype(FONT, 100).getlength(text)))
    center = (width / 2, height * 0.8)
    out = []
    for base in frames:
        frame = base.copy()
        draw = ImageDraw.Draw(frame)
        left, top, right, bottom = draw.textbbox(center, text, font=font, anchor="mm")
        draw.rectangle((left - 5, top - 5, right + 5, bottom + 5), fill="black")
        draw.text(center, text, font=font, anchor="mm", fill="white")
        # Родная палитра вместо подбора новой на каждый кадр: в 40 раз быстрее и файл вчетверо меньше.
        out.append(frame.quantize(palette=palette, dither=Image.Dither.NONE))
    buf = BytesIO()
    out[0].save(buf, "GIF", save_all=True, append_images=out[1:], loop=0, duration=duration)
    return buf.getvalue()


async def file_id_for(text: str, bot: Bot, chat_id: int) -> str:
    # Инлайн-ответу нужен file_id, а получить его можно только отправив файл в какой-нибудь чат.
    # Лок: одновременные запросы делят одну загрузку и не упираются в лимит сообщений на чат.
    async with _upload_lock:
        if text not in _file_ids:
            if len(_file_ids) >= 100:  # подписи с секундами не повторяются — не копим их вечно
                _file_ids.clear()
            gif = await asyncio.to_thread(render, text)
            msg = await bot.send_animation(
                chat_id, BufferedInputFile(gif, "shelby.gif"), disable_notification=True
            )
            await bot.delete_message(chat_id, msg.message_id)
            _file_ids[text] = msg.animation.file_id
        return _file_ids[text]


@dp.inline_query()
async def on_inline_query(query: InlineQuery, bot: Bot, storage_chat_id: int) -> None:
    now = datetime.now()  # локальное время контейнера, пояс задаёт переменная TZ
    date = f"Как же заебало {now.day} {MONTHS[now.month - 1]}"
    results = [
        InlineQueryResultCachedGif(
            id=str(i), gif_file_id=await file_id_for(text, bot, storage_chat_id), title=text
        )
        for i, text in enumerate((date, f"{date} {now:%H:%M:%S}"))
    ]
    await query.answer(results, cache_time=1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dp.run_polling(
        Bot(os.environ["BOT_TOKEN"]), storage_chat_id=int(os.environ["STORAGE_CHAT_ID"])
    )
