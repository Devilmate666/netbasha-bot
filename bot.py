import logging
import random
import json
import os
import re
import time
import hashlib
import datetime
import xml.etree.ElementTree as ET
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ChatMemberHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN    = "8782083692:AAF6RRfvHYTZd0kPZUDL1ttGeAtVt-JWG5E"
CHANNEL  = "-1003989153913"
APP_URL  = "https://t.me/NetbashaBot/netbasha"
CHAN_URL = "https://t.me/netbasha"

GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO  = "Devilmate666/netbasha-bot"
FEED_FILE = "feed.json"
FEED_PATH = "/tmp/feed.json"
MAX_FEED         = 200
MAX_PER_CATEGORY = 20

STATE_FILE = "/tmp/bot_state.json"

# ─── RSS sources — SAME as the frontend's categoryRSS ───────────────────────
# Each category maps to a list of RSS feed URLs (Google RSS / Arabic news sites)
CATEGORY_RSS = {
    "movies": {
        "emoji": "🎬",
        "label": "أفلام ومسلسلات",
        "feeds": [
            "https://www.masrawy.com/rss/arts",
            "https://www.youm7.com/rss/section/92",
            "https://www.el-balad.com/rss/entertainment",
            "https://www.elcinema.com/rss/news.xml",
        ],
    },
    "tv": {
        "emoji": "📺",
        "label": "قنوات مباشرة",
        "feeds": [
            "https://www.masrawy.com/rss/arts",
            "https://www.youm7.com/rss/section/92",
            "https://www.el-balad.com/rss/entertainment",
        ],
    },
    "sports": {
        "emoji": "⚽",
        "label": "رياضة",
        "feeds": [
            "https://www.kooora.com/rss.aspx",
            "https://www.filgoal.com/rss",
            "https://www.yallakora.com/rss/all",
            "https://www.youm7.com/rss/section/97",
        ],
    },
    "anime": {
        "emoji": "🎌",
        "label": "أنمي",
        "feeds": [
            "https://www.arab-anime.com/feed",
            "https://www.animeiat.com/feed",
            "https://witanime.cyou/feed",
        ],
    },
    "music": {
        "emoji": "🎵",
        "label": "موسيقى",
        "feeds": [
            "https://www.masrawy.com/rss/arts",
            "https://www.youm7.com/rss/section/92",
        ],
    },
    "food": {
        "emoji": "🍲",
        "label": "طبخ ووصفات",
        "feeds": [
            "https://www.sayidaty.net/rss/section/food",
            "https://www.masrawy.com/rss/woman",
            "https://www.youm7.com/rss/section/222",
        ],
    },
    "health": {
        "emoji": "💊",
        "label": "صحة ولياقة",
        "feeds": [
            "https://www.altibbi.com/rss",
            "https://www.sayidaty.net/rss/section/health",
            "https://www.webteb.com/rss",
            "https://www.youm7.com/rss/section/107",
        ],
    },
    "social": {
        "emoji": "📱",
        "label": "تواصل اجتماعي",
        "feeds": [
            "https://www.masrawy.com/rss/technology",
            "https://www.youm7.com/rss/section/291",
            "https://www.el-balad.com/rss/tech",
        ],
    },
    "books": {
        "emoji": "📚",
        "label": "كتب وروايات",
        "feeds": [
            "https://www.alarabimag.com/rss",
            "https://www.alquds.co.uk/feed",
            "https://arabic.cnn.com/rss/arts-entertainment.rss",
        ],
    },
    "tech": {
        "emoji": "💻",
        "label": "تقنية وذكاء اصطناعي",
        "feeds": [
            "https://www.masrawy.com/rss/technology",
            "https://www.youm7.com/rss/section/291",
            "https://www.arabi21.com/rss/technology",
            "https://aitnews.com/feed",
        ],
    },
}

ALL_CATEGORIES = list(CATEGORY_RSS.keys())

