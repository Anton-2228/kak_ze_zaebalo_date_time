import asyncio
import datetime
import uuid

from PIL import Image, ImageDraw, ImageSequence, ImageFont

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, InlineQuery, InlineQueryResultCachedGif


API_TOKEN = ''

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

router = Router()

width = 350

file_ids = []
last_day = datetime.date.today()

months = {
    1: "января", 2: "февраля", 3: "марта",
    4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября",
    10: "октября", 11: "ноября", 12: "декабря"
}

async def create_gif():
    with Image.open('shelby.gif') as img:
        frames = []
        for frame in ImageSequence.Iterator(img):
            frame = frame.convert("RGBA")

            koef = frame.height / frame.width
            frame = frame.resize((width, int(width*koef)))
            frame_draw = ImageDraw.Draw(frame)

            offset = width * 0.1

            font = ImageFont.truetype("Roboto-Black.ttf", 25, encoding='UTF-8')
            pos = (offset, frame.height*0.75)
            date = datetime.date.today()
            text = f'Как же заебало {date.day} {months[date.month]}'
            left, top, right, bottom = frame_draw.textbbox(pos, text, font=font)
            frame_draw.rectangle((left-5, top-5, right+5, bottom+5), fill="black")
            frame_draw.text(pos, text, font=font, fill="white")

            frames.append(frame.convert("P", palette=Image.ADAPTIVE))

        frames[0].save("new.gif", save_all=True, loop=0, append_images=frames[1:], optimize=False, duration=img.info['duration'])

@router.inline_query()
async def inline_handler(query: InlineQuery):
    print(file_ids[-1])
    item1 = InlineQueryResultCachedGif(
        id=str(uuid.uuid4()),
        title='Как же заебал {current_day}',
        # gif_file_id='BAACAgIAAxkDAAN5ZoRC6Z1Hzr1sCgRr-nZ3UV7xHfUAAu1aAAKCliBIvV332wxCEfs1BA'
        gif_file_id=file_ids[-1]
    )
    await bot.answer_inline_query(query.id, results=[item1])

async def upload_gif():
    global file_ids
    await create_gif()
    gif_file = FSInputFile('./new.gif')
    msg = await bot.send_animation(chat_id=173202775, animation=gif_file)
    file_id = msg.animation.file_id
    file_ids.append(file_id)


async def start_polling():
    dp.include_routers(router)
    await dp.start_polling(bot)

async def timer():
    global last_day
    await upload_gif()
    while True:
        if datetime.date.today() != last_day:
            last_day = datetime.date.today()
            await upload_gif()
        await asyncio.sleep(5)

async def start():
    await asyncio.gather(start_polling(), timer())

if __name__ == "__main__":
    asyncio.run(start())
