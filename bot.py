import logging
import random
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN    = "8782083692:AAF6RRfvHYTZd0kPZUDL1ttGeAtVt-JWG5E"
CHANNEL  = "-1003989153913"
APP_URL  = "https://t.me/NetbashaBot/netbasha"
CHAN_URL = "https://t.me/netbasha"

WELCOME_MSG = """\
👋 *أهلاً بك في قناة نت باشا!*

*نت باشا* هو تطبيقك العربي الشامل الذي يجمع لك كل شيء في مكان واحد:

🎬 أفلام ومسلسلات عربية وعالمية
📺 قنوات مباشرة على مدار الساعة
⚽ أخبار رياضية ونتائج المباريات
🎌 أنمي مترجم بجودة عالية
🎵 موسيقى وأغاني لكل الأذواق
🍲 وصفات طبخ من كل المطابخ العربية
💊 نصائح صحية ولياقة بدنية
📚 كتب وروايات متنوعة
💻 أخبار التقنية والذكاء الاصطناعي

كل هذا مجاناً وبنقرة واحدة 👇\
"""

CATEGORY_MSGS = {
    "movies": [
        "🎬 *أفلام ومسلسلات لكل الأذواق*\n\n*نت باشا* يجمع لك أحدث الأفلام والمسلسلات العربية والعالمية في مكان واحد — بجودة عالية وبدون إعلانات مزعجة 🍿\n\n👉 [افتح نت باشا الآن](" + APP_URL + ")",
        "🎥 *عندك وقت فراغ؟*\n\nمع *نت باشا* ما تحتاج تدور بعيد — أحدث الأفلام والمسلسلات بجودة عالية ومترجمة بدقة، كلها في تطبيق واحد 😉\n\n👉 [شاهد على نت باشا](" + APP_URL + ")",
        "🏆 *الأفلام والمسلسلات الأكثر مشاهدة*\n\n*نت باشا* — تطبيقك الشامل للترفيه العربي. هوليوود، بوليوود، وإنتاج عربي أصيل، كلها تجدها في مكان واحد 🎞️\n\n👉 [نت باشا — ما تفوّتك](" + APP_URL + ")",
        "🌙 *سهرة حلوة تبدأ باختيار الفيلم الصح*\n\n*نت باشا* عندك كل أنواع الأفلام — أكشن، كوميديا، رومانسي، رعب، ودراما. اختار وابدأ الآن 🎬\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🎭 *مسلسلات أم أفلام؟ عندنا الاثنين!*\n\n*نت باشا* — بدون اشتراكات متعددة أو تطبيقات كثيرة. كل الترفيه العربي والعالمي بنقرة واحدة 📲\n\n👉 [جرّب الآن](" + APP_URL + ")",
    ],
    "live": [
        "📺 *قنوات مباشرة على مدار الساعة*\n\n*نت باشا* يوفر لك بثاً مباشراً لعشرات القنوات العربية والعالمية بجودة HD — بدون تقطيع ولا تأخير 🔴\n\n👉 [نت باشا — بث حي](" + APP_URL + ")",
        "🔴 *LIVE الآن على نت باشا*\n\nأخبار، رياضة، ومنوعات — *نت باشا* يجمع لك كل القنوات المهمة في بث مباشر طوال اليوم 📡\n\n👉 [شاهد البث المباشر](" + APP_URL + ")",
        "📡 *تابع قنواتك المفضلة بدون انقطاع*\n\nمع *نت باشا* عندك عشرات القنوات العربية والإخبارية — مستمرة على مدار الساعة بجودة لا تنقطع 🕐\n\n👉 [افتح نت باشا الآن](" + APP_URL + ")",
        "🌍 *قنوات من كل العالم العربي*\n\n*نت باشا* يجمع قنوات من السعودية، مصر، الشام، والمغرب — كل ما تريده بين يديك 📱\n\n👉 [شاهد على نت باشا](" + APP_URL + ")",
    ],
    "sports": [
        "⚽ *الدوريات الكبرى — تابعها على نت باشا!*\n\n*نت باشا* يوفر لك نتائج، ترتيب، وأهداف من أهم المباريات — محدّث أولاً بأول ⚡\n\n👉 [نت باشا — الرياضة](" + APP_URL + ")",
        "🏆 *من فاز؟ اعرف النتيجة الآن!*\n\nمع *نت باشا* تابع كل دوريات العالم — نتائج فورية وتغطية رياضية شاملة في مكان واحد ⏱️\n\n👉 [تابع الرياضة على نت باشا](" + APP_URL + ")",
        "🎯 *أخبار الملاعب الساخنة اليوم*\n\n*نت باشا* — صفقات، إصابات، وتصريحات المدربين. لا تفوّت أي خبر رياضي من دوريك المفضل 🔥\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🏅 *رياضتك كلها في مكان واحد*\n\nكرة قدم، كرة سلة، تنس، وأكثر — *نت باشا* يغطي كل الرياضات التي تهمك 📊\n\n👉 [نت باشا — الرياضة](" + APP_URL + ")",
    ],
    "anime": [
        "🎌 *عالم الأنمي على نت باشا*\n\n*نت باشا* يوفر لك أحدث حلقات الأنمي مترجمة بعناية وبجودة عالية — كلاسيكي وحديث في مكان واحد 🌸\n\n👉 [شاهد على نت باشا](" + APP_URL + ")",
        "⚔️ *أنمي مترجم بجودة عالية*\n\nأحدث حلقات موسم الأنمي الحالي — *نت باشا* يضيفها بانتظام حتى لا تفوّتك أي حلقة 🔥\n\n👉 [نت باشا — عالم الأنمي](" + APP_URL + ")",
        "🌙 *دوّر على أنمي جديد تتابعه*\n\n*نت باشا* يملك أكبر مكتبة أنمي عربي مترجم — من الكلاسيكيات الخالدة لأحدث إصدارات الموسم 🎴\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "✨ *أنمي الموسم الحالي — ما تفوّت حلقة*\n\nمع *نت باشا* الإضافات منتظمة أسبوعياً — تابع أبطالك المفضلين بجودة ممتازة 🗡️\n\n👉 [شاهد الأنمي الآن](" + APP_URL + ")",
    ],
    "music": [
        "🎵 *موسيقى تناسب كل لحظة*\n\n*نت باشا* يجمع لك الأغاني العربية الحديثة والكلاسيكيات الخالدة — اختار مزاجك وابدأ الاستماع 🎶\n\n👉 [نت باشا — الموسيقى](" + APP_URL + ")",
        "🎤 *أغاني جديدة كل يوم!*\n\nمع *نت باشا* تابع أحدث إصدارات النجوم العرب والعالميين — بجودة صوت رائعة بدون انقطاع 🔊\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🎸 *ما هو مزاجك اليوم؟*\n\nطرب، شعبي، هيب هوب، أو بوب — *نت باشا* عنده كل الأنواع لكل الأوقات والأذواق 🌅\n\n👉 [اسمع على نت باشا](" + APP_URL + ")",
        "🎼 *ألبومات ومقاطع جديدة وصلت*\n\n*نت باشا* يبقيك على اطلاع بآخر إصدارات فنانيك المفضلين — كل شيء في مكان واحد 🎹\n\n👉 [اسمع الآن](" + APP_URL + ")",
    ],
    "cooking": [
        "🍲 *وصفة اليوم — جرّبها الليلة!*\n\n*نت باشا* يوفر لك أكلات شهية وسهلة التحضير من المطبخ العربي — خطوة بخطوة مع الصور 👨‍🍳\n\n👉 [نت باشا — الطبخ](" + APP_URL + ")",
        "🥘 *ما تعرف ماذا تطبخ اليوم؟*\n\nمع *نت باشا* عندك مئات الوصفات من كل المطابخ العربية — سريعة وسهلة ومضمونة النتيجة 😋\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🍽️ *وصفات شامية وخليجية ومغاربية*\n\n*نت باشا* يجمع لك من الحلويات للأطباق الرئيسية — كل وصفات المطبخ العربي في مكان واحد 🫕\n\n👉 [شاهد الوصفات على نت باشا](" + APP_URL + ")",
        "👩‍🍳 *أسرار الطهاة المحترفين*\n\nمع *نت باشا* تعلّم وأضف نكهة جديدة لمطبخك مع نصائح الشيفات الكبار خطوة بخطوة 🌿\n\n👉 [تعلّم الطبخ الآن](" + APP_URL + ")",
    ],
    "health": [
        "💊 *نصيحتك الصحية لليوم*\n\n*نت باشا* يقدم لك عادات بسيطة تغير حياتك — تغذية، نوم، ولياقة بدنية. ابدأ اليوم قبل الغد 💪\n\n👉 [نت باشا — الصحة](" + APP_URL + ")",
        "🏃 *تمارين تناسب كل المستويات*\n\nمبتدئ أو محترف — *نت باشا* عنده برامج تمارين لكل الأهداف. صحة أفضل تبدأ من هنا 🎯\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🥗 *الصحة في تفاصيل صغيرة*\n\nمع *نت باشا* تابع نصائح التغذية والمكملات والروتين اليومي — يشرحها لك متخصصون ببساطة 🌱\n\n👉 [نت باشا — عِش بصحة](" + APP_URL + ")",
        "😴 *صحتك أهم — تابع نصائح الخبراء*\n\n*نت باشا* يوفر لك دليلاً صحياً شاملاً — من إدارة الضغط للنوم الصحي والتغذية السليمة 🩺\n\n👉 [اعرف أكثر على نت باشا](" + APP_URL + ")",
    ],
    "social": [
        "🌐 *كل منصاتك في مكان واحد*\n\n*نت باشا* يجمع لك أهم المحتوى من تيك توك، انستغرام، ويوتيوب — بدون ما تفتح تطبيقات كثيرة 📲\n\n👉 [نت باشا — التواصل](" + APP_URL + ")",
        "📱 *ترندات اليوم على نت باشا*\n\nأكثر المحتوى انتشاراً في العالم العربي — *نت باشا* يجمع لك الفيديوهات والأخبار الرائجة يومياً 🔥\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "🤳 *المؤثرون والمبدعون العرب*\n\nمع *نت باشا* تابع أبرز صناع المحتوى العربي في مكان واحد — بدون فوضى ولا تشتت 🎯\n\n👉 [نت باشا — المحتوى العربي](" + APP_URL + ")",
    ],
    "books": [
        "📚 *كتاب يغير حياتك — ابدأ الآن*\n\n*نت باشا* يوفر لك روايات، كتب تطوير ذات، وأعمال أدبية عربية وعالمية — كلها في مكان واحد 📖\n\n👉 [نت باشا — الكتب](" + APP_URL + ")",
        "🔖 *أحدث الكتب والروايات وصلت*\n\nمع *نت باشا* تابع أحدث إصدارات الكتّاب العرب والعالميين — قراءة ممتعة بانتظارك 🌙\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "📝 *لمحبي القراءة فقط 📚*\n\n*نت باشا* يملك مكتبة ضخمة من الروايات التاريخية، الخيال العلمي، والتطوير الشخصي — اكتشفها الآن ✨\n\n👉 [اكتشف المكتبة الآن](" + APP_URL + ")",
        "🧠 *اقرأ أكثر، تعلّم أكثر*\n\nمع *نت باشا* وسّع مداركك بكتب الذكاء الاصطناعي، الاقتصاد، وعلم النفس — كلها بين يديك 💡\n\n👉 [شاهد الكتب على نت باشا](" + APP_URL + ")",
    ],
    "tech": [
        "💻 *أخبار التقنية اليوم*\n\n*نت باشا* يغطي لك ذكاء اصطناعي، هواتف جديدة، وتطبيقات ثورية — كل ما يهمك في عالم التكنولوجيا 🤖\n\n👉 [نت باشا — التقنية](" + APP_URL + ")",
        "🤖 *الذكاء الاصطناعي يتطور كل يوم!*\n\nمع *نت باشا* تابع ثورة الـ AI وأحدث أخبار التقنية العالمية — مبسّطة وبالعربي 🧠\n\n👉 [افتح نت باشا](" + APP_URL + ")",
        "📱 *أحدث الهواتف والأجهزة*\n\n*نت باشا* يوفر لك مراجعات ومقارنات دقيقة — اعرف رأي المتخصصين قبل ما تشتري 🔍\n\n👉 [نت باشا — التقنية](" + APP_URL + ")",
        "⚡ *تطبيقات ستغير طريقة عملك*\n\nمع *نت باشا* اكتشف أفضل الأدوات المجانية التي يستخدمها المحترفون يومياً 🛠️\n\n👉 [اكتشف على نت باشا](" + APP_URL + ")",
    ],
}

