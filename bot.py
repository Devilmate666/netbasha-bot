import logging
import random
import json
import os
import re
import feedparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN    = "8782083692:AAF6RRfvHYTZd0kPZUDL1ttGeAtVt-JWG5E"
CHANNEL  = "-1003989153913"
APP_URL  = "https://t.me/NetbashaBot/netbasha"
CHAN_URL = "https://t.me/netbasha"

# ─── Google News RSS queries per category ───────────────────────────────────────
# Each entry: (Arabic search query, emoji prefix, Arabic label)
CATEGORY_NEWS = {
    "movies":  ("أفلام مسلسلات",       "🎬", "أفلام ومسلسلات"),
    "live":    ("أخبار عاجلة",          "📺", "أخبار مباشرة"),
    "sports":  ("رياضة كرة قدم",        "⚽", "رياضة"),
    "anime":   ("انمي أنيمي",           "🎌", "أنمي"),
    "music":   ("موسيقى أغاني عربية",   "🎵", "موسيقى"),
    "cooking": ("وصفات طبخ",            "🍲", "طبخ ووصفات"),
    "health":  ("صحة لياقة",            "💊", "صحة ولياقة"),
    "social":  ("تواصل اجتماعي ترندات", "📱", "تواصل اجتماعي"),
    "books":   ("كتب روايات",           "📚", "كتب وروايات"),
    "tech":    ("تقنية ذكاء اصطناعي",   "💻", "تقنية وذكاء اصطناعي"),
}

# ─── Fallback static messages (used only when RSS fails) ────────────────────────
CATEGORY_MSGS = {
    "movies": [
        "🎬 *أفلام ومسلسلات لكل الأذواق*\n\n*نت باشا* يجمع لك أحدث الأفلام والمسلسلات العربية والعالمية في مكان واحد — بجودة عالية وبدون إعلانات مزعجة 🍿\n\n👉 [افتح نت باشا الآن](" + APP_URL + ")",
        "🎥 *عندك وقت فراغ؟*\n\nمع *نت باشا* ما تحتاج تدور بعيد — أحدث الأفلام والمسلسلات بجودة عالية ومترجمة بدقة، كلها في تطبيق واحد 😉\n\n👉 [شاهد على نت باشا](" + APP_URL + ")",
    ],
    "live": [
        "📺 *قنوات مباشرة على مدار الساعة*\n\n*نت باشا* يوفر لك بثاً مباشراً لعشرات القنوات العربية والعالمية بجودة HD — بدون تقطيع ولا تأخير 🔴\n\n👉 [نت باشا — بث حي](" + APP_URL + ")",
    ],
    "sports": [
        "⚽ *الدوريات الكبرى — تابعها على نت باشا!*\n\n*نت باشا* يوفر لك نتائج، ترتيب، وأهداف من أهم المباريات — محدّث أولاً بأول ⚡\n\n👉 [نت باشا — الرياضة](" + APP_URL + ")",
    ],
    "anime": [
        "🎌 *عالم الأنمي على نت باشا*\n\n*نت باشا* يوفر لك أحدث حلقات الأنمي مترجمة بعناية وبجودة عالية — كلاسيكي وحديث في مكان واحد 🌸\n\n👉 [شاهد على نت باشا](" + APP_URL + ")",
    ],
    "music": [
        "🎵 *موسيقى تناسب كل لحظة*\n\n*نت باشا* يجمع لك الأغاني العربية الحديثة والكلاسيكيات الخالدة — اختار مزاجك وابدأ الاستماع 🎶\n\n👉 [نت باشا — الموسيقى](" + APP_URL + ")",
    ],
    "cooking": [
        "🍲 *وصفة اليوم — جرّبها الليلة!*\n\n*نت باشا* يوفر لك أكلات شهية وسهلة التحضير من المطبخ العربي — خطوة بخطوة مع الصور 👨‍🍳\n\n👉 [نت باشا — الطبخ](" + APP_URL + ")",
    ],
    "health": [
        "💊 *نصيحتك الصحية لليوم*\n\n*نت باشا* يقدم لك عادات بسيطة تغير حياتك — تغذية، نوم، ولياقة بدنية. ابدأ اليوم قبل الغد 💪\n\n👉 [نت باشا — الصحة](" + APP_URL + ")",
    ],
    "social": [
        "🌐 *كل منصاتك في مكان واحد*\n\n*نت باشا* يجمع لك أهم المحتوى من تيك توك، انستغرام، ويوتيوب — بدون ما تفتح تطبيقات كثيرة 📲\n\n👉 [نت باشا — التواصل](" + APP_URL + ")",
    ],
    "books": [
        "📚 *كتاب يغير حياتك — ابدأ الآن*\n\n*نت باشا* يوفر لك روايات، كتب تطوير ذات، وأعمال أدبية عربية وعالمية — كلها في مكان واحد 📖\n\n👉 [نت باشا — الكتب](" + APP_URL + ")",
    ],
    "tech": [
        "💻 *أخبار التقنية اليوم*\n\n*نت باشا* يغطي لك ذكاء اصطناعي، هواتف جديدة، وتطبيقات ثورية — كل ما يهمك في عالم التكنولوجيا 🤖\n\n👉 [نت باشا — التقنية](" + APP_URL + ")",
    ],
}

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

