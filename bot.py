# RPG Gamifier v14 — Backend (Render)
import os, json, time, threading
from datetime import datetime, timedelta, timezone
from flask import Flask

TOKEN = os.getenv('BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
MINIAPP_URL = "https://reggio122.github.io/Gamefibot/"
OPENAI_KEY = os.getenv('OPENAI_API_KEY', '')

app = Flask(__name__)

@app.get('/health')
def health():
    return 'ok', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
