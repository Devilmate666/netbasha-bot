import logging
import random
import json
import os
import datetime
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN   = "8782083692:AAF6RRfvHYTZd0kPZUDL1ttGeAtVt-JWG5E"
APP_URL = "https://t.me/NetbashaBot/netbasha"

# ─── State file — persists registered users across GitHub Action runs ─────────
STATE_FILE = "/tmp/bot_state.json"

# ─── Category deeplink builder ────────────────────────────────────────────────
# Opens the Mini App directly on a specific category via startapp= parameter.
# Telegram passes it to the WebApp as tg.initDataUnsafe.start_param / tg.startParam.
def category_url(category: str) -> str:
    return f"{APP_URL}?startapp={category}"


# ─── All categories ───────────────────────────────────────────────────────────
CATEGORIES = {
    "movies": {"emoji": "🎬", "label": "أفلام ومسلسلات"},
    "tv":     {"emoji": "📺", "label": "قنوات مباشرة"},
    "sports": {"emoji": "⚽", "label": "رياضة"},
    "anime":  {"emoji": "🎌", "label": "أنمي"},
    "music":  {"emoji": "🎵", "label": "موسيقى"},
    "food":   {"emoji": "🍲", "label": "طبخ ووصفات"},
    "health": {"emoji": "💊", "label": "صحة ولياقة"},
    "social": {"emoji": "📱", "label": "تواصل اجتماعي"},
    "books":  {"emoji": "📚", "label": "كتب وروايات"},
    "tech":   {"emoji": "💻", "label": "تقنية وذكاء اصطناعي"},
}

ALL_CATEGORIES = list(CATEGORIES.keys())


