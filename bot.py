# RPG Gamifier — Render Backend (Reminders + GPT Coach + Telegram Bot)
# Run with: python bot.py
import os, json, time, threading
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler

# --- Config via environment ---
TOKEN = os.getenv('BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
MINIAPP_URL = os.getenv('MINIAPP_URL', 'https://your-gh-username.github.io/rpg-gamifier/')
DATA_FILE = 'data_render.json'
OPENAI_KEY = os.getenv('OPENAI_API_KEY', '')

# --- Optional OpenAI ---
USE_GPT = bool(OPENAI_KEY)
if USE_GPT:
    try:
        import openai
        openai.api_key = OPENAI_KEY
    except Exception:
        USE_GPT = False

# --- Simple storage ---
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        DATA = json.load(f)
else:
    DATA = {'users':{}, 'reminders': []}  # reminders: [{chat_id, title, when_iso}]

def save():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(DATA, f, ensure_ascii=False, indent=2)

# --- App / Bot ---
app = Flask(__name__)
bot = Bot(TOKEN)

@app.get('/health')
def health():
    return 'ok', 200

@app.post('/register_reminder')
def register_reminder():
    """
    Body: { chat_id: string/int, task: { title: str, XP: int, when: ISO8601 } }
    'when' must be ISO 8601 with timezone. Frontend uses new Date().toISOString() (UTC Z).
    """
    body = request.get_json(silent=True) or {}
    chat_id = str(body.get('chat_id','default'))
    t = body.get('task') or {}
    when = t.get('when')
    if when:
        DATA['reminders'].append({'chat_id': chat_id, 'title': t.get('title','Задание'), 'when': when})
        save()
        return jsonify({"ok": True, "scheduled": when})
    return jsonify({"ok": False, "error": "no 'when' provided"}), 400

@app.post('/coach')
def coach():
    """
    Body: { chat_id, prompt, level, stats }
    Returns: { ideas: [str, ...] }
    """
    body = request.get_json(silent=True) or {}
    prompt = body.get('prompt', 'Дай 4 коротких задания на сегодня для начинающего контент‑мейкера на русском.')
    if USE_GPT:
        try:
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content": prompt}],
                max_tokens=220,
                temperature=0.7,
            )
            text = resp.choices[0].message.content
            ideas = [line.strip('-• ').strip() for line in text.split('\n') if line.strip()][:4]
            return jsonify({"ideas": ideas})
        except Exception as e:
            # fall through to empty ideas
            pass
    return jsonify({"ideas": []})

# --- Reminder delivery loop ---
def reminder_loop():
    while True:
        try:
            now = datetime.now(timezone.utc).timestamp()
            keep=[]
            for r in DATA.get('reminders', []):
                try:
                    ts = datetime.fromisoformat(r['when'].replace('Z','+00:00')).timestamp()
                except Exception:
                    ts = None
                if ts and ts <= now:
                    try:
                        bot.send_message(int(r['chat_id']), text=f"⏰ Напоминание: {r['title']}")
                    except Exception:
                        pass
                else:
                    keep.append(r)
            DATA['reminders'] = keep
            save()
        except Exception:
            pass
        time.sleep(30)  # check every 30s

# --- Telegram commands ---
async def start_cmd(update, _):
    button = InlineKeyboardButton("Открыть RPG Gamifier", web_app=WebAppInfo(url=MINIAPP_URL))
    await update.message.reply_text("Добро пожаловать в гильдию! 🐉", reply_markup=InlineKeyboardMarkup([[button]]))

def run():
    app_ = ApplicationBuilder().token(TOKEN).build()
    app_.add_handler(CommandHandler('start', start_cmd))
    # Flask + reminder loop in background threads
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()
    threading.Thread(target=reminder_loop, daemon=True).start()
    app_.run_polling()

if __name__ == "__main__":
    run()