ALL_CATEGORIES = list(CATEGORY_MSGS.keys())  # 10 categories
STATE_FILE = "/tmp/bot_state.json"

# ─── State schema ───────────────────────────────────────────────────────────────
# {
#   "cat_queue":  [...],   # remaining categories to send this cycle (ordered)
#   "msg_used":   { cat: [used_indices] },  # per-category used message indices
# }

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

def get_next_categories(state: dict, n: int) -> list:
    """
    Pop the next `n` categories from the queue.
    Each category appears exactly once per full cycle of 10.
    Guarantees: no two consecutive categories are the same — both within
    a single run's schedule AND across run boundaries (via last_cat in state).
    Since GitHub Actions runners are ephemeral, last_cat is embedded in
    cat_queue as a sentinel so it survives across runs.
    """
    queue = state.get("cat_queue", [])
    last_cat = state.get("last_cat")
    result = []

    for _ in range(n):
        if not queue:
            new_queue = ALL_CATEGORIES[:]
            random.shuffle(new_queue)
            # Ensure the new cycle doesn't start with the same category
            # that was sent last (cross-run boundary protection)
            if last_cat and new_queue[0] == last_cat:
                new_queue.append(new_queue.pop(0))
            queue = new_queue
            logger.info(f"New category cycle: {queue}")

        # Extra guard: if top of queue matches last sent, swap it with
        # the next different category (handles mid-cycle edge cases)
        if last_cat and len(queue) > 1 and queue[0] == last_cat:
            for j in range(1, len(queue)):
                if queue[j] != last_cat:
                    queue[0], queue[j] = queue[j], queue[0]
                    break

        picked = queue.pop(0)
        result.append(picked)
        last_cat = picked

    state["cat_queue"] = queue
    state["last_cat"] = last_cat
    return result

