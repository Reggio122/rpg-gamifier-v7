# RPG Gamifier v14 — Backend (Prod)
import os, threading
from flask import Flask
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler

TOKEN = os.getenv('BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
MINIAPP_URL = "https://reggio122.github.io/Gamefibot/"

app = Flask(__name__)
bot = Bot(TOKEN)

@app.get('/health')
def health(): return 'ok', 200

async def start_cmd(update, _):
    button = InlineKeyboardButton("Открыть RPG Gamifier", web_app=WebAppInfo(url=MINIAPP_URL))
    await update.message.reply_text("Добро пожаловать в гильдию! 🐉", reply_markup=InlineKeyboardMarkup([[button]]))

def run():
    app_ = ApplicationBuilder().token(TOKEN).build()
    app_.add_handler(CommandHandler('start', start_cmd))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000), daemon=True).start()
    app_.run_polling()

if __name__ == "__main__":
    run()
