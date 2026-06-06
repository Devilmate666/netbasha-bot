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

# ─── Get token from environment variable ─────────────────────────────────────
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

APP_URL = "https://t.me/NetbashaBot/netbasha"

# ─── State file — persists registered users across GitHub Action runs ─────────
STATE_FILE = "/tmp/bot_state.json"

# ─── Deeplink builder — opens the app then navigates to the category ──────────
def category_url(category: str) -> str:
    """Opens the Telegram Mini App and lands the user on the given category."""
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

# ─── Schedule (Syrian time UTC+3) ────────────────────────────────────────────
SCHEDULE = [
    ( 8,  0, "health"),
    (10,  0, "books"),
    (12,  0, "sports"),
    (14,  0, "social"),
    (16,  0, "food"),
    (18,  0, "tech"),
    (19,  0, "movies"),
    (20,  0, "anime"),
    (21,  0, "music"),
    (22,  0, "tv"),
]

SYRIA_UTC_OFFSET = 3  # UTC+3

def syria_now() -> datetime.datetime:
    return datetime.datetime.utcnow() + datetime.timedelta(hours=SYRIA_UTC_OFFSET)

def utc_time(syria_hour: int, syria_minute: int) -> datetime.time:
    total = syria_hour * 60 + syria_minute - (SYRIA_UTC_OFFSET * 60)
    total %= 1440
    return datetime.time(total // 60, total % 60)

def slot_to_minutes(syria_hour: int, syria_minute: int) -> int:
    return syria_hour * 60 + syria_minute

def get_slot_datetime(syria_hour: int, syria_minute: int, reference: datetime.datetime) -> datetime.datetime:
    syria_ref = syria_now() if reference is None else reference
    slot = syria_ref.replace(hour=syria_hour, minute=syria_minute, second=0, microsecond=0)
    if slot < syria_ref:
        return None
    utc_slot = slot - datetime.timedelta(hours=SYRIA_UTC_OFFSET)
    return utc_slot


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATION MESSAGES
# Each lambda receives `url` = the category deeplink (opens app → category).
# Rules:
#   • Always general — never implies a specific article/title/event.
#   • Encourages user to open and discover by themselves.
#   • Never misleading about what they'll find (no نصائح نوم / دوري أبطال etc.)
# ══════════════════════════════════════════════════════════════════════════════

CATEGORY_MSGS: dict[str, list] = {

    # ── HEALTH ────────────────────────────────────────────────────────────────
    # Websites: مقالات طبية · منظمة الصحة العالمية · دايلي ميديكال · دليل الصحة · الصحة النفسية · الصحة و الجمال
    "health": [
        lambda url: (
            f"💊 *مقالات طبية*\n\n"
            f"في أسئلة طبية عندك ومو عارف كيف تدور عليها؟ قسم الصحة بنت باشا فيه مقالات طبية موثوقة — افتح واستكشف 🩺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 *منظمة الصحة العالمية*\n\n"
            f"المعلومة الصحية الصحيحة بتجيك من مصدرها. قسم الصحة على نت باشا فيه رابط مباشر لموقع منظمة الصحة العالمية — اكتشف 👀\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📋 *معلومات طبية يومية*\n\n"
            f"معلومة صحية جديدة كل يوم — دايلي ميديكال في انتظارك على قسم الصحة بنت باشا. افتح وتصفح 🔍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📖 *دليل الصحة*\n\n"
            f"دليل شامل عن الأمراض والعلاجات والأدوية — موجود على قسم الصحة بنت باشا. افتح وابحث عن ما يهمك 💡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🧠 *الصحة النفسية*\n\n"
            f"الصحة النفسية جزء من الصحة الكاملة. قسم الصحة على نت باشا فيه محتوى نفسي يساعدك تفهم أكتر — افتح واستكشف 🌿\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"✨ *الصحة والجمال*\n\n"
            f"عناية بالجسم من الداخل والخارج. قسم الصحة على نت باشا فيه محتوى صحة وجمال — افتح وتصفح 💅\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🩺 *المعرفة الطبية*\n\n"
            f"ما كل سؤال طبي يحتاج زيارة دكتور. قسم الصحة بنت باشا فيه مصادر موثوقة تساعدك — افتح وابحث 🔎\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💊 *صحة بمصادر عالمية*\n\n"
            f"المحتوى الصحي من مصادر عالمية — كلو في مكان واحد على قسم الصحة بنت باشا. افتح وتصفح 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"❤️ *اهتم بصحتك*\n\n"
            f"دقيقة واحدة بتكفي تبدأ. قسم الصحة على نت باشا جاهز — افتح واكتشف المحتوى اللي يناسبك 🌱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌿 *استكشف قسم الصحة*\n\n"
            f"مقالات، أدلة طبية، ومحتوى صحة نفسية — كلو بانتظارك على نت باشا. افتح قسم الصحة وتصفح 👇\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    # ── BOOKS ─────────────────────────────────────────────────────────────────
    # Websites (shuffled): نور كتب · مكتبة سهم · كتباتي · المكتبة العربية · كتابك عندنا · مجلة الكتب العربية · قهوة غرب
    "books": [
        lambda url: (
            f"📚 *عالم الكتب*\n\n"
            f"مكتبة كاملة بجيبك — ما تحتاج دور بعيد. افتح قسم الكتب على نت باشا واكتشف مكتبتك الجديدة 📖\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📗 *نور كتب*\n\n"
            f"آلاف الكتب العربية في مكان واحد — نور كتب بانتظارك على قسم الكتب بنت باشا. افتح وتصفح 🌟\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📚 *مكتبة سهم*\n\n"
            f"كتاب جديد كل يوم؟ مكتبة سهم متاحة على قسم الكتب بنت باشا — افتح واكتشف 📖\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📖 *كتباتي*\n\n"
            f"كتب PDF مجانية وجاهزة للقراءة — كتباتي على قسم الكتب بنت باشا. افتح وتصفح 📂\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⭐ *المكتبة العربية*\n\n"
            f"مكتبة عربية شاملة في انتظارك. افتح قسم الكتب على نت باشا واكتشف ما يناسبك 📚\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🗄️ *كتابك عندنا*\n\n"
            f"دور على الكتاب اللي بدك إياه — كتابك عندنا على قسم الكتب بنت باشا. افتح وابحث 🔍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📰 *مجلة الكتب العربية*\n\n"
            f"آخر أخبار عالم الكتب والأدب العربي — مجلة الكتب العربية على نت باشا. افتح وتصفح 🗞️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"☕ *قهوة غرب*\n\n"
            f"محتوى أدبي وثقافي يرافق قهوتك. قهوة غرب على قسم الكتب بنت باشا — افتح واستكشف 🌙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📚 *وقت القراءة*\n\n"
            f"وقت فراغ + كتاب جيد = يوم أفضل. قسم الكتب على نت باشا جاهز — افتح وابدأ 📖\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌟 *اكتشف مكتبتك*\n\n"
            f"سبعة مواقع كتب عربية كلها في قسم واحد — افتح نت باشا واكتشف المكتبة اللي ما كنت تعرفها 📚\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    # ── SPORTS ────────────────────────────────────────────────────────────────
    # كووورة · 365 سكور — أخبار ونتائج
    # مباريات لايف 1 · مباريات لايف 2 — مباريات مباشرة
    # قنوات رياضة — قنوات رياضية
    # رياضة عالمية — رياضة عالمية
    "sports": [
        lambda url: (
            f"⚽ *كووورة — أخبار الرياضة*\n\n"
            f"آخر أخبار الرياضة والنتائج من أكبر موقع عربي رياضي — كووورة على نت باشا. افتح وتابع ⚽\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📊 *365 سكور — نتائج ومباريات*\n\n"
            f"نتائج المباريات والترتيبات لحظة بلحظة — 365 سكور على قسم الرياضة بنت باشا. افتح وتصفح 🏆\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔴 *مباريات لايف — بث مباشر*\n\n"
            f"في مباريات عم تنبث هلق؟ مباريات لايف على قسم الرياضة بنت باشا جاهزة. افتح وتابع 📺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔴 *بث رياضي مباشر*\n\n"
            f"لا تفوت المباراة — بث مباشر من مباريات لايف على نت باشا. افتح وشوف مين يلعب هلق ⚡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📡 *قنوات رياضية مباشرة*\n\n"
            f"قنوات رياضية ببث مباشر — كلها على قسم الرياضة بنت باشا. افتح واختار قناتك 📺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 *رياضة عالمية*\n\n"
            f"مش بس كرة القدم — رياضات عالمية متنوعة على قسم الرياضة بنت باشا. افتح واكتشف 🏅\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⚽ *تابع الرياضة*\n\n"
            f"أخبار، نتائج، بث مباشر، وقنوات رياضية — كلو بانتظارك على قسم الرياضة بنت باشا 🔎\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🏆 *نتائج اليوم*\n\n"
            f"شو صار بالرياضة اليوم؟ كووورة و365 سكور على نت باشا بيعطوك كل شي — افتح وتابع 📱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌐 *رياضة من كل العالم*\n\n"
            f"من الملاعب المحلية للبطولات العالمية — قسم الرياضة على نت باشا جاهز. افتح واكتشف ⚡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📺 *البث الرياضي*\n\n"
            f"مباريات لايف وقنوات رياضية — كلها مباشرة على نت باشا. افتح قسم الرياضة وتابع هلق 🔴\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    # ── SOCIAL ────────────────────────────────────────────────────────────────
    # فيسبوك · تويتر · انستغرام · يوتيوب · تيك توك · سناب شات · ديسكورد · تويتش · لينكد إن · واتساب · ثريدز · بينترست · ريديت · كورا · في كي
    "social": [
        lambda url: (
            f"📘 *فيسبوك*\n\n"
            f"فيسبوك بانتظارك مع كل إشعاراتك ومجموعاتك — مباشرة من نت باشا. افتح وتصفح 👀\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🐦 *تويتر / X*\n\n"
            f"شو ترند هلق على X؟ ادخل مباشرة من قسم التواصل بنت باشا واكتشف 🔥\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📷 *انستغرام*\n\n"
            f"ريلز، ستوريز، ومحتوى جديد — انستغرام جاهز من نت باشا. افتح وتصفح 📸\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📹 *يوتيوب*\n\n"
            f"يوتيوب من نت باشا — بدون ما تفتح تطبيق تاني. افتح قسم التواصل وشوف الجديد ▶️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎵 *تيك توك*\n\n"
            f"الترند الجديد على تيك توك — ادخل مباشرة من نت باشا واكتشف بنفسك 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"👻 *سناب شات*\n\n"
            f"ستوريز سناب بانتظارك. ادخل مباشرة من قسم التواصل بنت باشا 👀\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎮 *ديسكورد*\n\n"
            f"سيرفرك على ديسكورد بانتظارك — ادخل مباشرة من نت باشا. افتح وانضم 🔗\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🟣 *تويتش*\n\n"
            f"في ستريمات عم تشتغل هلق على تويتش — افتح من نت باشا وشوف مين online 🔴\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💼 *لينكد إن*\n\n"
            f"شبكتك المهنية على لينكد إن — ادخل مباشرة من قسم التواصل بنت باشا 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📌 *بينترست*\n\n"
            f"أفكار وإلهام على بينترست — افتح من قسم التواصل بنت باشا واكتشف ما يلهمك 🎨\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    # ── FOOD ──────────────────────────────────────────────────────────────────
    # وصفات شامية · أكل صحي — متخصصة
    # الباقي يتناوب: وصفات عربية · فن الطهي · أكل وبس · غوودي · طخبات · يمي · أطيب أكلة
    "food": [
        lambda url: (
            f"🌶️ *وصفات شامية*\n\n"
            f"المطبخ الشامي الأصيل بكل تفاصيله — شامي فود على قسم الطبخ بنت باشا. افتح واستكشف الوصفات 🍽️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥗 *أكل صحي*\n\n"
            f"وصفات صحية وعملية للحياة اليومية — Helthy Cooking على قسم الطبخ بنت باشا. افتح وتصفح 🥦\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍳 *وصفات عربية*\n\n"
            f"مطابخ عربية من كل الدول في مكان واحد. افتح قسم الطبخ على نت باشا واكتشف الوصفات 👨‍🍳\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"👩‍🍳 *فن الطهي*\n\n"
            f"أكلات وطرق طبخ من كل مطابخ العالم — فن الطهي على نت باشا. افتح وتصفح ما يشهيك 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍲 *أكل وبس*\n\n"
            f"طبخ بدون تعقيد — أكل وبس على قسم الطبخ بنت باشا. افتح واكتشف وصفات اليوم 🔥\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍰 *غوودي*\n\n"
            f"وصفات احترافية بخطوات واضحة — غوودي كيتشن على نت باشا. افتح قسم الطبخ وتصفح 🎂\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥘 *طخبات*\n\n"
            f"آلاف الوصفات بالتفصيل — طخبات على قسم الطبخ بنت باشا. افتح واختار وصفتك 🍽️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍱 *يمي*\n\n"
            f"طبخات يومية لذيذة وسهلة — يمي على قسم الطبخ بنت باشا. افتح واكتشف شو تطبخ اليوم 😋\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍳 *أطيب أكلة*\n\n"
            f"وصفات من كل المطابخ — أطيب أكلة على نت باشا. افتح قسم الطبخ وتصفح الأكلات 🌶️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍽️ *استكشف قسم الطبخ*\n\n"
            f"من الشامي للصحي للعالمي — قسم الطبخ على نت باشا عنده كل الوصفات. افتح وتصفح 👇\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    # ── TECH ──────────────────────────────────────────────────────────────────
    # التقنية السورية · AI بدون حساب · أدوات AI · مقارنات أجهزة · شروحات ومراجعات · تطبيقات أندرويد · تطبيقات كومبيوتر · تطبيقات عامة · تطبيقات أبل
    "tech": [
        lambda url: (
            f"🛠️ *التقنية السورية*\n\n"
            f"أخبار التقنية باللهجة اللي نعرفها — التقنية السورية على نت باشا. افتح قسم التقنية وتصفح 💻\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🤖 *AI بدون حساب*\n\n"
            f"جرب الذكاء الاصطناعي هلق بدون تسجيل — Duck AI على قسم التقنية بنت باشا. افتح وجرب 🚀\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⚙️ *أدوات AI*\n\n"
            f"أدوات ذكاء اصطناعي مجانية ومفيدة — كلها على قسم التقنية بنت باشا. افتح واكتشف ما يفيدك 🧠\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📊 *مقارنات الأجهزة*\n\n"
            f"بدك تقارن بين جهازين؟ 3edda على قسم التقنية بنت باشا يعطيك المقارنة الكاملة. افتح وتصفح 🔍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📱 *شروحات ومراجعات*\n\n"
            f"شرح تقني أو مراجعة جهاز جديد؟ 3arrafni على قسم التقنية بنت باشا. افتح واكتشف 📖\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📲 *تطبيقات أندرويد*\n\n"
            f"تطبيقات أندرويد مدفوعة بشكل مجاني — APK Play على قسم التقنية بنت باشا. افتح وتصفح ⬇️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💻 *تطبيقات الكمبيوتر*\n\n"
            f"برامج كمبيوتر مدفوعة متاحة — Traidsoft على قسم التقنية بنت باشا. افتح واكتشف 🖥️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍎 *تطبيقات متنوعة*\n\n"
            f"تطبيقات لكل الأنظمة في مكان واحد — قسم التقنية على نت باشا. افتح وتصفح التطبيقات 📦\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍎 *تطبيقات أبل*\n\n"
            f"App Store مباشرة من نت باشا — ابحث عن التطبيق اللي بتحتاجه على قسم التقنية 📱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💡 *استكشف قسم التقنية*\n\n"
            f"AI، تطبيقات، مراجعات، ومقارنات — كل إشي تقني بانتظارك على نت باشا. افتح وتصفح 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    # ── MOVIES ────────────────────────────────────────────────────────────────
    # دليل الأفلام (elcinema) — دليل + سينما + دراما
    # الباقي (streaming) يتناوب: كيو فيلم · المصطبة · مدينة الأفلام · مسلسلات تايم · كيبوراما · قصة عشق · لاروزا · فشار · أهواك
    "movies": [
        lambda url: (
            f"🎬 *دليل الأفلام*\n\n"
            f"شو الجديد بالأفلام والمسلسلات والسينما؟ دليل الأفلام على نت باشا عنده كل شي — افتح واكتشف 🎥\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎭 *دراما جديدة*\n\n"
            f"شو الدراما الجديدة هالموسم؟ دليل الأفلام على نت باشا يعرفك كل جديد — افتح وتصفح 📺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎞️ *ما في عندك ما تشوفه؟*\n\n"
            f"مواقع مشاهدة متنوعة على قسم الأفلام بنت باشا — افتح واكتشف فيلم أو مسلسل جديد 🍿\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 *مشاهدة بدون حدود*\n\n"
            f"أفلام ومسلسلات عربية وعالمية وكورية وتركية — كلها على قسم الأفلام بنت باشا. افتح وتصفح 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍿 *ليلة مشاهدة*\n\n"
            f"مو عارف شو تشوف الليلة؟ قسم الأفلام على نت باشا جاهز — افتح واكتشف بنفسك 🎦\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📽️ *مسلسلات وأفلام*\n\n"
            f"مواقع مشاهدة متنوعة كلها بمكان واحد — افتح قسم الأفلام على نت باشا وتصفح 🎞️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎬 *سينما العالم*\n\n"
            f"من السينما العربية للكورية للتركية — كلها على قسم الأفلام بنت باشا. افتح واكتشف 🌏\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⭐ *اكتشف جديد*\n\n"
            f"في دايماً شي جديد تشوفه. افتح قسم الأفلام على نت باشا وتصفح المواقع المتاحة 🔍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎥 *أفلام ومسلسلات*\n\n"
            f"اختار الموقع اللي يناسبك — قسم الأفلام على نت باشا فيه خيارات كتيرة. افتح وتصفح 🎭\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎬 *دليل الأفلام — آخر الأخبار*\n\n"
            f"آخر أخبار السينما والدراما والأفلام الجديدة — دليل الأفلام على نت باشا. افتح واكتشف 🌟\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    # ── ANIME ─────────────────────────────────────────────────────────────────
    # أخبار الأنمي (gateanime) · دليل المانغا (daleelalmanga) · قراءة المانغا (3asq) — متخصصة
    # مواقع المشاهدة يتناوب: انمي فور اب · انمي بيك · اوك أنمي · ريستو · ويت أنمي · أنمي سيلفر
    "anime": [
        lambda url: (
            f"🎌 *أخبار الأنمي*\n\n"
            f"شو الجديد بعالم الأنمي هالموسم؟ أخبار الأنمي على نت باشا عندها كل جديد — افتح واكتشف 🌸\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📖 *دليل المانغا*\n\n"
            f"دور على مانغا جديدة أو تابع اللي بتقرأها — دليل المانغا على نت باشا. افتح وتصفح 📚\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📖 *قراءة المانغا*\n\n"
            f"اقرأ المانغا مباشرة من قسم الأنمي بنت باشا — فصول جديدة في انتظارك. افتح وتابع 🎌\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎌 *شاهد الأنمي*\n\n"
            f"مواقع مشاهدة أنمي عربية كلها على نت باشا — افتح قسم الأنمي واكتشف ما يناسبك 🌟\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⚔️ *أنمي جديد*\n\n"
            f"في دايماً أنمي جديد تنبسط فيه. افتح قسم الأنمي على نت باشا وتصفح مواقع المشاهدة 🔍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌸 *تابع أنميك*\n\n"
            f"وين وصلت؟ افتح قسم الأنمي على نت باشا واكمل متابعتك من مكانك 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎌 *مانغا وأنمي*\n\n"
            f"من قراءة المانغا لمشاهدة الأنمي — كلو على قسم الأنمي بنت باشا. افتح وتصفح 📖\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌺 *اكتشف أنمي جديد*\n\n"
            f"ما تعرف شو تشوف؟ قسم الأنمي على نت باشا فيه مواقع كتيرة تساعدك تختار — افتح وتصفح 🎯\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📰 *آخر أخبار الأنمي*\n\n"
            f"إعلانات، مواسم جديدة، وأخبار عالم الأنمي — أخبار الأنمي على نت باشا. افتح وتابع 🎌\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎌 *عالم الأنمي والمانغا*\n\n"
            f"أخبار، مانغا، وبث مباشر للأنمي — كلو بانتظارك على قسم الأنمي بنت باشا. افتح وتصفح 🌸\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    # ── MUSIC ─────────────────────────────────────────────────────────────────
    # راديو نت باشا — راديو 24 ساعة مدمج
    # بيلبورد عربية — أخبار موسيقى
    # تحميل mp3 (nogomistars) · تحميل ألبومات كاملة (mrmazika) · أحدث الألبومات (matb3aa) · أغاني أجنبي (jamendo)
    # أنغامي — بث موسيقى
    "music": [
        lambda url: (
            f"🎵 *راديو نت باشا*\n\n"
            f"راديو موسيقى 24 ساعة مدمج مباشرة بالتطبيق — افتح قسم الموسيقى على نت باشا واستمع هلق 🎧\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📰 *بيلبورد عربية*\n\n"
            f"آخر أخبار الموسيقى العربية والعالمية — بيلبورد عربية على قسم الموسيقى بنت باشا. افتح وتصفح 🎶\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⬇️ *تحميل mp3*\n\n"
            f"أغاني mp3 جاهزة للتحميل — نجوم ستارز على قسم الموسيقى بنت باشا. افتح وابحث عن أغنيتك 🎤\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💿 *ألبومات كاملة*\n\n"
            f"حمّل ألبومات كاملة — مر مازيكا على قسم الموسيقى بنت باشا. افتح وتصفح الألبومات 🎼\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🆕 *أحدث الألبومات*\n\n"
            f"أحدث إصدارات الألبومات العربية والعالمية — مطبعة على نت باشا. افتح قسم الموسيقى واكتشف 🎵\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 *أغاني أجنبي*\n\n"
            f"موسيقى عالمية مرخصة مجانية — جامندو على قسم الموسيقى بنت باشا. افتح واستكشف 🎸\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎵 *أنغامي*\n\n"
            f"الموسيقى العربية الأصيلة على أنغامي — مباشرة من قسم الموسيقى بنت باشا. افتح واستمع 🎶\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📻 *استمع هلق*\n\n"
            f"راديو مدمج + أغاني + ألبومات + أخبار موسيقى — كلو بانتظارك على نت باشا. افتح قسم الموسيقى 🎧\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎤 *اكتشف الموسيقى*\n\n"
            f"من الراديو للتحميل للأخبار — قسم الموسيقى على نت باشا عنده كل شي. افتح وتصفح 🎼\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎵 *موسيقى لكل مزاج*\n\n"
            f"عربية، أجنبية، راديو، أو تحميل — اختار اللي يناسبك من قسم الموسيقى بنت باشا 🎧\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    # ── TV / CHANNELS ─────────────────────────────────────────────────────────
    # دليل البرامج (elcinema tvguide) · قنوات عربية 1 · قنوات عربية 2 · قنوات عالمية (sportika tv) · قنوات الدول (globetv) · اذاعات راديو (radioarabic)
    "tv": [
        lambda url: (
            f"📺 *دليل البرامج*\n\n"
            f"شو عم ينبث هلق على القنوات العربية؟ دليل البرامج على نت باشا يعرفك — افتح وتصفح 🕐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📡 *قنوات عربية مباشرة*\n\n"
            f"القنوات العربية ببث مباشر — كلها على قسم القنوات بنت باشا. افتح واختار قناتك 🔴\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📡 *قنوات عربية — الخيار الثاني*\n\n"
            f"بث مباشر للقنوات العربية من مصدر تاني — aflam4uall على نت باشا. افتح وتصفح 📺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 *قنوات عالمية*\n\n"
            f"قنوات من كل بلاد العالم ببث مباشر — على قسم القنوات بنت باشا. افتح واكتشف 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🗺️ *قنوات الدول*\n\n"
            f"ابحث عن قنوات أي بلد بدك — globetv على قسم القنوات بنت باشا. افتح وتصفح 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📻 *إذاعات راديو*\n\n"
            f"محطات راديو عربية متنوعة ببث مباشر — راديو عربية على نت باشا. افتح قسم القنوات واستمع 🎙️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔴 *بث مباشر الآن*\n\n"
            f"قنوات عربية وعالمية وإذاعات — كلها ببث مباشر على قسم القنوات بنت باشا. افتح وتصفح 📡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📺 *تلفزيون بجيبك*\n\n"
            f"القنوات المفضلة بانتظارك — من العربية للعالمية والدول. افتح قسم القنوات على نت باشا 📲\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎙️ *راديو عربي*\n\n"
            f"استمع لمحطات الراديو العربية من أي مكان — راديو عربية على نت باشا. افتح وتصفح المحطات 📻\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌐 *استكشف قسم القنوات*\n\n"
            f"دليل برامج، قنوات عربية وعالمية، قنوات الدول، وراديو — كلو على نت باشا. افتح وتصفح 👇\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
}

ALL_CATEGORIES = list(CATEGORIES.keys())

WELCOME_MSG = """\
👋 *أهلاً بك في نت باشا!*

ابحث عن أي شي يهمك — أفلام، رياضة، موسيقى، أخبار التقنية، وصفات، كتب، أنمي، قنوات مباشرة، وأكثر 🔍

كل شي في مكان واحد. افتح وابدأ 👇\
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
    return state.setdefault("users", {})


def get_slots_fired(state: dict) -> dict:
    return state.setdefault("slots_fired", {})


def mark_slot_fired(state: dict, slot_key: str):
    today = syria_now().strftime("%Y-%m-%d")
    slots_fired = get_slots_fired(state)
    if today not in slots_fired:
        slots_fired[today] = {}
    slots_fired[today][slot_key] = True
    save_state(state)


def is_slot_fired_today(state: dict, slot_key: str) -> bool:
    today = syria_now().strftime("%Y-%m-%d")
    slots_fired = get_slots_fired(state)
    return slots_fired.get(today, {}).get(slot_key, False)


def register_user(state: dict, chat_id: int):
    users = get_users(state)
    key = str(chat_id)
    if key not in users:
        now = datetime.datetime.utcnow()
        first_notify_after = (now + datetime.timedelta(hours=1)).isoformat()
        users[key] = {
            "joined_at": now.isoformat(),
            "first_notify_after": first_notify_after,
            "msg_used": {},
            "slot_queues": {},
            "slot_last": {},
        }
        logger.info(f"New user registered: {chat_id} — first notification after {first_notify_after} UTC")


def build_message(category: str, user_data: dict) -> str:
    """Pick a notification variant for the category (no repeats until all used)."""
    msg_list = CATEGORY_MSGS[category]
    msg_used = user_data.setdefault("msg_used", {})
    used: list = msg_used.get(category, [])
    available = [i for i in range(len(msg_list)) if i not in used]
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
    category = context.job.data
    slot_key = f"{category}"

    state = load_state()

    if is_slot_fired_today(state, slot_key):
        logger.info(f"Slot [{category}] already fired today — skipping duplicate")
        save_state(state)
        return

    users = get_users(state)
    if not users:
        logger.info("No users to notify yet.")
        save_state(state)
        return

    now = datetime.datetime.utcnow()
    sent_count = 0

    for chat_id_str, user_data in list(users.items()):
        first_notify_after_raw = user_data.get("first_notify_after")
        if not first_notify_after_raw:
            joined_at = user_data.get("joined_at")
            if joined_at:
                try:
                    first_notify_after_raw = (
                        datetime.datetime.fromisoformat(joined_at)
                        + datetime.timedelta(hours=1)
                    ).isoformat()
                    user_data["first_notify_after"] = first_notify_after_raw
                except Exception:
                    pass

        if first_notify_after_raw:
            try:
                if now < datetime.datetime.fromisoformat(first_notify_after_raw):
                    logger.info(f"Skipping {chat_id_str} — grace period until {first_notify_after_raw}")
                    continue
            except Exception:
                pass

        chat_id = int(chat_id_str)
        msg = build_message(category, user_data)

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            sent_count += 1
            logger.info(f"Notified user {chat_id} → [{category}]")
        except Exception as e:
            logger.warning(f"Failed to notify {chat_id} [{category}]: {e}")

    if sent_count > 0 or users:
        mark_slot_fired(state, slot_key)
        logger.info(f"Slot [{category}] marked as fired — notified {sent_count}/{len(users)} users")
    else:
        logger.info(f"Slot [{category}] had no eligible users (all in grace period)")

    save_state(state)


# ─── Catch-up function for missed slots on restart ───────────────────────────

async def catch_up_missed_slots(application: Application):
    state = load_state()
    now_syria = syria_now()
    today_str = now_syria.strftime("%Y-%m-%d")

    logger.info(f"Checking for missed slots on {today_str} at {now_syria.strftime('%H:%M')} Syria time")

    missed_slots = []

    for syria_h, syria_m, category in SCHEDULE:
        slot_key = category

        if is_slot_fired_today(state, slot_key):
            logger.info(f"Slot [{category}] already fired today — skipping catch-up")
            continue

        slot_syria = now_syria.replace(hour=syria_h, minute=syria_m, second=0, microsecond=0)

        if slot_syria < now_syria:
            logger.warning(f"Slot [{category}] scheduled at {syria_h:02d}:{syria_m:02d} has PASSED — will fire immediately")
            missed_slots.append((category, slot_syria))

    for category, scheduled_time in missed_slots:
        logger.info(f"Catching up missed slot: [{category}] (was scheduled at {scheduled_time.strftime('%H:%M')} Syria time)")

        state = load_state()
        if not is_slot_fired_today(state, category):
            users = get_users(state)
            now = datetime.datetime.utcnow()
            sent_count = 0

            for chat_id_str, user_data in list(users.items()):
                first_notify_after_raw = user_data.get("first_notify_after")
                if first_notify_after_raw:
                    try:
                        if now < datetime.datetime.fromisoformat(first_notify_after_raw):
                            continue
                    except Exception:
                        pass

                chat_id = int(chat_id_str)
                msg = build_message(category, user_data)

                try:
                    await application.bot.send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                    sent_count += 1
                    logger.info(f"Catch-up notified user {chat_id} → [{category}]")
                except Exception as e:
                    logger.warning(f"Catch-up failed for {chat_id} [{category}]: {e}")

            if sent_count > 0 or users:
                mark_slot_fired(state, category)
                logger.info(f"Catch-up completed for [{category}] — notified {sent_count} users")

        await asyncio.sleep(2)

    save_state(state)

    if not missed_slots:
        logger.info("No missed slots detected — all caught up!")


# ─── /start handler ───────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state()

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
        logger.info(f"New user {chat_id} registered — regular notifications start in 1 hour.")


# ─── Health check command ─────────────────────────────────────────────────────

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    now_syria = syria_now()
    today_str = now_syria.strftime("%Y-%m-%d")

    status_lines = [f"📅 *Today: {today_str}*", f"🕐 *Current Syria time: {now_syria.strftime('%H:%M')}*", ""]

    for syria_h, syria_m, category in SCHEDULE:
        slot_key = category
        fired = is_slot_fired_today(state, slot_key)
        slot_time = f"{syria_h:02d}:{syria_m:02d}"

        slot_syria = now_syria.replace(hour=syria_h, minute=syria_m, second=0, microsecond=0)

        if fired:
            status_txt = "✅ *DONE*"
        elif slot_syria < now_syria:
            status_txt = "⏰ *MISSED* (will catch up)"
        else:
            status_txt = "⏳ *PENDING*"

        emoji = CATEGORIES[category]["emoji"]
        status_lines.append(f"{emoji} {slot_time} {category}: {status_txt}")

    await update.message.reply_text(
        "\n".join(status_lines),
        parse_mode="Markdown"
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))

    async def post_init(application: Application):
        now_utc = datetime.datetime.utcnow()
        now_syria = syria_now()
        logger.info(f"Bot starting — UTC: {now_utc.strftime('%H:%M')}, Syria: {now_syria.strftime('%H:%M')}")

        await catch_up_missed_slots(application)

        for syria_h, syria_m, category in SCHEDULE:
            t = utc_time(syria_h, syria_m)

            application.job_queue.run_daily(
                send_notifications,
                time=t,
                data=category,
                name=f"slot_{category}_{syria_h:02d}{syria_m:02d}",
            )
            logger.info(f"Scheduled [{category}] at {syria_h:02d}:{syria_m:02d} Syria ({t.hour:02d}:{t.minute:02d} UTC)")

        state = load_state()
        slots_fired = state.get("slots_fired", {})
        if slots_fired:
            today = syria_now()
            seven_days_ago = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
            old_keys = [k for k in slots_fired.keys() if k < seven_days_ago]
            for k in old_keys:
                del slots_fired[k]
                logger.info(f"Cleaned up old slot_fired entry for {k}")
            save_state(state)

    app.post_init = post_init

    logger.info("Bot is running...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message"],
    )


if __name__ == "__main__":
    main()
