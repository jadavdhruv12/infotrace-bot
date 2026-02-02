import os
import time
import sqlite3
import secrets
import telebot
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ================= ENV TOKEN =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env variable missing")

ADMIN_IDS = [8558491786]  # apna telegram user id

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= DATABASE =================
db = sqlite3.connect("license.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS licenses (
    key TEXT PRIMARY KEY,
    start REAL,
    duration INTEGER,
    user INTEGER,
    blocked INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user INTEGER PRIMARY KEY,
    first_seen REAL
)
""")
db.commit()

# ================= HELPERS =================
def is_admin(uid):
    return uid in ADMIN_IDS

def time_left(start, dur):
    if not start:
        return "UNUSED"
    left = int((start + dur) - time.time())
    if left <= 0:
        return "EXPIRED"
    m = left // 60
    h = m // 60
    d = h // 24
    if d > 0:
        return f"{d} days"
    if h > 0:
        return f"{h} hours"
    return f"{m} minutes"

# ================= BOT COMMANDS =================

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (uid, time.time()))
    db.commit()

    bot.reply_to(
        message,
        "🔐 *Personal Access Required*\n\n"
        "Enter your license key\n"
        "Example:\n"
        "`/key INFO-ABC123XYZ456`\n\n"
        "📩 Contact Admin 👉 @Iamdhruv011"
    )

@bot.message_handler(commands=['admincmd'])
def admincmd(message):
    if not is_admin(message.from_user.id):
        return
    bot.reply_to(
        message,
        "👑 *Admin Panel*\n\n"
        "/genkey – Generate key\n"
        "/showkeys – Show all keys\n"
        "/blockkey KEY – Block key\n"
        "/resume KEY – Resume key"
    )

@bot.message_handler(commands=['genkey'])
def genkey(message):
    if not is_admin(message.from_user.id):
        return
    key = "INFO-" + secrets.token_hex(6).upper()
    duration = 24 * 60 * 60  # 1 day
    cur.execute(
        "INSERT INTO licenses VALUES (?,?,?,?,?)",
        (key, None, duration, None, 0)
    )
    db.commit()
    bot.reply_to(message, f"✅ *Key Generated:*\n\n`{key}`")

@bot.message_handler(commands=['key'])
def key_cmd(message):
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /key YOURKEY")
        return

    key = parts[1]
    uid = message.from_user.id

    cur.execute("SELECT * FROM licenses WHERE key=?", (key,))
    row = cur.fetchone()
    if not row:
        bot.reply_to(message, "❌ Invalid key")
        return

    _, start, dur, user, blocked = row

    if blocked:
        bot.reply_to(message, "🚫 Key blocked")
        return

    if user and user != uid:
        bot.reply_to(message, "🔒 Key already used")
        return

    if not start:
        start = time.time()
        user = uid
        cur.execute(
            "UPDATE licenses SET start=?, user=? WHERE key=?",
            (start, user, key)
        )
        db.commit()

    bot.reply_to(
        message,
        f"✅ *Access Granted*\n⏳ Time Left: `{time_left(start, dur)}`"
    )

@bot.message_handler(commands=['showkeys'])
def showkeys(message):
    if not is_admin(message.from_user.id):
        return
    cur.execute("SELECT * FROM licenses")
    rows = cur.fetchall()
    if not rows:
        bot.reply_to(message, "No keys found")
        return

    text = "🔑 *All Keys*\n\n"
    for r in rows:
        status = "BLOCKED" if r[4] else time_left(r[1], r[2])
        text += f"`{r[0]}` → {status}\n"

    bot.reply_to(message, text)

@bot.message_handler(commands=['blockkey'])
def blockkey(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2:
        return
    key = parts[1]
    cur.execute("UPDATE licenses SET blocked=1 WHERE key=?", (key,))
    db.commit()
    bot.reply_to(message, f"🚫 Key blocked: `{key}`")

@bot.message_handler(commands=['resume'])
def resume(message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2:
        return
    key = parts[1]
    cur.execute("UPDATE licenses SET blocked=0 WHERE key=?", (key,))
    db.commit()
    bot.reply_to(message, f"✅ Key resumed: `{key}`")

# ================= WEBSITE (CRON / KEEP ALIVE) =================

def run_web():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("""
            InfoTrace Bot is Running 🚀
            """.encode("utf-8"))
            <html>
            <head><title>InfoTrace</title></head>
            <body style="background:#0f172a;color:#22d3ee;
            display:flex;justify-content:center;align-items:center;height:100vh;">
            <h1>InfoTrace Bot is Running 🚀</h1>
            </body>
            </html>
            """)

    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

# ================= RUN =================
print("InfoTrace bot running...")

threading.Thread(target=run_web).start()
bot.infinity_polling()
