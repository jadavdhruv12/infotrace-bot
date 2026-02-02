import os
import time
import sqlite3
import secrets
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= ENV TOKEN =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env variable missing")

ADMIN_IDS = [8558491786]

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
    left = int((start + dur) - time.time())
    if left <= 0:
        return "EXPIRED"
    m = left // 60
    h = m // 60
    d = h // 24
    if d > 0: return f"{d} days"
    if h > 0: return f"{h} hours"
    return f"{m} minutes"

# ================= COMMANDS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    cur.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (uid, time.time()))
    db.commit()

    await update.message.reply_text(
        "🔐 Personal Access Required\n\n"
        "Enter your license key\n"
        "Example:\n"
        "/key INFO-ABC123XYZ456\n\n"
        "📩 Contact Admin 👉 @Iamdhruv011"
    )

async def admincmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "/genkey\n/showkeys\n/activeusers\n/user\n/blockkey KEY\n/resume KEY"
    )

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    key = "INFO-" + secrets.token_hex(6).upper()
    duration = 24 * 60 * 60
    cur.execute("INSERT INTO licenses VALUES (?,?,?,?,?)",
                (key, None, duration, None, 0))
    db.commit()
    await update.message.reply_text(f"✅ Key Generated:\n\n`{key}`", parse_mode="Markdown")

async def key_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return
    key = context.args[0]
    uid = update.effective_user.id

    cur.execute("SELECT * FROM licenses WHERE key=?", (key,))
    row = cur.fetchone()
    if not row:
        await update.message.reply_text("❌ Invalid key")
        return

    _, start, dur, user, blocked = row
    if blocked:
        await update.message.reply_text("🚫 Key blocked")
        return
    if user and user != uid:
        await update.message.reply_text("🔒 Key already used")
        return

    if not start:
        start = time.time()
        user = uid
        cur.execute("UPDATE licenses SET start=?, user=? WHERE key=?",
                    (start, user, key))
        db.commit()

    await update.message.reply_text(
        f"✅ Access Granted\n⏳ Time Left: {time_left(start, dur)}"
    )

async def showkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    cur.execute("SELECT * FROM licenses")
    rows = cur.fetchall()
    text = ""
    for r in rows:
        status = "BLOCKED" if r[4] else time_left(r[1], r[2]) if r[1] else "UNUSED"
        text += f"{r[0]} → {status}\n"
    await update.message.reply_text(text or "No keys")

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admincmd", admincmd))
app.add_handler(CommandHandler("genkey", genkey))
app.add_handler(CommandHandler("key", key_cmd))
app.add_handler(CommandHandler("showkeys", showkeys))

app.run_polling()