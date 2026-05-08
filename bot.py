import logging
import random
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN    = "8782083692:AAF6RRfvHYTZd0kPZUDL1ttGeAtVt-JWG5E"
CHANNEL  = "-1003989153913"
APP_URL  = "https://t.me/NetbashaBot/netbasha"
CHAN_URL = "https://t.me/netbasha"

# ─── Multiple varied messages per category ─────────────────────────────────────
CATEGORY_MSGS = {
    "movies": [
        "🎬 *الأفلام الجديدة وصلت!*\n\nالتشكيلة تتجدد باستمرار — أكشن، رومانسي، رعب، ودراما. شاهد ما يناسبك ولا تفوّت شيئاً 🍿\n\n👉 [افتح نت باشا الآن](" + APP_URL + ")",
        "🎥 *عندك وقت فراغ؟*\n\nعندنا أحدث الأفلام بجودة عالية ومترجمة بدقة. ما تحتاج تدور بعيد 😉\n\n👉 [شاهد الأفلام على نت باشا](" + APP_URL + ")",
        "🏆 *أفلام الأسبوع الأكثر مشاهدة*\n\nهوليوود، بوليوود، وأفلام عربية — كلها في مكان واحد 🎞️\n\n👉 [نت باشا — ما تفوّتك](" + APP_URL + ")",
        "🌙 *سهرة حلوة تبدأ باختيار الفيلم الصح*\n\nمن الكوميديا للإثارة — ابدأ المشاهدة الآن بدون إعلانات 🎬\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🎭 *مسلسلات أم أفلام؟ عندنا الاثنين!*\n\nكل شيء في مكان واحد بنقرة واحدة — بدون اشتراكات متعددة 📲\n\n👉 [جرّب الآن](" + APP_URL + ")",
    ],
    "live": [
        "📺 *البث المباشر شغّال الحين!*\n\nقنوات عربية وعالمية بجودة HD — بدون تقطيع ولا تأخير 🔴\n\n👉 [نت باشا — بث حي](" + APP_URL + ")",
        "🔴 *LIVE الآن على نت باشا*\n\nأخبار، رياضة، ومنوعات — كل القنوات المهمة بثها مباشر طوال اليوم 📡\n\n👉 [شاهد البث المباشر](" + APP_URL + ")",
        "📡 *تابع قنواتك المفضلة بدون انقطاع*\n\nعشرات القنوات العربية والإخبارية — مستمرة على مدار الساعة 🕐\n\n👉 [افتح نت باشا الآن](" + APP_URL + ")",
        "🌍 *قنوات من كل العالم العربي*\n\nمن السعودية لمصر للمغرب — كل القنوات بين يديك 📱\n\n👉 [شاهد على نت باشا](" + APP_URL + ")",
    ],
    "sports": [
        "⚽ *الدوريات الكبرى — تابعها معنا!*\n\nنتائج، ترتيب، وأهداف من أهم المباريات — محدّث أولاً بأول ⚡\n\n👉 [نت باشا — الرياضة](" + APP_URL + ")",
        "🏆 *من فاز؟ اعرف النتيجة الآن!*\n\nالبريميرليغ، الليغا، السيريا A، والدوري السعودي — كل النتائج في ثوانٍ ⏱️\n\n👉 [تابع الرياضة على نت باشا](" + APP_URL + ")",
        "🎯 *أخبار الملاعب الساخنة اليوم*\n\nصفقات، إصابات، وتصريحات المدربين — لا تفوّت أي خبر رياضي 🔥\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🏅 *رياضتك كلها في مكان واحد*\n\nكرة قدم، كرة سلة، تنس، وأكثر — ما تفوّت تفصيلة من دوريك المفضل 📊\n\n👉 [نت باشا — الرياضة](" + APP_URL + ")",
    ],
    "anime": [
        "🎌 *أنمي جديد مترجم وصل!*\n\nأحدث حلقات الموسم — مترجمة بعناية وبجودة عالية 🌸\n\n👉 [شاهد على نت باشا](" + APP_URL + ")",
        "⚔️ *الحلقة الجديدة نزلت!*\n\nOne Piece؟ Demon Slayer؟ Jujutsu Kaisen؟ — كلها عندنا محدّثة 🔥\n\n👉 [نت باشا — عالم الأنمي](" + APP_URL + ")",
        "🌙 *دوّر على أنمي جديد تتابعه*\n\nأكبر مكتبة أنمي عربي مترجم — كلاسيكي وحديث. ابدأ رحلتك الآن 🎴\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "✨ *أنمي الموسم الحالي — ما تفوّت حلقة*\n\nالإضافات منتظمة أسبوعياً — تابع أبطالك على نت باشا 🗡️\n\n👉 [شاهد الأنمي الآن](" + APP_URL + ")",
    ],
    "music": [
        "🎵 *موسيقى تناسب كل لحظة*\n\nمن الأغاني العربية الحديثة للكلاسيكيات الخالدة — اختار مزاجك 🎶\n\n👉 [نت باشا — الموسيقى](" + APP_URL + ")",
        "🎤 *أغاني جديدة كل يوم!*\n\nأحدث إصدارات النجوم العرب والعالميين — بجودة صوت رائعة 🔊\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🎸 *ما هو مزاجك اليوم؟*\n\nشعبي، طرب، هيب هوب، بوب — عندنا كل الأنواع لكل الأوقات 🌅\n\n👉 [شاهد واسمع على نت باشا](" + APP_URL + ")",
        "🎼 *ألبومات ومقاطع جديدة وصلت*\n\nابقَ على اطلاع بآخر إصدارات فنانيك المفضلين 🎹\n\n👉 [اسمع الآن](" + APP_URL + ")",
    ],
    "cooking": [
        "🍲 *وصفة اليوم — جرّبها الليلة!*\n\nأكلات شهية وسهلة التحضير من المطبخ العربي — خطوة بخطوة مع الصور 👨‍🍳\n\n👉 [نت باشا — الطبخ](" + APP_URL + ")",
        "🥘 *ما تعرف ماذا تطبخ اليوم؟*\n\nمئات الوصفات من كل المطابخ العربية — سريعة وسهلة ومضمونة 😋\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🍽️ *وصفات شامية وخليجية ومغاربية*\n\nمن الحلويات للأطباق الرئيسية — كل الوصفات في مكان واحد 🫕\n\n👉 [شاهد الوصفات على نت باشا](" + APP_URL + ")",
        "👩‍🍳 *أسرار الطهاة المحترفين*\n\nأضف نكهة جديدة لمطبخك مع نصائح الشيفات الكبار 🌿\n\n👉 [تعلّم الطبخ الآن](" + APP_URL + ")",
    ],
    "health": [
        "💊 *نصيحتك الصحية لليوم*\n\nعادات بسيطة تغير حياتك — تغذية، نوم، ولياقة. ابدأ اليوم 💪\n\n👉 [نت باشا — الصحة](" + APP_URL + ")",
        "🏃 *تمارين تناسب كل المستويات*\n\nمبتدئ أو محترف — عندنا برامج لكل الأهداف. صحة أفضل تبدأ من هنا 🎯\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🥗 *الصحة في تفاصيل صغيرة*\n\nنصائح تغذية، مكملات، وروتين يومي — متخصصون يشرحون لك ببساطة 🌱\n\n👉 [نت باشا — عِش بصحة](" + APP_URL + ")",
        "😴 *صحتك أهم — تابع نصائح الخبراء*\n\nمن إدارة الضغط للنوم الصحي — دليلك الصحي الكامل على نت باشا 🩺\n\n👉 [اعرف أكثر على نت باشا](" + APP_URL + ")",
    ],
    "social": [
        "🌐 *كل منصاتك في مكان واحد*\n\nتيك توك، انستغرام، يوتيوب — تابع أهم المحتوى العربي بدون تطبيقات كثيرة 📲\n\n👉 [نت باشا — التواصل](" + APP_URL + ")",
        "📱 *ترندات اليوم على نت باشا*\n\nأكثر المحتوى انتشاراً في العالم العربي — فيديوهات، ميمز، وأخبار الإنترنت 🔥\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🤳 *المؤثرون والمبدعون العرب*\n\nتابع أبرز صناع المحتوى في مكان واحد — بدون فوضى ولا تشتت 🎯\n\n👉 [نت باشا — المحتوى العربي](" + APP_URL + ")",
    ],
    "books": [
        "📚 *كتاب يغير حياتك — ابدأ الآن*\n\nروايات، كتب تطوير ذات، وأعمال أدبية عربية وعالمية 📖\n\n👉 [نت باشا — الكتب](" + APP_URL + ")",
        "🔖 *أحدث الكتب والروايات وصلت*\n\nإصدارات جديدة من أبرز الكتّاب العرب والعالميين — قراءة ممتعة بانتظارك 🌙\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "📝 *لمحبي القراءة فقط 📚*\n\nمكتبة ضخمة من الروايات التاريخية، الخيال العلمي، والتطوير الشخصي ✨\n\n👉 [اكتشف المكتبة الآن](" + APP_URL + ")",
        "🧠 *اقرأ أكثر، تعلّم أكثر*\n\nكتب الذكاء الاصطناعي، الاقتصاد، وعلم النفس — وسّع مداركك مع نت باشا 💡\n\n👉 [شاهد الكتب على نت باشا](" + APP_URL + ")",
    ],
    "tech": [
        "💻 *أخبار التقنية اليوم*\n\nذكاء اصطناعي، هواتف جديدة، وتطبيقات ثورية — كل ما يهمك في عالم التكنولوجيا 🤖\n\n👉 [نت باشا — التقنية](" + APP_URL + ")",
        "🤖 *الذكاء الاصطناعي يتطور كل يوم!*\n\nأحدث أخبار ChatGPT وGemini وثورة الـ AI — مبسّطة بالعربي 🧠\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "📱 *أحدث الهواتف والأجهزة*\n\nمراجعات ومقارنات قبل ما تشتري — رأي المتخصصين على نت باشا 🔍\n\n👉 [نت باشا — التقنية](" + APP_URL + ")",
        "⚡ *تطبيقات ستغير طريقة عملك*\n\nأفضل الأدوات المجانية التي يستخدمها المحترفون يومياً 🛠️\n\n👉 [اكتشف على نت باشا](" + APP_URL + ")",
    ],
}

