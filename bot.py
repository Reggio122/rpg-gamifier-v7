# RPG Gamifier v8 — Telegram Bot + Flask API + optional GPT coach
import os, json, time, threading
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = os.getenv('BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
MINIAPP_URL = os.getenv('MINIAPP_URL', 'https://your-gh-username.github.io/rpg-gamifier-v8/')
DATA_FILE = 'data_v8.json'

USE_GPT = bool(os.getenv('OPENAI_API_KEY'))
try:
    if USE_GPT:
        import openai
        openai.api_key = os.getenv('OPENAI_API_KEY')
except Exception:
    USE_GPT = False

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        DATA = json.load(f)
else:
    DATA = {'users':{}}

def ensure_user(cid):
    cid = str(cid)
    if cid not in DATA['users']:
        DATA['users'][cid] = {"avatar":"hero1.png","stats":{"STR":0,"INT":0,"CHA":0},"xpLog":[],"tasks":[],"achievements":[]}
        save()
    return DATA['users'][cid]

def save():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(DATA, f, ensure_ascii=False, indent=2)

app = Flask(__name__)
bot = Bot(TOKEN)

@app.route('/health')
def health(): return 'ok', 200

@app.post('/register_reminder')
def register_reminder():
    body = request.get_json() or {}
    chat_id = str(body.get('chat_id','default'))
    t = body.get('task')
    user = ensure_user(chat_id)
    if t:
        user['tasks'].append(t); save()
    return jsonify({"ok":True})

@app.post('/task_completed')
def task_completed():
    body = request.get_json() or {}
    chat_id = str(body.get('chat_id','default'))
    t = body.get('task') or {}
    user = ensure_user(chat_id)
    xp = int(t.get('XP',0))
    if xp>0:
        user['xpLog'].append({"ts": int(time.time()*1000), "amount": xp, "note": "MiniApp: "+t.get('title','')})
        save()
        try: bot.send_message(int(chat_id), text=f"⚔️ Квест выполнен: {t.get('title','')} • +{xp} XP")
        except: pass
    return jsonify({"ok":True})

@app.post('/set_avatar')
def set_avatar():
    body = request.get_json() or {}
    chat_id = str(body.get('chat_id','default'))
    avatar = body.get('avatar','hero1.png')
    user = ensure_user(chat_id)
    user['avatar'] = avatar; save()
    return jsonify({"ok":True})

@app.post('/coach')
def coach():
    body = request.get_json() or {}
    level = body.get('level',1); stats = body.get('stats',{}); backlog = body.get('backlog',[])
    if USE_GPT:
        try:
            prompt = f"User level {level}, stats {stats}. Backlog: {[b.get('title') if isinstance(b,dict) else b for b in backlog]}. Suggest 4 short actionable tasks for a content creator in Russian with XP value hints."
            resp = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":prompt}], max_tokens=180)
            text = resp.choices[0].message.content
            ideas = [line.strip('-• ').strip() for line in text.split('\n') if line.strip()][:4]
            return jsonify({"ideas": ideas})
        except Exception:
            pass
    ideas = ["⚡ 15 минут чтения (+10 XP)","✍️ 200 слов черновика (+10 XP)","🎥 30 минут монтажа (+20 XP)","📣 Запланировать пост (+10 XP)"]
    return jsonify({"ideas": ideas})

# Telegram
async def start_cmd(update, context):
    button = InlineKeyboardButton("Открыть RPG Gamifier", web_app=WebAppInfo(url=MINIAPP_URL))
    await update.message.reply_text("Добро пожаловать в гильдию! 🐉", reply_markup=InlineKeyboardMarkup([[button]]))

async def add_cmd(update, context):
    chat_id = update.message.chat_id
    text = " ".join(context.args)
    parts = text.split('|')
    title = parts[0].strip() if parts else 'Новый квест'
    try: xp = int(parts[1].strip()) if len(parts)>1 else 10
    except: xp = 10
    when = parts[2].strip() if len(parts)>2 else None
    user = ensure_user(chat_id)
    user['tasks'].append({"title":title, "XP":xp, "when":when, "done":False})
    save()
    await update.message.reply_text(f"Квест добавлен: {title} (+{xp} XP){' ⏰ '+when if when else ''}")

def run_bot():
    app_ = ApplicationBuilder().token(TOKEN).build()
    app_.add_handler(CommandHandler('start', start_cmd))
    app_.add_handler(CommandHandler('add', add_cmd))
    app_.run_polling()

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()
    run_bot()
