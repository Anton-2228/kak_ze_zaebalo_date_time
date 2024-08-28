import asyncio
import datetime
import os
import uuid

from PIL import Image, ImageDraw, ImageSequence, ImageFont

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, InlineQuery, InlineQueryResultCachedGif

API_TOKEN = '7268779699:AAGITXxUBXUBEHSwXT7LPL5JHhUp5B7FjQw'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

router = Router()

width = 350

file_date_ids = []
file_datetime_ids = []
last_day = datetime.date.today()
last_time = datetime.datetime.now().time()

months = {
    1: "января", 2: "февраля", 3: "марта",
    4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября",
    10: "октября", 11: "ноября", 12: "декабря"
}


def find_font_size(text, target_width, font_path, min_font_size=10, max_font_size=100):
    # Создаем временное изображение для рисования текста
    image = Image.new("RGB", (target_width, 100))
    draw = ImageDraw.Draw(image)

    # Ищем подходящий размер шрифта методом двоичного поиска
    while min_font_size < max_font_size:
        font_size = (min_font_size + max_font_size) // 2
        font = ImageFont.truetype(font_path, font_size)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]

        if text_width < target_width:
            min_font_size = font_size + 1
        elif text_width > target_width:
            max_font_size = font_size - 1
        else:
            return font_size

    # Проверяем окончательно
    font = ImageFont.truetype(font_path, min_font_size)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    if text_width <= target_width:
        return min_font_size
    else:
        return min_font_size - 1

    # Проверяем окончательно
    font = ImageFont.truetype(font_path, min_font_size)
    text_width, _ = draw.textsize(text, font=font)
    if text_width <= target_width:
        return min_font_size
    else:
        return min_font_size - 1

async def create_gif(text, file_path):
    with Image.open('shelby.gif') as img:
        frames = []
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGBA")

            koef = frame.height / frame.width
            frame = frame.resize((width, int(width*koef)))
            frame_draw = ImageDraw.Draw(frame)

            offset = width * 0.1

            pos = (offset, frame.height*0.75)
            # date = datetime.date.today()
            # text = f'Как же заебало {date.day} {months[date.month]}'

            font_size = find_font_size(text, int(width*0.8), "Roboto-Black.ttf")
            font = ImageFont.truetype("Roboto-Black.ttf", font_size, encoding='UTF-8')

            left, top, right, bottom = frame_draw.textbbox(pos, text, font=font)
            frame_draw.rectangle((left-5, top-5, right+5, bottom+5), fill="black")
            frame_draw.text(pos, text, font=font, fill="white")

            frames.append(frame.convert("P", palette=Image.ADAPTIVE))

        frames[0].save(file_path, save_all=True, loop=0, append_images=frames[1:], optimize=False, duration=img.info['duration'])

@router.inline_query()
async def inline_handler(query: InlineQuery):
    # print(file_date_ids[-1])
    # await upload_date()
    await upload_datetime()
    item1 = InlineQueryResultCachedGif(
        id=str(1),
        title='Как же заебал {current_day}',
        # gif_file_id='BAACAgIAAxkDAAN5ZoRC6Z1Hzr1sCgRr-nZ3UV7xHfUAAu1aAAKCliBIvV332wxCEfs1BA'
        gif_file_id=file_date_ids[-1]
    )
    item2 = InlineQueryResultCachedGif(
        id=str(2),
        title='Как же заебал {current_daytime}',
        # gif_file_id='BAACAgIAAxkDAAN5ZoRC6Z1Hzr1sCgRr-nZ3UV7xHfUAAu1aAAKCliBIvV332wxCEfs1BA'
        gif_file_id=file_datetime_ids[-1]
    )
    await bot.answer_inline_query(query.id, results=[item1, item2], cache_time=1)

# async def upload_gif():
#     await upload_date()
#     await upload_datetime()

# print(str(datetime.datetime.now().time()).split(".")[0])

async def upload_datetime():
    global file_datetime_ids
    if not os.path.exists('./new_datetime.gif'):
        date = datetime.date.today()
        time = str(datetime.datetime.now().time()).split(".")[0]
        text = f'Как же заебало {date.day} {months[date.month]} {time}'
        await create_gif(text, "new_datetime.gif")
    gif_file = FSInputFile('./new_datetime.gif')
    msg = await bot.send_animation(chat_id=173202775, animation=gif_file)
    await bot.delete_message(chat_id=173202775, message_id=msg.message_id)
    file_id = msg.animation.file_id
    file_datetime_ids.append(file_id)

async def upload_date():
    global file_date_ids
    # if not os.path.exists('./new_date.gif'):
    date = datetime.date.today()
    text = f'Как же заебало {date.day} {months[date.month]}'
    await create_gif(text, "new_date.gif")
    gif_file = FSInputFile('./new_date.gif')
    msg = await bot.send_animation(chat_id=173202775, animation=gif_file)
    await bot.delete_message(chat_id=173202775, message_id=msg.message_id)
    file_id = msg.animation.file_id
    file_date_ids.append(file_id)

async def start_polling():
    dp.include_routers(router)
    await dp.start_polling(bot)

async def timer():
    global last_day
    global last_time
    await upload_date()
    await upload_datetime()
    while True:
        if datetime.date.today() != last_day:
            last_day = datetime.date.today()
            # date = datetime.date.today()
            # text = f'Как же заебало {date.day} {months[date.month]}'
            # await create_gif(text, "new_date.gif")
            await upload_date()
        if datetime.datetime.now().time() != last_time:
            last_time = datetime.datetime.now().time()
            date = datetime.date.today()
            time = str(datetime.datetime.now().time()).split(".")[0]
            text = f'Как же заебало {date.day} {months[date.month]} {time}'
            await create_gif(text, "new_datetime.gif")
            # await upload_datetime()
        # print(last_time)
        await asyncio.sleep(3)

async def start():
    await asyncio.gather(start_polling(), timer())

if __name__ == "__main__":
    asyncio.run(start())
