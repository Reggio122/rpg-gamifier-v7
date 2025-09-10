# RPG Gamifier — Render Backend (Telegram Reminders + GPT Coach)

Этот бэкенд принимает запросы от фронтенда (GitHub Pages) и:
- отправляет напоминания в Telegram в нужное время;
- по запросу выдаёт идеи от GPT (если указан `OPENAI_API_KEY`).

## 1) Подготовка
- Создайте репозиторий на GitHub и загрузите сюда файлы:
  - `bot.py`
  - `requirements.txt`

## 2) Render — Web Service
1. Зайдите на https://render.com → **New → Web Service**.
2. Выберите репозиторий.
3. Настройки:
   - **Environment:** Python 3
   - **Build Command:**
     ```
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```
     python bot.py
     ```
4. Переменные окружения (**Environment → Add**):
   - `BOT_TOKEN` — токен Telegram‑бота (от @BotFather).
   - `MINIAPP_URL` — URL вашего фронтенда на GitHub Pages (например, `https://username.github.io/Gamefibot/`).
   - `OPENAI_API_KEY` — *опционально*, если хотите GPT‑советы.

После деплоя Render даст URL вида `https://YOUR-APP.onrender.com`.

## 3) Подключение фронтенда
В `index.html` фронтенда укажите адрес API (замените заглушку):
```html
<script>const BOT_API_BASE = "https://YOUR-APP.onrender.com";</script>
```

## 4) Проверка
- Откройте фронтенд, добавьте задачу с датой/временем — в логах Render вы увидите регистрацию напоминания, а в момент Х придёт сообщение в Telegram.
- Кнопка «Совет» вызовет `/coach`; если указан `OPENAI_API_KEY`, вернутся идеи от GPT.

## 5) Важно
- Бэкенд использует **long polling** Telegram + **Flask** на одном процессе; это подходит для Render Web Service.
- Напоминания работают в фоновом потоке. Если инстанс «спит» на бесплатном тарифе, доставка может задержаться. Для гарантированной доставки используйте Always On или внешний аптайм‑пингер.
- Фронтенд должен отправлять `when` как **ISO 8601 UTC** (`new Date().toISOString()`), так код корректно сравнивает время.

## 6) Команды бота
- `/start` — присылает кнопку для открытия Mini App (ссылку из `MINIAPP_URL`).

Готово! После этого ваш фронт и бэк будут соединены.
