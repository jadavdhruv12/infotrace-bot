import os
import time
import sqlite3
import secrets
import telebot

# ================= ENV =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env variable missing")

ADMIN_IDS = [8558491786]  # apna telegram id

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

# ================= USER =================
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

@bot.message_handler(commands=['key'])
def key_cmd(message):
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ Usage: `/key YOUR_KEY`")
        return

    key = parts[1].upper()
    uid = message.from_user.id

    cur.execute("SELECT * FROM licenses WHERE key=?", (key,))
    row = cur.fetchone()

    if not row:
        bot.reply_to(message, "❌ Invalid key")
        return

    _, start, dur, user, blocked = row

    if blocked:
        bot.reply_to(message, "🚫 This key is blocked")
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
        f"✅ *Access Granted*\n"
        f"⏳ Time Left: `{time_left(start, dur)}`"
    )

# ================= ADMIN =================
@bot.message_handler(commands=['admincmd'])
def admincmd(message):
    if not is_admin(message.from_user.id):
        return

    bot.reply_to(
        message,
        "👑 *Admin Commands*\n\n"
        "/genkey\n"
        "/showkeys\n"
        "/blockkey KEY\n"
        "/resume KEY\n"
        "/dashboard"
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

    bot.reply_to(
        message,
        f"✅ *New Key Generated*\n\n`{key}`"
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

    text = "🔑 *All License Keys*\n\n"
    for r in rows:
        status = "🚫 BLOCKED" if r[4] else time_left(r[1], r[2])
        text += f"`{r[0]}` → {status}\n"

    bot.reply_to(message, text)

@bot.message_handler(commands=['blockkey'])
def blockkey(message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) != 2:
        return

    key = parts[1].upper()
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

    key = parts[1].upper()
    cur.execute("UPDATE licenses SET blocked=0 WHERE key=?", (key,))
    db.commit()

    bot.reply_to(message, f"✅ Key resumed: `{key}`")

# ================= DASHBOARD =================
@bot.message_handler(commands=['dashboard'])
def dashboard(message):
    if not is_admin(message.from_user.id):
        return

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM licenses")
    total_keys = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM licenses WHERE blocked=1")
    blocked = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM licenses WHERE start IS NOT NULL")
    active = cur.fetchone()[0]

    bot.reply_to(
        message,
        "📊 *INFO TRACE – ADMIN DASHBOARD*\n\n"
        f"👥 Users: `{users}`\n"
        f"🔑 Total Keys: `{total_keys}`\n"
        f"✅ Active Keys: `{active}`\n"
        f"🚫 Blocked Keys: `{blocked}`\n\n"
        "⚙️ System: `ONLINE`"
    )

# ================= RUN =================
print("Bot running...")
bot.infinity_polling()
