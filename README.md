# kak_ze_zaebalo_date_time

Инлайн-бот для Telegram: набираете `@имя_бота` в любом чате и получаете гифку с Шелби
и подписью «Как же заебало 18 ноября» — с текущей датой или с датой и временем.

## Запуск

1. Создайте бота у [@BotFather](https://t.me/BotFather) и включите ему инлайн-режим командой `/setinline`.
2. Напишите боту `/start` в личку. Туда он будет на секунду присылать гифки: Telegram
   отдаёт `file_id` для инлайн-ответа только после отправки файла в какой-нибудь чат.
3. Скопируйте `.env.example` в `.env` и заполните:
   - `BOT_TOKEN` — токен от BotFather;
   - `STORAGE_CHAT_ID` — ваш user id (подскажет, например, [@userinfobot](https://t.me/userinfobot));
   - `TZ` — часовой пояс подписи, по умолчанию `Europe/Moscow`.
4. Запустите: `docker compose up -d --build`

Логи: `docker compose logs -f`

## Тесты

```
pip install -r requirements.txt
python -m unittest
```