نت باشا - كن من يعرف أولاً 👇\
"""

ALL_CATEGORIES = list(CATEGORY_NEWS.keys())
STATE_FILE = "/tmp/bot_state.json"

# ─── State helpers ───────────────────────────────────────────────────────────────

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
    queue = state.get("cat_queue", [])
    last_cat = state.get("last_cat")
    result = []

    for _ in range(n):
        if not queue:
            new_queue = ALL_CATEGORIES[:]
            random.shuffle(new_queue)
            if last_cat and new_queue[0] == last_cat:
                new_queue.append(new_queue.pop(0))
            queue = new_queue
            logger.info(f"New category cycle: {queue}")

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

# ─── News fetching ───────────────────────────────────────────────────────────────

def _clean_html(text: str) -> str:
    """Strip HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text).strip()

def fetch_news_post(category: str, state: dict) -> str:
    """
    Fetch a fresh news headline from Google News RSS for the given category.
    Tracks which articles have already been used (by URL) so the same headline
    is never posted twice in the same cycle.  Falls back to a static message
    if the feed is empty or unavailable.
    """
    query, emoji, label = CATEGORY_NEWS[category]

    # Per-category set of already-used article URLs
    used_urls: list = state.setdefault("used_news", {}).get(category, [])

    try:
        rss_url = (
            f"https://news.google.com/rss/search"
            f"?q={query.replace(' ', '+')}&hl=ar&gl=AE&ceid=AE:ar"
        )
        feed = feedparser.parse(rss_url)
        entries = feed.entries

        if not entries:
            raise ValueError("Empty feed")

        # Pick the first entry whose URL hasn't been used yet
        chosen = None
        for entry in entries[:15]:          # look at top 15 at most
            url = entry.get("link", "")
            if url not in used_urls:
                chosen = entry
                break

        # If all recent entries were already used, reset and take the first one
        if chosen is None:
            used_urls = []
            chosen = entries[0]

        title   = _clean_html(chosen.get("title", ""))
        source  = chosen.get("source", {}).get("title", "")
        url     = chosen.get("link", "")

        # Mark this article as used
        used_urls.append(url)
        if len(used_urls) > 50:             # cap to avoid state bloat
            used_urls = used_urls[-50:]
        state["used_news"][category] = used_urls

        # Build Telegram Markdown message
        source_line = f"_المصدر: {source}_\n\n" if source else ""
        post = (
            f"{emoji} *{label}*\n\n"
            f"*{title}*\n\n"
            f"{source_line}"
            f"🔗 [اقرأ الخبر كاملاً]({url})\n\n"
            f"📲 تابع المزيد على *نت باشا* 👇\n"
            f"[افتح نت باشا الآن]({APP_URL})"
        )
        logger.info(f"[{category}] News fetched: {title[:60]}")
        return post

    except Exception as e:
        logger.warning(f"[{category}] RSS fetch failed ({e}), using fallback.")
        return _fallback_message(category, state)

def _fallback_message(category: str, state: dict) -> str:
    """Return a non-recently-used static fallback message for the category."""
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

# ─── /start handler ──────────────────────────────────────────────────────────────

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

# ─── Welcome new channel members ─────────────────────────────────────────────────

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

# ─── Main ─────────────────────────────────────────────────────────────────────────

def main():
    state = load_state()

    schedule = get_next_categories(state, 5)
    save_state(state)
    logger.info(f"This run schedule: {schedule}")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))

    async def post_init(application: Application):
        first_delay = 120           # 2 min after start
        for i, category in enumerate(schedule):
            delay = first_delay + (i * 3600)   # 2, 62, 122, 182, 242 min

            def make_callback(cat):
                async def callback(ctx: ContextTypes.DEFAULT_TYPE):
                    msg = fetch_news_post(cat, state)
                    save_state(state)
                    await ctx.bot.send_message(
                        chat_id=CHANNEL,
                        text=msg,
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                    logger.info(f"Sent [{cat}] post.")
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
