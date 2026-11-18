import asyncio
import logging
import os
import re
import sqlite3
from datetime import datetime
from functools import cache
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo, available_timezones

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import (
    BufferedInputFile,
    InlineQuery,
    InlineQueryResultCachedGif,
    InlineQueryResultsButton,
    Message,
)
from PIL import Image, ImageDraw, ImageFont, ImageSequence

HERE = Path(__file__).parent
FONT = str(HERE / "Roboto-Black.ttf")
WIDTH = 350
MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)

ZONES = {zone.lower(): zone for zone in available_timezones()}

dp = Dispatcher()
_file_ids: dict[str, str] = {}  # подпись -> file_id уже загруженной гифки
_upload_lock = asyncio.Lock()


@cache
def _db() -> sqlite3.Connection:
    db = sqlite3.connect(os.getenv("DB_PATH", "zones.db"), autocommit=True)
    db.execute("CREATE TABLE IF NOT EXISTS zones (user_id INTEGER PRIMARY KEY, zone TEXT NOT NULL)")
    return db


def find_zone(text: str) -> str | None:
    """'europe/belgrade' -> 'Europe/Belgrade', '+3' и 'UTC+3' -> 'Etc/GMT-3', всё остальное -> None."""
    text = text.strip().lower()
    if m := re.fullmatch(r"(?:utc|gmt)?\s*([+-])\s*(\d{1,2})(?::00)?", text):
        # У зон Etc/GMT знак перевёрнут: UTC+3 называется Etc/GMT-3.
        text = f"etc/gmt{'-' if m[1] == '+' else '+'}{int(m[2])}"
    return ZONES.get(text)


def now_for(user_id: int) -> datetime:
    row = _db().execute("SELECT zone FROM zones WHERE user_id = ?", (user_id,)).fetchone()
    # Без своей настройки — пояс контейнера (переменная TZ).
    return datetime.now().astimezone(ZoneInfo(row[0]) if row else None)


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
    now = now_for(query.from_user.id)
    date = f"Как же заебало {now.day} {MONTHS[now.month - 1]}"
    results = [
        InlineQueryResultCachedGif(
            id=str(i), gif_file_id=await file_id_for(text, bot, storage_chat_id), title=text
        )
        for i, text in enumerate((date, f"{date} {now:%H:%M:%S}"))
    ]
    await query.answer(
        results,
        cache_time=1,
        is_personal=True,  # иначе Telegram отдаст чужой кэш с чужим часовым поясом
        button=InlineQueryResultsButton(
            text=f"Часовой пояс UTC{now:%:z} — изменить", start_parameter="tz"
        ),
    )


@dp.message(F.chat.type == "private")
async def on_private_message(message: Message) -> None:
    if zone := find_zone(message.text or ""):
        _db().execute("INSERT OR REPLACE INTO zones VALUES (?, ?)", (message.from_user.id, zone))
        reply = "Готово."
    else:
        reply = (
            "Пришлите свой часовой пояс: смещение от UTC (например, +3) "
            "или название (например, Europe/Belgrade)."
        )
    now = now_for(message.from_user.id)
    await message.answer(f"{reply}\nПо моим данным, у вас сейчас {now:%H:%M} (UTC{now:%:z}).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Пустой TELEGRAM_PROXY — прямое соединение.
    session = AiohttpSession(proxy=os.getenv("TELEGRAM_PROXY") or None)
    dp.run_polling(
        Bot(os.environ["BOT_TOKEN"], session=session),
        storage_chat_id=int(os.environ["STORAGE_CHAT_ID"]),
    )
