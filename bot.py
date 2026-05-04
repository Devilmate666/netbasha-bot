import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN    = "8782083692:AAF6RRfvHYTZd0kPZUDL1ttGeAtVt-JWG5E"
CHANNEL  = "-1003989153913"
APP_URL  = "https://t.me/NetbashaBot/netbasha"
CHAN_URL = "https://t.me/netbasha"

MSGS = [
    "🎬 *أفلام ومسلسلات*\n\nشاهد أحدث الأفلام والمسلسلات\n\n📱 [فتح نت باشا](" + APP_URL + ")",
    "📺 *قنوات مباشرة*\n\nبث مباشر للقنوات العربية\n\n📱 [فتح نت باشا](" + APP_URL + ")",
    "⚽ *رياضة*\n\nنتائج المباريات وأخبار الرياضة\n\n📱 [فتح نت باشا](" + APP_URL + ")",
    "🎌 *أنمي*\n\nأحدث حلقات الأنمي المترجمة\n\n📱 [فتح نت باشا](" + APP_URL + ")",
    "🎵 *موسيقى*\n\nأحدث الأغاني والألبومات\n\n📱 [فتح نت باشا](" + APP_URL + ")",
    "🍲 *طبخ*\n\nوصفات شهية من المطبخ العربي\n\n📱 [فتح نت باشا](" + APP_URL + ")",
    "💊 *صحة*\n\nنصائح طبية وتمارين لياقة\n\n📱 [فتح نت باشا](" + APP_URL + ")",
    "🌐 *تواصل اجتماعي*\n\nمنصات التواصل في مكان واحد\n\n📱 [فتح نت باشا](" + APP_URL + ")",
    "📚 *كتب*\n\nأحدث الكتب والروايات\n\n📱 [فتح نت باشا](" + APP_URL + ")",
    "💻 *تقنية*\n\nأخبار التقنية والذكاء الاصطناعي\n\n📱 [فتح نت باشا](" + APP_URL + ")",
]

rotate_idx = 0

# ─── /start command ────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 فتح نت باشا", url=APP_URL)],
        [InlineKeyboardButton("📢 قناة الأخبار", url=CHAN_URL)],
    ])
    await update.message.reply_text(
        "🎬 *نت باشا*\n\nأفلام • قنوات • رياضة • أنمي • موسيقى • طبخ • صحة • كتب • تقنية\n\n👇 اختر من القائمة",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# ─── rotating channel message ──────────────────────────────────────────────
async def send_rotating(context: ContextTypes.DEFAULT_TYPE):
    global rotate_idx
    msg = MSGS[rotate_idx % len(MSGS)]
    rotate_idx += 1
    await context.bot.send_message(
        chat_id=CHANNEL,
        text=msg,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

# ─── main ──────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.job_queue.run_repeating(send_rotating, interval=21600, first=10)
    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
