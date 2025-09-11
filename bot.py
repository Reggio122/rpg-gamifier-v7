# v15 Clean Backend: Flask + Telegram Bot + Assistant + Smart Reminders
import os, json, time, threading
from datetime import datetime, timedelta, timezone
from flask import Flask, request, jsonify
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.constants import ParseMode

TOKEN = os.getenv('BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
MINIAPP_URL = os.getenv('MINIAPP_URL', 'https://example.com')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

USE_GPT = bool(OPENAI_API_KEY)
if USE_GPT:
    try:
        import openai
        openai.api_key = OPENAI_API_KEY
    except Exception:
        USE_GPT = False

DATA = {"reminders": []}  # in-memory for simplicity

app = Flask(__name__)
bot = Bot(TOKEN)

@app.get('/health')
def health(): return 'ok', 200

@app.post('/assistant')
def assistant():
    body = request.get_json(silent=True) or {}
    mode = body.get('mode','breakdown'); text = body.get('text','')
    if USE_GPT:
        try:
            prompt = {
                "breakdown": f"Разбей цель на 5-7 коротких шагов. Цель: {text}. Список без префиксов.",
                "week": f"Сформируй план на неделю (5-7 пунктов) для цели: {text}. Список без префиксов.",
                "motivate": f"Дай 5-7 коротких мотивационных подсказок в RPG‑стиле, учитывая цель: {text}. Список без префиксов."
            }[mode]
            resp = openai.chat.completions.create(model="gpt-4o-mini",
                messages=[{"role":"user","content": prompt}], max_tokens=300, temperature=0.7)
            out = resp.choices[0].message.content
            items = [s.strip('-• ').strip() for s in out.split('\n') if s.strip()][:7]
            return jsonify({"items": items})
        except Exception:
            pass
    # fallback
    defaults = {
        "breakdown": ["Подготовить план","Сделать первый шаг","Определить дедлайн","Настроить напоминание","Проверить прогресс"],
        "week": ["Пн: 200 слов","Вт: 15 мин чтения","Ср: аудиозапись","Чт: монтаж","Пт: публикация","Вс: обзор"],
        "motivate": ["Начни с малого","Сделай 1% прогресс","Ради себя будущего","Герой выполняет квесты","Ты можешь больше"]
    }
    return jsonify({"items": defaults.get(mode, defaults["breakdown"])})

@app.post('/remind_smart')
def remind_smart():
    body = request.get_json(silent=True) or {}
    task = body.get('task') or {}
    chat_id = str(body.get('chat_id','default'))
    when = task.get('when'); repeat = task.get('repeat','')
    if not when: return jsonify({"ok":False,"error":"no when"}), 400
    DATA["reminders"].append({"chat_id":chat_id, "title": task.get('title','Квест'), "when": when, "repeat": repeat})
    return jsonify({"ok":True})

def loop():
    while True:
        try:
            now = datetime.now(timezone.utc).timestamp()
            keep=[]
            for r in DATA["reminders"]:
                try:
                    ts = datetime.fromisoformat(r["when"].replace('Z','+00:00')).timestamp()
                except Exception:
                    ts = None
                if ts and ts <= now:
                    kb = [[
                        {"text":"✅ Выполнено","callback_data":"done"},
                        {"text":"⏳ Отложить","callback_data":"snooze"},
                        {"text":"✖️ Пропустить","callback_data":"skip"},
                    ]]
                    try:
                        bot.send_message(int(r["chat_id"]), text=f"⚔️ Герой, пора: *{r['title']}*",
                                         reply_markup={"inline_keyboard": kb}, parse_mode=ParseMode.MARKDOWN)
                    except Exception: pass
                    if r.get('repeat') in ('DAILY','WEEKLY'):
                        try:
                            dt = datetime.fromisoformat(r['when'].replace('Z','+00:00'))
                            dt = dt + (timedelta(days=1) if r['repeat']=='DAILY' else timedelta(weeks=1))
                            r['when'] = dt.astimezone(timezone.utc).isoformat(); keep.append(r)
                        except Exception: pass
                else:
                    keep.append(r)
            DATA["reminders"]=keep
        except Exception: pass
        time.sleep(30)

async def start(update, _):
    button = InlineKeyboardButton("Открыть RPG Gamifier", web_app=WebAppInfo(url=MINIAPP_URL))
    await update.message.reply_text("Добро пожаловать в гильдию! 🐉", reply_markup=InlineKeyboardMarkup([[button]]))

def main():
    app_ = ApplicationBuilder().token(TOKEN).build()
    app_.add_handler(CommandHandler('start', start))
    # start Flask + reminder loop
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()
    threading.Thread(target=loop, daemon=True).start()
    app_.run_polling()

if __name__ == "__main__":
    main()
