import os
import logging
from datetime import datetime, timedelta

from telegram import Update, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext
)

# =======================
# CONFIG
# =======================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_USERNAME = "Iamdhruv011"
BOT_NAME = "InfoTrace"
KEY_PREFIX = "INF"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in environment variables")

# =======================
# LOGGING
# =======================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# =======================
# IN-MEMORY DATA
# (later DB laga sakta hai)
# =======================

LICENSE_KEYS = {}
ACTIVE_USERS = set()
BLOCKED_KEYS = set()

# =======================
# UTIL FUNCTIONS
# =======================

def generate_key():
    import random
    import string
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
    return f"{KEY_PREFIX}-{rand}"

# =======================
# USER COMMANDS
# =======================

def start(update: Update, context: CallbackContext):
    text = (
        "🔐 *Personal Access Required*\n\n"
        "Enter your license key\n"
        "Example:\n"
        f"`/key {KEY_PREFIX}-ABC123XYZ456`\n\n"
        f"📩 Contact Admin 👉 @{ADMIN_USERNAME}"
    )
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def key_cmd(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("❌ Please provide a license key.")
        return

    key = context.args[0].strip().upper()

    if key in BLOCKED_KEYS:
        update.message.reply_text("🚫 This key is blocked.")
        return

    if key not in LICENSE_KEYS:
        update.message.reply_text("❌ Invalid license key.")
        return

    expiry = LICENSE_KEYS[key]
    if datetime.utcnow() > expiry:
        update.message.reply_text("⌛ License expired.")
        return

    ACTIVE_USERS.add(update.effective_user.id)
    update.message.reply_text("✅ Access granted. Welcome to InfoTrace.")

# =======================
# ADMIN COMMANDS
# =======================

def is_admin(update: Update):
    return update.effective_user.username == ADMIN_USERNAME

def admincmd(update: Update, context: CallbackContext):
    if not is_admin(update):
        update.message.reply_text("❌ Admin only.")
        return

    text = (
        "👑 *Admin Licence Commands*\n\n"
        "/genkey – Generate new licence key\n"
        "/showkeys – View licence keys\n"
        "/activeusers – View active users\n"
        "/blockkey <KEY> – Block licence key\n"
    )
    update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def genkey(update: Update, context: CallbackContext):
    if not is_admin(update):
        return

    key = generate_key()
    expiry = datetime.utcnow() + timedelta(days=30)
    LICENSE_KEYS[key] = expiry

    update.message.reply_text(
        f"✅ *New Key Generated*\n\n"
        f"`{key}`\n"
        f"🕒 Valid till: {expiry.strftime('%Y-%m-%d')}",
        parse_mode=ParseMode.MARKDOWN
    )

def showkeys(update: Update, context: CallbackContext):
    if not is_admin(update):
        return

    if not LICENSE_KEYS:
        update.message.reply_text("No keys found.")
        return

    msg = "🔑 *All Licence Keys*\n\n"
    for k, v in LICENSE_KEYS.items():
        msg += f"`{k}` → {v.strftime('%Y-%m-%d')}\n"

    update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

def activeusers(update: Update, context: CallbackContext):
    if not is_admin(update):
        return

    update.message.reply_text(f"👥 Active Users: {len(ACTIVE_USERS)}")

def blockkey(update: Update, context: CallbackContext):
    if not is_admin(update):
        return

    if not context.args:
        update.message.reply_text("Usage: /blockkey KEY")
        return

    key = context.args[0].upper()
    BLOCKED_KEYS.add(key)
    update.message.reply_text(f"🚫 Key blocked: `{key}`", parse_mode=ParseMode.MARKDOWN)

# =======================
# MAIN
# =======================

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # User commands
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("key", key_cmd))

    # Admin commands
    dp.add_handler(CommandHandler("admincmd", admincmd))
    dp.add_handler(CommandHandler("genkey", genkey))
    dp.add_handler(CommandHandler("showkeys", showkeys))
    dp.add_handler(CommandHandler("activeusers", activeusers))
    dp.add_handler(CommandHandler("blockkey", blockkey))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