# ─── Notification messages — one per category, each with its own deeplink ─────
# Each message links directly to the relevant category inside the Mini App.
CATEGORY_MSGS: dict[str, list[str]] = {
    "movies": [
        lambda url: (
            f"🎬 *أفلام ومسلسلات لكل الأذواق*\n\n"
            f"*نت باشا* يجمع لك أحدث الأفلام والمسلسلات العربية والعالمية في مكان واحد — بجودة عالية وبدون إعلانات مزعجة 🍿\n\n"
            f"👉 [افتح قسم الأفلام الآن]({url})"
        ),
        lambda url: (
            f"🎥 *عندك وقت فراغ؟*\n\n"
            f"مع *نت باشا* ما تحتاج تدور بعيد — أحدث الأفلام والمسلسلات بجودة عالية ومترجمة بدقة، كلها في تطبيق واحد 😉\n\n"
            f"👉 [شاهد على نت باشا]({url})"
        ),
    ],
    "tv": [
        lambda url: (
            f"📺 *قنوات مباشرة على مدار الساعة*\n\n"
            f"*نت باشا* يوفر لك بثاً مباشراً لعشرات القنوات العربية والعالمية بجودة HD — بدون تقطيع ولا تأخير 🔴\n\n"
            f"👉 [شاهد القنوات الآن]({url})"
        ),
        lambda url: (
            f"🔴 *بث حي الآن على نت باشا*\n\n"
            f"لا تفوّت أي لحظة — عشرات القنوات المباشرة بجودة عالية وبدون انقطاع 📡\n\n"
            f"👉 [افتح القنوات المباشرة]({url})"
        ),
    ],
    "sports": [
        lambda url: (
            f"⚽ *الدوريات الكبرى — تابعها على نت باشا!*\n\n"
            f"*نت باشا* يوفر لك نتائج، ترتيب، وأهداف من أهم المباريات — محدّث أولاً بأول ⚡\n\n"
            f"👉 [افتح قسم الرياضة]({url})"
        ),
        lambda url: (
            f"🏆 *ما تفوّت أي مباراة!*\n\n"
            f"نتائج لحظية، ترتيب الدوريات، وأبرز الأهداف — كل شيء في *نت باشا* 🎯\n\n"
            f"👉 [تابع الرياضة الآن]({url})"
        ),
    ],
    "anime": [
        lambda url: (
            f"🎌 *عالم الأنمي على نت باشا*\n\n"
            f"*نت باشا* يوفر لك أحدث حلقات الأنمي مترجمة بعناية وبجودة عالية — كلاسيكي وحديث في مكان واحد 🌸\n\n"
            f"👉 [افتح قسم الأنمي]({url})"
        ),
        lambda url: (
            f"✨ *حلقات جديدة كل أسبوع على نت باشا*\n\n"
            f"أنمي مترجم للعربية بأعلى جودة — لا تفوّت حلقة 🎌\n\n"
            f"👉 [شاهد الأنمي الآن]({url})"
        ),
    ],
    "music": [
        lambda url: (
            f"🎵 *موسيقى تناسب كل لحظة*\n\n"
            f"*نت باشا* يجمع لك الأغاني العربية الحديثة والكلاسيكيات الخالدة — اختار مزاجك وابدأ الاستماع 🎶\n\n"
            f"👉 [افتح قسم الموسيقى]({url})"
        ),
        lambda url: (
            f"🎧 *مزاجك يحكم — اسمع ما تحب*\n\n"
            f"أغاني عربية وعالمية، قديمة وجديدة — كلها على *نت باشا* 🎼\n\n"
            f"👉 [استمع الآن]({url})"
        ),
    ],
    "food": [
        lambda url: (
            f"🍲 *وصفة اليوم — جرّبها الليلة!*\n\n"
            f"*نت باشا* يوفر لك أكلات شهية وسهلة التحضير من المطبخ العربي — خطوة بخطوة مع الصور 👨‍🍳\n\n"
            f"👉 [افتح قسم الطبخ]({url})"
        ),
        lambda url: (
            f"👨‍🍳 *هل أنت جاهز للطبخ؟*\n\n"
            f"وصفات شهية من كل المطابخ العربية — سهلة وسريعة ومجربة 🍽️\n\n"
            f"👉 [اكتشف الوصفات الآن]({url})"
        ),
    ],
    "health": [
        lambda url: (
            f"💊 *نصيحتك الصحية لليوم*\n\n"
            f"*نت باشا* يقدم لك عادات بسيطة تغير حياتك — تغذية، نوم، ولياقة بدنية. ابدأ اليوم قبل الغد 💪\n\n"
            f"👉 [افتح قسم الصحة]({url})"
        ),
        lambda url: (
            f"💪 *صحتك أهم شيء — خلّها أولويتك*\n\n"
            f"نصائح يومية للتغذية واللياقة والنوم الصحي — كلها على *نت باشا* 🌿\n\n"
            f"👉 [اقرأ نصائح الصحة]({url})"
        ),
    ],
    "social": [
        lambda url: (
            f"🌐 *كل منصاتك في مكان واحد*\n\n"
            f"*نت باشا* يجمع لك أهم المحتوى من تيك توك، انستغرام، ويوتيوب — بدون ما تفتح تطبيقات كثيرة 📲\n\n"
            f"👉 [افتح قسم التواصل]({url})"
        ),
        lambda url: (
            f"📲 *ترند اليوم على نت باشا*\n\n"
            f"أبرز ما يتحدث عنه الناس في تيك توك وانستغرام — كله في مكان واحد 🔥\n\n"
            f"👉 [اكتشف التواصل الاجتماعي]({url})"
        ),
    ],
    "books": [
        lambda url: (
            f"📚 *كتاب يغير حياتك — ابدأ الآن*\n\n"
            f"*نت باشا* يوفر لك روايات، كتب تطوير ذات، وأعمال أدبية عربية وعالمية — كلها في مكان واحد 📖\n\n"
            f"👉 [افتح قسم الكتب]({url})"
        ),
        lambda url: (
            f"📖 *لكل عقل كتاب ينتظره*\n\n"
            f"روايات، تطوير ذات، وأدب عربي وعالمي — اختار كتابك على *نت باشا* ✨\n\n"
            f"👉 [اكتشف الكتب الآن]({url})"
        ),
    ],
    "tech": [
        lambda url: (
            f"💻 *أخبار التقنية اليوم*\n\n"
            f"*نت باشا* يغطي لك ذكاء اصطناعي، هواتف جديدة، وتطبيقات ثورية — كل ما يهمك في عالم التكنولوجيا 🤖\n\n"
            f"👉 [افتح قسم التقنية]({url})"
        ),
        lambda url: (
            f"🤖 *الذكاء الاصطناعي يغير العالم*\n\n"
            f"آخر أخبار التقنية، الهواتف، والـ AI — كلها على *نت باشا* 💡\n\n"
            f"👉 [اقرأ أخبار التقنية]({url})"
        ),
    ],
}


WELCOME_MSG = """\
👋 *أهلاً بك في نت باشا!*

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

ستصلك تنبيهات منتظمة بأبرز ما على المنصة 🔔

نت باشا - كن من يعرف أولاً 👇\
"""


