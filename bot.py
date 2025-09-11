# v16 — backend на Webhook
import json, time, threading
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

TOKEN = "8483792538:AAG4PPtToaX7pQbzEtLkmfscm9xiH8CSab4"
OPENAI_API_KEY = "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"
MINIAPP_URL = "https://reggio122.github.io/Gamefibot/"
BACKEND_URL = "https://rpg-gamifier-v7-1.onrender.com"

USE_GPT = True
try:
    import openai
    openai.api_key = OPENAI_API_KEY
except Exception:
    USE_GPT = False

DATA = {"reminders": [], "last_chat_id": None}

app = Flask(__name__)
CORS(app)
bot = Bot(TOKEN)

@app.get("/health")
def health():
    return "ok", 200

@app.post("/assistant")
def assistant():
    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "breakdown")
    text = body.get("text", "")
    if USE_GPT:
        try:
            prompt = {
                "breakdown": f"Разбей цель на 5-7 шагов. Цель: {text}",
                "week": f"Составь план на неделю для цели: {text}",
                "motivate": f"Дай 5 RPG-стиля мотивационных фраз для цели: {text}"
            }[mode]
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            out = resp.choices[0].message.content
            items = [s.strip("-• ").strip() for s in out.split("\n") if s.strip()][:7]
            return jsonify({"items": items})
        except Exception:
            pass
    defaults = {
        "breakdown": ["Подготовить план", "Сделать первый шаг", "Определить дедлайн", "Настроить напоминание", "Проверить прогресс"],
        "week": ["Пн: 200 слов", "Вт: 15 мин чтения", "Ср: запись", "Чт: монтаж", "Пт: публикация"],
        "motivate": ["Начни с малого", "Сделай 1% прогресс", "Ради себя будущего", "Герой выполняет квесты", "Ты можешь больше"]
    }
    return jsonify({"items": defaults.get(mode, defaults["breakdown"])})

@app.post("/remind_smart")
def remind_smart():
    body = request.get_json(silent=True) or {}
    task = body.get("task") or {}
    chat_id = str(body.get("chat_id", "default"))
    if chat_id == "default" and DATA.get("last_chat_id"):
        chat_id = DATA["last_chat_id"]
    when = task.get("when")
    repeat = body.get("repeat", "")
    if not when:
        return jsonify({"ok": False, "error": "no when"}), 400
    DATA["reminders"].append({"chat_id": chat_id, "title": task.get("title", "Квест"), "when": when, "repeat": repeat})
    return jsonify({"ok": True})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    DATA["last_chat_id"] = str(update.effective_chat.id)
    button = InlineKeyboardButton("Открыть RPG Gamifier", web_app=WebAppInfo(url=MINIAPP_URL))
    await update.message.reply_text("Добро пожаловать в гильдию! 🐉", reply_markup=InlineKeyboardMarkup([[button]]))

def loop():
    while True:
        try:
            now = datetime.now(timezone.utc).timestamp()
            keep = []
            for r in DATA["reminders"]:
                try:
                    ts = datetime.fromisoformat(r["when"].replace("Z", "+00:00")).timestamp()
                except Exception:
                    ts = None
                if ts and ts <= now and r.get("chat_id"):
                    kb = [[
                        {"text": "✅ Выполнено", "callback_data": "done"},
                        {"text": "⏳ Отложить", "callback_data": "snooze"},
                        {"text": "✖️ Пропустить", "callback_data": "skip"},
                    ]]
                    try:
                        bot.send_message(
                            int(r["chat_id"]),
                            text=f"⚔️ Герой, пора: *{r['title']}*",
                            reply_markup={"inline_keyboard": kb},
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception:
                        pass
                    if r.get("repeat") in ("DAILY", "WEEKLY"):
                        try:
                            dt = datetime.fromisoformat(r["when"].replace("Z", "+00:00"))
                            dt = dt + (timedelta(days=1) if r["repeat"] == "DAILY" else timedelta(weeks=1))
                            r["when"] = dt.astimezone(timezone.utc).isoformat()
                            keep.append(r)
                        except Exception:
                            pass
                else:
                    keep.append(r)
            DATA["reminders"] = keep
        except Exception:
            pass
        time.sleep(30)

from telegram.ext import Application

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))

@app.post("/webhook")
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put(update)
    return "ok"

def main():
    url = f"{BACKEND_URL}/webhook"
    bot.set_webhook(url)
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