STATE_FILE = "/tmp/bot_state.json"

# ─── State helpers ──────────────────────────────────────────────────────────────
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def pick_message(category: str, state: dict) -> str:
    """Pick a non-recently-used message for a category, cycling when all are used."""
    msgs = CATEGORY_MSGS[category]
    used: list = state.get(category, [])
    available = [i for i in range(len(msgs)) if i not in used]
    if not available:
        used = []
        available = list(range(len(msgs)))
    idx = random.choice(available)
    used.append(idx)
    state[category] = used
    return msgs[idx]

def build_schedule() -> list:
    """
    GitHub runs the bot for ~4.7 hours (timeout 17000s ≈ 283 min).
    We send 5 messages: at 2, 62, 122, 182, 242 minutes.
    Each run picks 5 random categories in a shuffled order.
    """
    categories = list(CATEGORY_MSGS.keys())
    random.shuffle(categories)
    return categories[:5]

# ─── Handlers ───────────────────────────────────────────────────────────────────
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

# ─── Main ────────────────────────────────────────────────────────────────────────
def main():
    schedule = build_schedule()
    state = load_state()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    async def post_init(application: Application):
        """Register all timed jobs after the event loop is running."""
        first_delay = 120  # 2 minutes after bot starts

        for i, category in enumerate(schedule):
            delay = first_delay + (i * 3600)  # sends at: 2, 62, 122, 182, 242 min

            def make_callback(cat):
                async def callback(ctx: ContextTypes.DEFAULT_TYPE):
                    msg = pick_message(cat, state)
                    save_state(state)
                    await ctx.bot.send_message(
                        chat_id=CHANNEL,
                        text=msg,
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                    logger.info(f"Sent [{cat}] message.")
                return callback

            application.job_queue.run_once(make_callback(category), when=delay)
            logger.info(f"Scheduled [{category}] at {delay // 60} min mark.")

    app.post_init = post_init

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message"])

if __name__ == "__main__":
    main()