# ─── State helpers ────────────────────────────────────────────────────────────

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


def get_users(state: dict) -> dict:
    """Return {str(chat_id): {joined_at, cat_queue, msg_used}} dict."""
    return state.setdefault("users", {})


def register_user(state: dict, chat_id: int):
    """Record a user the first time they /start. Stores join timestamp."""
    users = get_users(state)
    key = str(chat_id)
    if key not in users:
        users[key] = {
            "joined_at": datetime.datetime.utcnow().isoformat(),
            "cat_queue": [],
            "last_cat": None,
            "msg_used": {},
        }
        logger.info(f"New user registered: {chat_id}")


def pick_next_category(user_data: dict) -> str:
    """Round-robin through all categories for one user, shuffled each cycle."""
    queue    = user_data.get("cat_queue", [])
    last_cat = user_data.get("last_cat")

    if not queue:
        new_queue = ALL_CATEGORIES[:]
        random.shuffle(new_queue)
        # Avoid repeating the last category at the start of a new cycle
        if last_cat and new_queue[0] == last_cat:
            new_queue.append(new_queue.pop(0))
        queue = new_queue

    # Also avoid consecutive repeats mid-queue
    if last_cat and len(queue) > 1 and queue[0] == last_cat:
        for j in range(1, len(queue)):
            if queue[j] != last_cat:
                queue[0], queue[j] = queue[j], queue[0]
                break

    picked = queue.pop(0)
    user_data["cat_queue"] = queue
    user_data["last_cat"]  = picked
    return picked


def build_message(category: str, user_data: dict) -> str:
    """Pick a message variant for the category (no repeats until all used)."""
    msg_list = CATEGORY_MSGS[category]
    msg_used = user_data.setdefault("msg_used", {})
    used: list = msg_used.get(category, [])
    available  = [i for i in range(len(msg_list)) if i not in used]
    if not available:
        used = []
        available = list(range(len(msg_list)))
    idx = random.choice(available)
    used.append(idx)
    msg_used[category] = used

    url = category_url(category)
    return msg_list[idx](url)


# ─── Job: send one notification to all registered users ──────────────────────

async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Called by the job queue every hour. Sends one per-category message to each user."""
    state = load_state()
    users = get_users(state)
    if not users:
        logger.info("No users to notify yet.")
        save_state(state)
        return

    for chat_id_str, user_data in list(users.items()):
        chat_id  = int(chat_id_str)
        category = pick_next_category(user_data)
        msg      = build_message(category, user_data)
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            logger.info(f"Notified user {chat_id} → [{category}]")
        except Exception as e:
            logger.warning(f"Failed to notify {chat_id}: {e}")

    save_state(state)


# ─── /start handler ───────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state   = load_state()

    is_new = str(chat_id) not in get_users(state)
    register_user(state, chat_id)
    save_state(state)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 افتح نت باشا", url=APP_URL)],
    ])
    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )

    if is_new:
        # Schedule the first notification 1 hour after /start, then every hour
        # We use run_once so we don't duplicate if the user /starts again
        context.job_queue.run_once(
            _first_notification,
            when=3600,          # 1 hour delay
            chat_id=chat_id,
            name=f"first_{chat_id}",
        )
        logger.info(f"First notification for {chat_id} scheduled in 1 h.")


async def _first_notification(context: ContextTypes.DEFAULT_TYPE):
    """Send the very first notification for a new user, then hand over to the global job."""
    chat_id = context.job.chat_id
    state   = load_state()
    users   = get_users(state)
    user_data = users.get(str(chat_id))
    if not user_data:
        return
    category = pick_next_category(user_data)
    msg      = build_message(category, user_data)
    save_state(state)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        logger.info(f"First notification sent to {chat_id} → [{category}]")
    except Exception as e:
        logger.warning(f"Failed first notification for {chat_id}: {e}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    async def post_init(application: Application):
        # Global hourly job — notifies ALL registered users each hour.
        # New users also get their own run_once (see start handler).
        application.job_queue.run_repeating(
            send_notifications,
            interval=3600,      # every hour
            first=60,           # first fire 1 minute after startup (catches any already-registered users)
        )
        logger.info("Global hourly notification job scheduled.")

    app.post_init = post_init

    logger.info("Bot is running...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message"],
    )


if __name__ == "__main__":
    main()
