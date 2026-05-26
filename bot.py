import logging
import random
import json
import os
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN    = "8782083692:AAF6RRfvHYTZd0kPZUDL1ttGeAtVt-JWG5E"
CHANNEL  = "-1003989153913"
APP_URL  = "https://t.me/NetbashaBot/netbasha"
CHAN_URL = "https://t.me/netbasha"

NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
GH_TOKEN     = os.environ.get("GH_TOKEN", "")   # GitHub token to commit feed.json
GH_REPO      = "Devilmate666/netbasha-bot"
FEED_FILE    = "feed.json"
FEED_PATH    = "/tmp/feed.json"
MAX_FEED     = 50

# ─── NewsAPI queries per category ───────────────────────────────────────────────
# (newsapi keyword/query,  emoji,  Arabic label)
CATEGORY_NEWS = {
    "movies":  ("movies OR series OR cinema OR مسلسل OR فيلم",   "🎬", "أفلام ومسلسلات"),
    "live":    ("breaking news OR عاجل",                          "📺", "أخبار مباشرة"),
    "sports":  ("football OR soccer OR sports OR كرة قدم",        "⚽", "رياضة"),
    "anime":   ("anime OR أنيمي OR انمي",                         "🎌", "أنمي"),
    "music":   ("music OR أغاني OR موسيقى",                       "🎵", "موسيقى"),
    "cooking": ("cooking OR recipes OR طبخ OR وصفات",             "🍲", "طبخ ووصفات"),
    "health":  ("health OR fitness OR صحة OR لياقة",              "💊", "صحة ولياقة"),
    "social":  ("social media OR trends OR تواصل اجتماعي",        "📱", "تواصل اجتماعي"),
    "books":   ("books OR novels OR كتب OR روايات",               "📚", "كتب وروايات"),
    "tech":    ("technology OR AI OR artificial intelligence OR تقنية OR ذكاء اصطناعي", "💻", "تقنية وذكاء اصطناعي"),
}

# ─── Fallback static messages ────────────────────────────────────────────────────
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

# ─── News fetching via NewsAPI ───────────────────────────────────────────────────

def fetch_news_post(category: str, state: dict) -> str:
    """Fetch a real news headline from NewsAPI for the category."""
    if not NEWS_API_KEY:
        logger.warning("NEWS_API_KEY not set — using fallback.")
        return _fallback_message(category, state)

    query, emoji, label = CATEGORY_NEWS[category]
    used_urls: list = state.setdefault("used_news", {}).get(category, [])

    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q":        query,
                "language": "ar",
                "sortBy":   "publishedAt",
                "pageSize": 20,
                "apiKey":   NEWS_API_KEY,
            },
            timeout=10,
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])

        if not articles:
            # fallback to English if no Arabic articles found
            resp2 = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        query,
                    "sortBy":   "publishedAt",
                    "pageSize": 20,
                    "apiKey":   NEWS_API_KEY,
                },
                timeout=10,
            )
            resp2.raise_for_status()
            articles = resp2.json().get("articles", [])

        if not articles:
            raise ValueError("No articles returned")

        # Pick first article not already used
        chosen = None
        for article in articles:
            url = article.get("url", "")
            if url not in used_urls and url != "https://removed.com":
                chosen = article
                break

        if chosen is None:
            used_urls = []
            chosen = articles[0]

        title   = chosen.get("title", "").split(" - ")[0].strip()   # strip source suffix
        source  = chosen.get("source", {}).get("name", "")
        url     = chosen.get("url", "")
        desc    = chosen.get("description") or ""
        # trim description to ~100 chars
        if len(desc) > 100:
            desc = desc[:97] + "…"

        # Track used
        used_urls.append(url)
        if len(used_urls) > 50:
            used_urls = used_urls[-50:]
        state["used_news"][category] = used_urls

        source_line = f"_المصدر: {source}_\n\n" if source else ""
        desc_line   = f"{desc}\n\n" if desc else ""
        post = (
            f"{emoji} *{label}*\n\n"
            f"*{title}*\n\n"
            f"{desc_line}"
            f"{source_line}"
            f"🔗 [اقرأ الخبر كاملاً]({url})\n\n"
            f"📲 تابع المزيد على *نت باشا* 👇\n"
            f"[افتح نت باشا الآن]({APP_URL})"
        )
        logger.info(f"[{category}] News fetched: {title[:60]}")
        return post

    except Exception as e:
        logger.warning(f"[{category}] NewsAPI failed ({e}), using fallback.")
        return _fallback_message(category, state)


def _load_feed() -> list:
    if os.path.exists(FEED_PATH):
        try:
            with open(FEED_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def _save_feed(feed: list):
    with open(FEED_PATH, "w") as f:
        json.dump(feed, f, ensure_ascii=False, indent=2)

def append_to_feed(post_text: str, article_url: str, category: str):
    """Append the just-sent post to feed.json and push to GitHub."""
    query, emoji, label = CATEGORY_NEWS[category]
    lines = [l for l in post_text.split("\n") if l.strip()]
    title = lines[0].replace("*", "").strip() if lines else label
    desc  = " ".join(lines[1:3]).replace("*", "").replace("_", "").strip()[:160]

    entry = {
        "id":     f"{category}_{int(__import__('time').time())}",
        "emoji":  emoji,
        "title":  title,
        "text":   desc,
        "link":   article_url,
        "date":   __import__('datetime').datetime.utcnow().isoformat() + "Z",
        "pubMs":  int(__import__('time').time() * 1000),
    }

    feed = _load_feed()
    feed.insert(0, entry)
    feed = feed[:MAX_FEED]
    _save_feed(feed)
    logger.info(f"Feed updated ({len(feed)} entries).")

    if GH_TOKEN:
        _push_feed_to_github(feed)

def _push_feed_to_github(feed: list):
    """Commit the updated feed.json to the GitHub repo so the app can read it."""
    import base64
    api = f"https://api.github.com/repos/{GH_REPO}/contents/{FEED_FILE}"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    # Get current SHA (needed for update)
    sha = None
    try:
        r = requests.get(api, headers=headers, timeout=10)
        if r.status_code == 200:
            sha = r.json().get("sha")
    except Exception:
        pass

    content = base64.b64encode(
        json.dumps(feed, ensure_ascii=False, indent=2).encode()
    ).decode()

    payload = {
        "message": "chore: update feed.json [bot]",
        "content": content,
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(api, headers=headers, json=payload, timeout=15)
        if r.status_code in (200, 201):
            logger.info("feed.json pushed to GitHub.")
        else:
            logger.warning(f"GitHub push failed: {r.status_code} {r.text[:200]}")
    except Exception as e:
        logger.warning(f"GitHub push error: {e}")
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
        first_delay = 120
        for i, category in enumerate(schedule):
            delay = first_delay + (i * 3600)

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
                    # Save post to feed.json and push to GitHub
                    article_url = state.get("used_news", {}).get(cat, [""])[-1] or ""
                    append_to_feed(msg, article_url, cat)
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