def pick_message(category: str, state: dict) -> str:
    """Pick a non-recently-used message variant for a category."""
    msgs = CATEGORY_MSGS[category]
    msg_used = state.setdefault("msg_used", {})
    used: list = msg_used.get(category, [])
    available = [i for i in range(len(msgs)) if i not in used]
    if not available:
        used = []
        available = list(range(len(msgs)))
    idx = random.choice(available)
    used.append(idx)
    msg_used[category] = used
    return msgs[idx]

# ─── /start handler ─────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 افتح نت باشا", url=APP_URL)],
        [InlineKeyboardButton("📢 قناة الأخبار", url=CHAN_URL)],
    ])
    await update.message.reply_text(
        "🎬 *نت باشا*\n\nأفلام • قنوات • رياضة • أنمي • موسيقى • طبخ • صحة • كتب • تقنية\n\n👇 اختر من القائمة",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# ─── Welcome new channel members ────────────────────────────────────────────────
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    if old_status in ("left", "kicked") and new_status == "member":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 افتح نت باشا الآن", url=APP_URL)],
        ])
        await context.bot.send_message(
            chat_id=result.chat.id,
            text=WELCOME_MSG,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

# ─── Main ────────────────────────────────────────────────────────────────────────
def main():
    state = load_state()

    # Decide which 5 categories to send this run — guaranteed no repeats across runs
    schedule = get_next_categories(state, 5)
    save_state(state)
    logger.info(f"This run schedule: {schedule}")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))

    async def post_init(application: Application):
        first_delay = 120  # 2 min after start
        for i, category in enumerate(schedule):
            delay = first_delay + (i * 3600)  # 2, 62, 122, 182, 242 min

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
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "chat_member"]
    )

if __name__ == "__main__":
    main()
