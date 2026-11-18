import asyncio
import os
import unittest
from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

from PIL import Image

import main

os.environ["DB_PATH"] = ":memory:"


class BotTest(unittest.TestCase):
    def test_render_keeps_animation(self):
        with Image.open(main.HERE / "shelby.gif") as src:
            n_frames, duration = src.n_frames, src.info["duration"]
        with Image.open(BytesIO(main.render("Как же заебало 31 сентября 23:59:59"))) as gif:
            self.assertEqual(gif.format, "GIF")
            self.assertEqual(gif.n_frames, n_frames)
            self.assertEqual(gif.info["duration"], duration)
            self.assertEqual(gif.width, main.WIDTH)

    def test_same_caption_is_uploaded_once(self):
        bot = AsyncMock()
        bot.send_animation.return_value = SimpleNamespace(
            message_id=7, animation=SimpleNamespace(file_id="FILE")
        )

        async def ask_twice_concurrently():
            return await asyncio.gather(*(main.file_id_for("подпись", bot, 42) for _ in range(2)))

        self.assertEqual(asyncio.run(ask_twice_concurrently()), ["FILE", "FILE"])
        bot.send_animation.assert_awaited_once()
        bot.delete_message.assert_awaited_once_with(42, 7)

    def test_find_zone(self):
        self.assertEqual(main.find_zone("europe/belgrade"), "Europe/Belgrade")
        self.assertEqual(main.find_zone("+3"), "Etc/GMT-3")
        self.assertEqual(main.find_zone(" UTC -5:00 "), "Etc/GMT+5")
        for junk in ("", "/start tz", "+99", "../../etc/passwd", "Москва"):
            self.assertIsNone(main.find_zone(junk))

    def test_user_zone_is_stored_per_user(self):
        main._db().execute("INSERT OR REPLACE INTO zones VALUES (1, 'Etc/GMT-9')")
        self.assertEqual(main.now_for(1).utcoffset(), timedelta(hours=9))
        self.assertEqual(main.now_for(2).utcoffset(), main.datetime.now().astimezone().utcoffset())


if __name__ == "__main__":
    unittest.main()
