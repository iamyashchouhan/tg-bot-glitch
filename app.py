import logging
import re
import requests
import asyncio
import nest_asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from flask import Flask
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from threading import Thread

# Apply fix for nested event loops in Termux
nest_asyncio.apply()

# Flask app setup
app = Flask(__name__)

# Telegram Bot Token fetch function
def get_bot_token():
    try:
        response = requests.get("https://teradisk.xyz/admin/python/token.txt", timeout=10)
        if response.status_code == 200 and response.text.strip():
            return response.text.strip()
        else:
            raise Exception("Failed to fetch token.")
    except Exception as e:
        logging.error(f"Error fetching BOT_TOKEN: {e}")
        return None

# Fetch BOT_TOKEN dynamically
BOT_TOKEN = get_bot_token()
if not BOT_TOKEN:
    logging.error("Bot Token is not available. Exiting.")
    exit(1)  # Exit the program if the token isn't fetched

# Logging Setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Terabox API for URL conversion
TERABOX_API = "https://teradisk.xyz/admin/gen.php?gen_url=true&terabox_url="

# Terabox Regex Pattern
TERABOX_REGEX = r"https?:\/\/(?:www\.)?(?:terabox|1024terabox)\.com\/s\/\S+"

# Fancy Fonts
BOLD = lambda text: f"*{text}*"
ITALIC = lambda text: f"_{text}_"
MONOSPACE = lambda text: f"`{text}`"

# Telegram bot handlers
async def start(update: Update, context: CallbackContext) -> None:
    """Handles /start command"""
    text = f"""
{BOLD("Welcome to the Terabox Link Converter! 🚀")}
{ITALIC("Send me a video URL, and I'll generate a stream link for you.")}
🔹 {BOLD("Supported Links:")}
  - Terabox
  - 1024terabox
📥 {BOLD("Just send me a link, and I'll do the rest!")}
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Processes incoming messages (text, images, videos)"""
    message = update.message
    chat_id = message.chat_id
    text = message.text or message.caption or ""

    text = re.sub(r'https?://t\.me/\S+', '', text)

    # Handle Images & Videos
    if message.video:
        await message.reply_text("🎥 You sent a video! Currently, I only process video links.")
        return

    # Find Terabox links
    links = re.findall(TERABOX_REGEX, text, re.IGNORECASE)

    if not links:
        await message.reply_text("❌ No valid Terabox links found. Please send a correct link.")
        return

    # If the user sent a photo, get the file ID
    photo_id = None
    if message.photo:
        photo = message.photo[-1]  # Get the highest resolution photo
        photo_id = photo.file_id

    # Send a waiting message
    waiting_message = await message.reply_text("🔄 *Generating stream links...*\nPlease wait a moment ⏳", parse_mode=ParseMode.MARKDOWN)

    # Convert Links
    converted_links = {}
    for link in links:
        try:
            response = requests.get(f"{TERABOX_API}{link}", timeout=10)
            if response.status_code == 200 and response.text.strip():
                converted_links[link] = response.text.strip()
        except Exception as e:
            logger.error(f"Error converting link {link}: {e}")

    if not converted_links:
        await waiting_message.edit_text("❌ *Failed to convert links.*\nPlease try again later.", parse_mode=ParseMode.MARKDOWN)
        return

    # Replace original links with converted ones
    final_text = text
    for original, converted in converted_links.items():
        final_text = final_text.replace(original, f"🔗 {(converted)}")

    # If there's no photo, just edit the waiting message with the text
    if not photo_id:
        await waiting_message.edit_text(f"✅ *Here are your converted links:*\n{final_text}", parse_mode=ParseMode.MARKDOWN)
    else:
        # If there's a photo, send the photo with the converted links
        media = InputMediaPhoto(media=photo_id, caption=f"✅ *Here are your converted links:*\n{final_text}", parse_mode=ParseMode.MARKDOWN)
        await waiting_message.edit_media(media)

# Flask route to keep the app alive
@app.route('/')
def home():
    return "Bot is running"

# Run Flask in the background thread
def start_flask():
    app.run(port=5000, use_reloader=False)  # Disable reloader as it's incompatible with threads

# Main function to start the bot
async def main():
    """Main function to start the bot"""
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))

    # Start the bot
    logger.info("Bot is running... 🚀")
    await app.run_polling()

if __name__ == "__main__":
    # Start Flask server in the background
    flask_thread = Thread(target=start_flask)
    flask_thread.start()

    # Start bot with asyncio
    asyncio.run(main())
