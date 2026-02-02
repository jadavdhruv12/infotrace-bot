import os
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Render ENV variable
START_TIME = time.time()

KEYS = {}
ACTIVE_USERS = set()
ADMIN_IDS = {8558491786}  # <-- apna Telegram ID daal

# ================= UTILS =================

def uptime():
    seconds = int(time.time() - START_TIME)
    mins, sec = divmod(seconds, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs}h {mins}m {sec}s"

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ================= COMMANDS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 *Personal Access Required*\n\n"
        "Enter your license key\n"
        "Example:\n"
        "`/key INFO-ABC123XYZ456`",
        parse_mode="Markdown"
    )

async def key_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /key <LICENSE_KEY>")
        return

    key = context.args[0].upper()

    if key not in KEYS:
        await update.message.reply_text("❌ Invalid key")
        return

    if KEYS[key]["blocked"]:
        await update.message.reply_text("🚫 This key is blocked")
        return

    user_id = update.effective_user.id
    ACTIVE_USERS.add(user_id)

    await update.message.reply_text("✅ Access granted")

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /genkey <KEY>")
        return

    key = context.args[0].upper()
    KEYS[key] = {"blocked": False}

    await update.message.reply_text(f"🔑 Key generated:\n`{key}`", parse_mode="Markdown")

async def blockkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /blockkey <KEY>")
        return

    key = context.args[0].upper()
    if key in KEYS:
        KEYS[key]["blocked"] = True
        await update.message.reply_text("🔒 Key blocked")
    else:
        await update.message.reply_text("❌ Key not found")

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🟢 *SYSTEM OK*\n\n"
        f"⏱ Uptime: `{uptime()}`\n"
        f"👥 Active Users: `{len(ACTIVE_USERS)}`\n"
        f"🔑 Total Keys: `{len(KEYS)}`",
        parse_mode="Markdown"
    )

# ================= MAIN =================

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set in environment variables")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("key", key_cmd))
    app.add_handler(CommandHandler("genkey", genkey))
    app.add_handler(CommandHandler("blockkey", blockkey))
    app.add_handler(CommandHandler("health", health))

    print("✅ InfoTrace Bot Started")
    app.run_polling()

if __name__ == "__main__":
    main()