# ─── Fallback static messages (used when no new RSS article is found) ─────────
CATEGORY_MSGS = {
    "movies": [
        "🎬 *أفلام ومسلسلات لكل الأذواق*\n\n*نت باشا* يجمع لك أحدث الأفلام والمسلسلات العربية والعالمية في مكان واحد — بجودة عالية وبدون إعلانات مزعجة 🍿\n\n👉 [افتح نت باشا الآن](" + APP_URL + ")",
        "🎥 *عندك وقت فراغ؟*\n\nمع *نت باشا* ما تحتاج تدور بعيد — أحدث الأفلام والمسلسلات بجودة عالية ومترجمة بدقة، كلها في تطبيق واحد 😉\n\n👉 [شاهد على نت باشا](" + APP_URL + ")",
    ],
    "tv": [
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
    "food": [
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

# ─── RSS helpers ─────────────────────────────────────────────────────────────

def _url_id(url: str) -> str:
    """Stable short ID for a URL — used to deduplicate sent articles."""
    return hashlib.md5(url.encode()).hexdigest()[:16]


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse RSS/Atom XML and return a list of {title, link, pub_date, description}."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://purl.org/rss/1.0/modules/content/",
    }

    # RSS 2.0
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        desc  = (item.findtext("description") or "").strip()
        pub   = (item.findtext("pubDate") or "").strip()
        if link:
            items.append({"title": title, "link": link, "description": desc, "pub_date": pub})

    # Atom
    if not items:
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            link = (link_el.get("href", "") if link_el is not None else "").strip()
            desc = (entry.findtext("{http://www.w3.org/2005/Atom}summary") or "").strip()
            pub  = (entry.findtext("{http://www.w3.org/2005/Atom}updated") or "").strip()
            if link:
                items.append({"title": title, "link": link, "description": desc, "pub_date": pub})

    return items


def fetch_rss_items(feed_url: str, timeout: int = 12) -> list[dict]:
    """Download and parse a single RSS feed. Returns [] on any error."""
    try:
        # Use rss2json as a proxy for CORS/format issues, fall back to direct fetch
        r = requests.get(
            "https://api.rss2json.com/v1/api.json",
            params={"rss_url": feed_url, "count": 20},
            timeout=timeout,
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "ok":
                items = []
                for it in data.get("items", []):
                    items.append({
                        "title":       (it.get("title") or "").strip(),
                        "link":        (it.get("link") or it.get("guid") or "").strip(),
                        "description": re.sub(r"<[^>]+>", "", it.get("description") or "").strip()[:200],
                        "pub_date":    it.get("pubDate", ""),
                    })
                return [i for i in items if i["link"]]
    except Exception as e:
        logger.debug(f"rss2json proxy failed for {feed_url}: {e}")

    # Direct fetch fallback
    try:
        r2 = requests.get(feed_url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        r2.raise_for_status()
        return _parse_rss(r2.text)
    except Exception as e:
        logger.debug(f"Direct RSS fetch failed for {feed_url}: {e}")
        return []


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


def get_next_categories(state: dict, n: int) -> list:
    queue     = state.get("cat_queue", [])
    last_cat  = state.get("last_cat")
    result    = []

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
    state["last_cat"]  = last_cat
    return result


# ─── Article deduplication ────────────────────────────────────────────────────

def _sent_ids(state: dict, category: str) -> set:
    """Return the set of URL-IDs already sent for this category."""
    return set(state.setdefault("sent_ids", {}).get(category, []))


def _mark_sent(state: dict, category: str, url: str):
    """Record a URL as sent. Keeps the last 200 per category."""
    bucket = state.setdefault("sent_ids", {}).setdefault(category, [])
    uid = _url_id(url)
    if uid not in bucket:
        bucket.append(uid)
    if len(bucket) > 200:
        state["sent_ids"][category] = bucket[-200:]


# ─── Main post builder ────────────────────────────────────────────────────────

def fetch_rss_post(category: str, state: dict) -> tuple[str, str]:
    """
    Try every RSS feed for the category. Return (message_text, article_url).
    Falls back to a static promo message (article_url = "") if nothing new is found.
    Only articles NOT previously sent are considered.
    """
    cfg      = CATEGORY_RSS[category]
    emoji    = cfg["emoji"]
    label    = cfg["label"]
    feeds    = cfg["feeds"]
    sent     = _sent_ids(state, category)

    # Shuffle feed order so we spread load across sources
    feed_order = feeds[:]
    random.shuffle(feed_order)

    for feed_url in feed_order:
        items = fetch_rss_items(feed_url)
        for item in items:
            url = item["link"]
            if not url or _url_id(url) in sent:
                continue

            title = item["title"] or label
            desc  = item["description"] or ""
            if len(desc) > 150:
                desc = desc[:147] + "…"

            _mark_sent(state, category, url)

            desc_line = f"{desc}\n\n" if desc else ""
            post = (
                f"{emoji} *{label}*\n\n"
                f"*{title}*\n\n"
                f"{desc_line}"
                f"🔗 [اقرأ المقال كاملاً]({url})\n\n"
                f"📲 تابع المزيد على *نت باشا* 👇\n"
                f"[افتح نت باشا الآن]({APP_URL})"
            )
            logger.info(f"[{category}] RSS article found: {title[:60]}")
            return post, url

    # Nothing new found — use a fallback static message
    logger.info(f"[{category}] No new RSS articles — using fallback.")
    return _fallback_message(category, state), ""


def _fallback_message(category: str, state: dict) -> str:
    msgs     = CATEGORY_MSGS[category]
    msg_used = state.setdefault("msg_used", {})
    used: list = msg_used.get(category, [])
    available  = [i for i in range(len(msgs)) if i not in used]
    if not available:
        used = []
        available = list(range(len(msgs)))
    idx = random.choice(available)
    used.append(idx)
    msg_used[category] = used
    return msgs[idx]


# ─── feed.json / GitHub helpers ──────────────────────────────────────────────

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
    """Append the sent post to feed.json and push to GitHub."""
    cfg   = CATEGORY_RSS[category]
    emoji = cfg["emoji"]
    label = cfg["label"]

    lines = [l.replace("*","").replace("_","").strip() for l in post_text.split("\n") if l.strip()]
    title = (lines[1] if len(lines) > 1 else lines[0] if lines else label).strip() or label
    desc_parts = []
    for l in lines[2:]:
        if l.startswith("🔗") or l.startswith("📲") or l.startswith("http") or l.startswith("["):
            break
        desc_parts.append(l)
        if len(desc_parts) >= 2:
            break
    desc = " ".join(desc_parts).strip()[:200]

    entry = {
        "id":       f"{category}_{int(time.time())}",
        "category": category,
        "emoji":    emoji,
        "label":    label,
        "title":    title,
        "text":     desc,
        "link":     article_url,
        "date":     datetime.datetime.utcnow().isoformat() + "Z",
        "pubMs":    int(time.time() * 1000),
    }

    feed = _load_feed()
    feed.insert(0, entry)
    from collections import Counter
    counts: Counter = Counter()
    pruned = []
    for e in feed:
        k = e.get("category","")
        if counts[k] < MAX_PER_CATEGORY:
            pruned.append(e)
            counts[k] += 1
    feed = pruned[:MAX_FEED]
    _save_feed(feed)
    logger.info(f"Feed updated ({len(feed)} entries).")

    if GH_TOKEN:
        _push_feed_to_github(feed)


def _push_feed_to_github(feed: list):
    import base64
    api     = f"https://api.github.com/repos/{GH_REPO}/contents/{FEED_FILE}"
    headers = {
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept":        "application/vnd.github+json",
    }
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

    payload = {"message": "chore: update feed.json [bot]", "content": content}
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


# ─── Telegram handlers ────────────────────────────────────────────────────────

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


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result     = update.chat_member
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


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    state    = load_state()
    schedule = get_next_categories(state, 5)
    save_state(state)
    logger.info(f"This run schedule: {schedule}")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))

    async def post_init(application: Application):
        # First post fires 2 minutes in, then one per hour
        first_delay = 120
        for i, category in enumerate(schedule):
            delay = first_delay + (i * 3600)

            def make_callback(cat):
                async def callback(ctx: ContextTypes.DEFAULT_TYPE):
                    msg, article_url = fetch_rss_post(cat, state)
                    save_state(state)
                    await ctx.bot.send_message(
                        chat_id=CHANNEL,
                        text=msg,
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                    # Only append to feed if it was a real article (not a fallback)
                    if article_url:
                        append_to_feed(msg, article_url, cat)
                    logger.info(f"Sent [{cat}] post. article_url={article_url or '(fallback)'}")
                return callback

            application.job_queue.run_once(make_callback(category), when=delay)
            logger.info(f"Scheduled [{category}] at {delay // 60} min mark.")

    app.post_init = post_init

    logger.info("Bot is running...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "chat_member"],
    )


if __name__ == "__main__":
    main()
