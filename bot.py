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

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

APP_URL = "https://t.me/NetbashaBot/netbasha"

STATE_FILE = "/tmp/bot_state.json"

# Deeplink opens app → category → specific site (by index in categorySites array)
# Format: category__index  e.g. "movies__0"  "anime__2"
def site_url(category: str, site_index: int) -> str:
    return f"{APP_URL}?startapp={category}__{site_index}"

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

SYRIA_UTC_OFFSET = 3

def syria_now():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=SYRIA_UTC_OFFSET)

def utc_time(syria_hour, syria_minute):
    total = syria_hour * 60 + syria_minute - (SYRIA_UTC_OFFSET * 60)
    total %= 1440
    return datetime.time(total // 60, total % 60)

# ══════════════════════════════════════════════════════════════════════════════
# SITE INDEX MAP — matches categorySites order in index.html exactly
# movies:  0=دليل الأفلام  1=كيو فيلم  2=المصطبة  3=مدينة الأفلام  4=مسلسلات تايم
#          5=كيبوراما      6=قصة عشق   7=لاروزا   8=فشار           9=أهواك
# tv:      0=دليل البرامج  1=قنوات عربية1  2=قنوات عربية2  3=قنوات عالمية
#          4=قنوات الدول   5=اذاعات راديو
# sports:  0=كووورة  1=365سكور  2=مباريات لايف1  3=مباريات لايف2
#          4=قنوات رياضة  5=رياضة عالمية
# anime:   0=أخبار الأنمي  1=دليل المانغا  2=قراءة المانغا
#          3=انمي فور اب  4=انمي بيك  5=اوك أنمي  6=ريستو  7=ويت أنمي  8=أنمي سيلفر
# music:   0=أنغامي  1=راديو نت باشا  2=بيلبورد عربية  3=تحميل mp3
#          4=تحميل ألبومات كاملة  5=أحدث الألبومات  6=أغاني أجنبي
# food:    0=وصفات شامية  1=وصفات عربية  2=فن الطهي  3=أكل وبس
#          4=غوودي  5=طخبات  6=أكل صحي  7=يمي  8=أطيب أكلة
# health:  0=مقالات طبية  1=منظمة الصحة العالمية  2=دايلي ميديكال
#          3=دليل الصحة  4=الصحة النفسية  5=الصحة و الجمال
# social:  0=فيسبوك  1=تويتر  2=انستغرام  3=يوتيوب  4=تيك توك
#          5=سناب شات  6=ديسكورد  7=تويتش  8=لينكد إن  9=واتساب
#          10=ثريدز  11=بينترست  12=ريديت  13=كورا  14=في كي
# books:   0=نور كتب  1=مكتبة سهم  2=كتباتي  3=المكتبة العربية
#          4=كتابك عندنا  5=مجلة الكتب العربية  6=قهوة غرب
# tech:    0=التقنية السورية  1=AI بدون حساب  2=أدوات AI  3=مقارنات أجهزة
#          4=شروحات ومراجعات  5=تطبيقات أندرويد  6=تطبيقات كومبيوتر
#          7=تطبيقات عامة  8=تطبيقات أبل
# ══════════════════════════════════════════════════════════════════════════════

CATEGORY_MSGS = {

    # ── HEALTH ────────────────────────────────────────────────────────────────
    "health": [
        lambda: (f"💊 *مقالات طبية*\n\nعندك سؤال طبي وبدك إجابة موثوقة؟ موقع الطبي فيه مقالات طبية محترفة — افتح وتصفح 🩺", site_url("health", 0)),
        lambda: (f"🌍 *منظمة الصحة العالمية*\n\nالمعلومة الصحية الصحيحة من مصدرها مباشرة. افتح موقع منظمة الصحة العالمية واكتشف 👀", site_url("health", 1)),
        lambda: (f"📋 *دايلي ميديكال*\n\nمعلومات طبية يومية متجددة من مصادر عالمية — دايلي ميديكال بانتظارك. افتح وتصفح 🔍", site_url("health", 2)),
        lambda: (f"📖 *دليل الصحة*\n\nدليل طبي شامل للأمراض والعلاجات والأدوية. افتح وابحث عن ما يهمك 💡", site_url("health", 3)),
        lambda: (f"🧠 *الصحة النفسية*\n\nمحتوى نفسي يساعدك تفهم نفسك أكتر. افتح موقع نفسياتي واكتشف 🌿", site_url("health", 4)),
        lambda: (f"✨ *الصحة والجمال*\n\nعناية بالجسم من الداخل والخارج. افتح موقع صحة وجمال وتصفح 💅", site_url("health", 5)),
        lambda: (f"💊 *مقالات طبية*\n\nموقع الطبي فيه مئات المقالات الطبية الموثوقة — افتح وابحث 🔎", site_url("health", 0)),
        lambda: (f"🌍 *منظمة الصحة العالمية*\n\nتقارير ومواضيع صحية عالمية من WHO — افتح واكتشف 🌐", site_url("health", 1)),
        lambda: (f"❤️ *دليل الصحة*\n\nMSD Manuals بالعربي — مرجع طبي كامل في يدك. افتح وتصفح 🌱", site_url("health", 3)),
        lambda: (f"🌿 *الصحة النفسية*\n\nمدونة نفسياتي للصحة النفسية — افتح وتصفح المحتوى 👇", site_url("health", 4)),
    ],

    # ── BOOKS ─────────────────────────────────────────────────────────────────
    "books": [
        lambda: (f"📗 *نور كتب*\n\nآلاف الكتب العربية للتحميل المجاني — نور كتب بانتظارك. افتح وتصفح 🌟", site_url("books", 0)),
        lambda: (f"📚 *مكتبة سهم*\n\nكتب PDF متنوعة جاهزة للقراءة — افتح مكتبة سهم واكتشف 📖", site_url("books", 1)),
        lambda: (f"📖 *كتباتي*\n\nكتب PDF مجانية من كل الأنواع — افتح كتباتي وتصفح 📂", site_url("books", 2)),
        lambda: (f"⭐ *المكتبة العربية*\n\nمكتبة عربية شاملة من موسقف — افتح واكتشف ما يناسبك 📚", site_url("books", 3)),
        lambda: (f"🗄️ *كتابك عندنا*\n\nدور على الكتاب اللي بدك إياه — افتح وابحث 🔍", site_url("books", 4)),
        lambda: (f"📰 *مجلة الكتب العربية*\n\nآخر أخبار عالم الكتب والأدب العربي — افتح وتصفح 🗞️", site_url("books", 5)),
        lambda: (f"☕ *قهوة غرب*\n\nمحتوى أدبي وثقافي يرافق قهوتك — افتح واستكشف 🌙", site_url("books", 6)),
        lambda: (f"📗 *نور كتب*\n\nوقت فراغ + كتاب من نور كتب = يوم أفضل. افتح وابدأ 📖", site_url("books", 0)),
        lambda: (f"📚 *مكتبة سهم*\n\nمكتبة سهم فيها كتب ما راح تلاقيها في مكان ثاني — افتح وتصفح 📚", site_url("books", 1)),
        lambda: (f"☕ *قهوة غرب*\n\nأفضل مرافق لقهوة الصباح — افتح قهوة غرب واقرأ 🌟", site_url("books", 6)),
    ],

    # ── SPORTS ────────────────────────────────────────────────────────────────
    "sports": [
        lambda: (f"⚽ *كووورة*\n\nآخر أخبار الرياضة والنتائج من كووورة — افتح وتابع ⚽", site_url("sports", 0)),
        lambda: (f"📊 *365 سكور*\n\nنتائج المباريات والترتيبات لحظة بلحظة — افتح 365 سكور وتصفح 🏆", site_url("sports", 1)),
        lambda: (f"🔴 *مباريات لايف 1*\n\nبث مباشر للمباريات هلق — افتح مباريات لايف وتابع 📺", site_url("sports", 2)),
        lambda: (f"🔴 *مباريات لايف 2*\n\nبث رياضي مباشر من مصدر ثاني — افتح وشوف مين يلعب هلق ⚡", site_url("sports", 3)),
        lambda: (f"📡 *قنوات رياضية*\n\nقنوات رياضية ببث مباشر — افتح واختار قناتك 📺", site_url("sports", 4)),
        lambda: (f"🌍 *رياضة عالمية*\n\nرياضات عالمية متنوعة من سبورتيكا — افتح واكتشف 🏅", site_url("sports", 5)),
        lambda: (f"⚽ *كووورة*\n\nشو صار بالرياضة اليوم؟ كووورة عندها كل شي — افتح وتابع 📱", site_url("sports", 0)),
        lambda: (f"📊 *365 سكور*\n\nترتيبات الدوريات والنتائج المباشرة — افتح 365 سكور ⚡", site_url("sports", 1)),
        lambda: (f"🌐 *رياضة عالمية*\n\nمن الملاعب المحلية للبطولات العالمية — افتح سبورتيكا واكتشف ⚡", site_url("sports", 5)),
        lambda: (f"📡 *قنوات رياضية*\n\nقنوات رياضية مباشرة بانتظارك — افتح وتابع هلق 🔴", site_url("sports", 4)),
    ],

    # ── SOCIAL ────────────────────────────────────────────────────────────────
    "social": [
        lambda: (f"📘 *فيسبوك*\n\nإشعاراتك ومجموعاتك على فيسبوك بانتظارك — افتح وتصفح 👀", site_url("social", 0)),
        lambda: (f"🐦 *تويتر / X*\n\nشو ترند هلق على X؟ افتح واكتشف 🔥", site_url("social", 1)),
        lambda: (f"📷 *انستغرام*\n\nريلز وستوريز جديدة — افتح انستغرام وتصفح 📸", site_url("social", 2)),
        lambda: (f"📹 *يوتيوب*\n\nمحتوى جديد بانتظارك على يوتيوب — افتح وشوف الجديد ▶️", site_url("social", 3)),
        lambda: (f"🎵 *تيك توك*\n\nالترند الجديد على تيك توك — افتح واكتشف بنفسك 🎬", site_url("social", 4)),
        lambda: (f"👻 *سناب شات*\n\nستوريز سناب بانتظارك — افتح وتصفح 👀", site_url("social", 5)),
        lambda: (f"🎮 *ديسكورد*\n\nسيرفرك على ديسكورد بانتظارك — افتح وانضم 🔗", site_url("social", 6)),
        lambda: (f"🟣 *تويتش*\n\nستريمات مباشرة على تويتش — افتح وشوف مين online 🔴", site_url("social", 7)),
        lambda: (f"💼 *لينكد إن*\n\nشبكتك المهنية على لينكد إن — افتح وتصفح 🌐", site_url("social", 8)),
        lambda: (f"📌 *بينترست*\n\nأفكار وإلهام على بينترست — افتح واكتشف ما يلهمك 🎨", site_url("social", 11)),
    ],

    # ── FOOD ──────────────────────────────────────────────────────────────────
    "food": [
        lambda: (f"🌶️ *وصفات شامية*\n\nالمطبخ الشامي الأصيل بكل تفاصيله — افتح شامي فود واستكشف الوصفات 🍽️", site_url("food", 0)),
        lambda: (f"🍳 *وصفات عربية*\n\nمطابخ عربية من كل الدول في مكان واحد — افتح واكتشف الوصفات 👨‍🍳", site_url("food", 1)),
        lambda: (f"👩‍🍳 *فن الطهي*\n\nأكلات من كل مطابخ العالم — افتح وتصفح ما يشهيك 🌍", site_url("food", 2)),
        lambda: (f"🍲 *أكل وبس*\n\nطبخ بدون تعقيد — افتح أكل وبس واكتشف وصفات اليوم 🔥", site_url("food", 3)),
        lambda: (f"🍰 *غوودي*\n\nوصفات احترافية بخطوات واضحة — افتح غوودي كيتشن وتصفح 🎂", site_url("food", 4)),
        lambda: (f"🥘 *طخبات*\n\nآلاف الوصفات بالتفصيل — افتح طخبات واختار وصفتك 🍽️", site_url("food", 5)),
        lambda: (f"🥗 *أكل صحي*\n\nوصفات صحية وعملية للحياة اليومية — افتح Helthy Cooking وتصفح 🥦", site_url("food", 6)),
        lambda: (f"🍱 *يمي*\n\nطبخات يومية لذيذة وسهلة — افتح يمي واكتشف شو تطبخ اليوم 😋", site_url("food", 7)),
        lambda: (f"🍳 *أطيب أكلة*\n\nوصفات من كل المطابخ — افتح أطيب أكلة وتصفح الأكلات 🌶️", site_url("food", 8)),
        lambda: (f"🌶️ *وصفات شامية*\n\nأكلات شامية أصيلة بوصفات تفصيلية — افتح شامي فود وتصفح 🍽️", site_url("food", 0)),
    ],

    # ── TECH ──────────────────────────────────────────────────────────────────
    "tech": [
        lambda: (f"🛠️ *التقنية السورية*\n\nأخبار التقنية باللهجة اللي نعرفها — افتح التقنية السورية وتصفح 💻", site_url("tech", 0)),
        lambda: (f"🤖 *AI بدون حساب*\n\nجرب الذكاء الاصطناعي هلق بدون تسجيل — افتح Duck AI وجرب 🚀", site_url("tech", 1)),
        lambda: (f"⚙️ *أدوات AI*\n\nأدوات ذكاء اصطناعي مجانية ومفيدة — افتح واكتشف ما يفيدك 🧠", site_url("tech", 2)),
        lambda: (f"📊 *مقارنات أجهزة*\n\nقارن بين أي جهازين — افتح 3edda وتصفح المقارنات 🔍", site_url("tech", 3)),
        lambda: (f"📱 *شروحات ومراجعات*\n\nشرح تقني أو مراجعة جهاز جديد — افتح 3arrafni واكتشف 📖", site_url("tech", 4)),
        lambda: (f"📲 *تطبيقات أندرويد*\n\nتطبيقات أندرويد مدفوعة مجاناً — افتح APK Play وتصفح ⬇️", site_url("tech", 5)),
        lambda: (f"💻 *تطبيقات كومبيوتر*\n\nبرامج كمبيوتر مدفوعة متاحة — افتح Traidsoft واكتشف 🖥️", site_url("tech", 6)),
        lambda: (f"📦 *تطبيقات عامة*\n\nتطبيقات لكل الأنظمة — افتح Softmany وتصفح 🍎", site_url("tech", 7)),
        lambda: (f"🍎 *تطبيقات أبل*\n\nApp Store مباشرة — ابحث عن التطبيق اللي بتحتاجه 📱", site_url("tech", 8)),
        lambda: (f"🤖 *أدوات AI*\n\nأحدث أدوات الذكاء الاصطناعي — افتح AI Arabai واكتشف 🌐", site_url("tech", 2)),
    ],

    # ── MOVIES ────────────────────────────────────────────────────────────────
    "movies": [
        lambda: (f"🎬 *دليل الأفلام*\n\nشو الجديد بالأفلام والمسلسلات والسينما؟ افتح دليل الأفلام واكتشف 🎥", site_url("movies", 0)),
        lambda: (f"🎭 *دليل الأفلام*\n\nشو الدراما الجديدة هالموسم؟ دليل الأفلام عنده كل الإجابات — افتح وتصفح 📺", site_url("movies", 0)),
        lambda: (f"🎞️ *كيو فيلم*\n\nأفلام ومسلسلات جاهزة للمشاهدة — افتح كيو فيلم وتصفح 🍿", site_url("movies", 1)),
        lambda: (f"🌍 *المصطبة*\n\nمحتوى عربي وعالمي متنوع — افتح المصطبة واكتشف 🎬", site_url("movies", 2)),
        lambda: (f"🍿 *مدينة الأفلام*\n\nمو عارف شو تشوف الليلة؟ افتح مدينة الأفلام واكتشف 🎦", site_url("movies", 3)),
        lambda: (f"📽️ *مسلسلات تايم*\n\nمسلسلات عربية وعالمية — افتح مسلسلات تايم وتصفح 🎞️", site_url("movies", 4)),
        lambda: (f"🎬 *قصة عشق*\n\nمسلسلات تركية مدبلجة ومترجمة — افتح قصة عشق واكتشف 🌹", site_url("movies", 6)),
        lambda: (f"⭐ *كيبوراما*\n\nدراما كورية مترجمة للعربي — افتح كيبوراما وتصفح 🌏", site_url("movies", 5)),
        lambda: (f"🎥 *فشار*\n\nأفلام ومسلسلات جاهزة للمشاهدة — افتح فشار وتصفح 🎭", site_url("movies", 8)),
        lambda: (f"🎬 *دليل الأفلام*\n\nآخر أخبار السينما والدراما — افتح دليل الأفلام واكتشف 🌟", site_url("movies", 0)),
    ],

    # ── ANIME ─────────────────────────────────────────────────────────────────
    "anime": [
        lambda: (f"🎌 *أخبار الأنمي*\n\nشو الجديد بعالم الأنمي هالموسم؟ افتح أخبار الأنمي واكتشف 🌸", site_url("anime", 0)),
        lambda: (f"📖 *دليل المانغا*\n\nدور على مانغا جديدة أو تابع اللي بتقرأها — افتح دليل المانغا وتصفح 📚", site_url("anime", 1)),
        lambda: (f"📖 *قراءة المانغا*\n\nاقرأ المانغا مباشرة من عسق — فصول جديدة في انتظارك. افتح وتابع 🎌", site_url("anime", 2)),
        lambda: (f"🎌 *انمي فور اب*\n\nأنمي مترجم للعربي جاهز للمشاهدة — افتح انمي فور اب واكتشف 🌟", site_url("anime", 3)),
        lambda: (f"⚔️ *انمي بيك*\n\nمكتبة أنمي كبيرة بانتظارك — افتح انمي بيك وتصفح 🔍", site_url("anime", 4)),
        lambda: (f"🌸 *اوك أنمي*\n\nأنمي جديد وقديم — افتح اوك أنمي وتابع مشاهدتك 🎬", site_url("anime", 5)),
        lambda: (f"🎌 *ريستو أنمي*\n\nموقع أنمي آخر متاح — افتح ريستو واكتشف ما يناسبك 🎯", site_url("anime", 6)),
        lambda: (f"🌺 *ويت أنمي*\n\nأنمي مترجم ومنظم — افتح ويت أنمي وتصفح 🎌", site_url("anime", 7)),
        lambda: (f"📰 *أخبار الأنمي*\n\nإعلانات ومواسم جديدة وأخبار عالم الأنمي — افتح وتابع 🎌", site_url("anime", 0)),
        lambda: (f"📖 *دليل المانغا*\n\nدليل شامل للمانغا العربية والمترجمة — افتح وتصفح 🌸", site_url("anime", 1)),
    ],

    # ── MUSIC ─────────────────────────────────────────────────────────────────
    "music": [
        lambda: (f"🎵 *راديو نت باشا*\n\nراديو موسيقى 24 ساعة مدمج — افتح وابدأ الاستماع هلق 🎧", site_url("music", 1)),
        lambda: (f"📰 *بيلبورد عربية*\n\nآخر أخبار الموسيقى العربية والعالمية — افتح وتصفح 🎶", site_url("music", 2)),
        lambda: (f"⬇️ *تحميل mp3*\n\nأغاني mp3 جاهزة للتحميل من نجوم ستارز — افتح وابحث عن أغنيتك 🎤", site_url("music", 3)),
        lambda: (f"💿 *تحميل ألبومات كاملة*\n\nحمّل ألبومات كاملة من مر مازيكا — افتح وتصفح 🎼", site_url("music", 4)),
        lambda: (f"🆕 *أحدث الألبومات*\n\nأحدث إصدارات الألبومات العربية والعالمية — افتح مطبعة واكتشف 🎵", site_url("music", 5)),
        lambda: (f"🌍 *أغاني أجنبي*\n\nموسيقى عالمية مرخصة مجانية من جامندو — افتح واستكشف 🎸", site_url("music", 6)),
        lambda: (f"🎵 *أنغامي*\n\nالموسيقى العربية الأصيلة على أنغامي — افتح واستمع 🎶", site_url("music", 0)),
        lambda: (f"📻 *راديو نت باشا*\n\nموسيقى مستمرة 24 ساعة بدون انقطاع — افتح وابدأ 🎧", site_url("music", 1)),
        lambda: (f"🎤 *تحميل mp3*\n\nابحث عن أغنيتك وحملها مباشرة — افتح نجوم ستارز 🎵", site_url("music", 3)),
        lambda: (f"🎵 *أنغامي*\n\nاستمع لأغانيك المفضلة على أنغامي — افتح هلق 🎶", site_url("music", 0)),
    ],

    # ── TV / CHANNELS ─────────────────────────────────────────────────────────
    "tv": [
        lambda: (f"📺 *دليل البرامج*\n\nشو عم ينبث هلق على القنوات العربية؟ افتح دليل البرامج وتصفح 🕐", site_url("tv", 0)),
        lambda: (f"📡 *قنوات عربية*\n\nقنوات عربية ببث مباشر — افتح واختار قناتك 🔴", site_url("tv", 1)),
        lambda: (f"📡 *قنوات عربية 2*\n\nبث مباشر للقنوات العربية من مصدر تاني — افتح وتصفح 📺", site_url("tv", 2)),
        lambda: (f"🌍 *قنوات عالمية*\n\nقنوات من كل بلاد العالم ببث مباشر — افتح واكتشف 🌐", site_url("tv", 3)),
        lambda: (f"🗺️ *قنوات الدول*\n\nابحث عن قنوات أي بلد بدك من globetv — افتح وتصفح 🌍", site_url("tv", 4)),
        lambda: (f"📻 *إذاعات راديو*\n\nمحطات راديو عربية متنوعة ببث مباشر — افتح وتصفح واستمع 🎙️", site_url("tv", 5)),
        lambda: (f"🔴 *قنوات عربية*\n\nقنواتك المفضلة ببث مباشر هلق — افتح وتابع 📡", site_url("tv", 1)),
        lambda: (f"📺 *دليل البرامج*\n\nاعرف شو عم يطلع هلق على كل قناة — افتح دليل البرامج 📺", site_url("tv", 0)),
        lambda: (f"🎙️ *إذاعات راديو*\n\nاستمع لمحطات الراديو العربية من أي مكان — افتح وتصفح 📻", site_url("tv", 5)),
        lambda: (f"🌐 *قنوات الدول*\n\nقنوات أي دولة بالعالم — ابحث وشاهد من globetv 🗺️", site_url("tv", 4)),
    ],
}

WELCOME_MSG = """\
👋 *أهلاً بك في نت باشا!*

ابحث عن أي شي يهمك — أفلام، رياضة، موسيقى، تقنية، وصفات، كتب، أنمي، قنوات مباشرة، وأكثر 🔍

كل شي في مكان واحد. افتح وابدأ 👇\
"""

# ─── State helpers ────────────────────────────────────────────────────────────

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def get_users(state):
    return state.setdefault("users", {})

def get_slots_fired(state):
    return state.setdefault("slots_fired", {})

def mark_slot_fired(state, slot_key):
    today = syria_now().strftime("%Y-%m-%d")
    slots_fired = get_slots_fired(state)
    if today not in slots_fired:
        slots_fired[today] = {}
    slots_fired[today][slot_key] = True
    save_state(state)

def is_slot_fired_today(state, slot_key):
    today = syria_now().strftime("%Y-%m-%d")
    return get_slots_fired(state).get(today, {}).get(slot_key, False)

def register_user(state, chat_id):
    users = get_users(state)
    key = str(chat_id)
    if key not in users:
        now = datetime.datetime.utcnow()
        first_notify_after = (now + datetime.timedelta(hours=1)).isoformat()
        users[key] = {
            "joined_at": now.isoformat(),
            "first_notify_after": first_notify_after,
            "msg_used": {},
        }
        logger.info(f"New user registered: {chat_id}")

def build_message(category, user_data):
    """Pick a variant, return (text, url). No repeats until all used."""
    msg_list = CATEGORY_MSGS[category]
    msg_used = user_data.setdefault("msg_used", {})
    used = msg_used.get(category, [])
    available = [i for i in range(len(msg_list)) if i not in used]
    if not available:
        used = []
        available = list(range(len(msg_list)))
    idx = random.choice(available)
    used.append(idx)
    msg_used[category] = used
    text, url = msg_list[idx]()
    return text, url

# ─── Send notifications ───────────────────────────────────────────────────────

async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    category = context.job.data
    state = load_state()

    if is_slot_fired_today(state, category):
        logger.info(f"Slot [{category}] already fired today — skipping")
        return

    users = get_users(state)
    if not users:
        save_state(state)
        return

    now = datetime.datetime.utcnow()
    sent_count = 0

    for chat_id_str, user_data in list(users.items()):
        fnr = user_data.get("first_notify_after")
        if fnr:
            try:
                if now < datetime.datetime.fromisoformat(fnr):
                    continue
            except Exception:
                pass

        chat_id = int(chat_id_str)
        text, url = build_message(category, user_data)

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{CATEGORIES[category]['emoji']} افتح نت باشا", url=url)
        ]])

        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
                disable_web_page_preview=True,
            )
            sent_count += 1
        except Exception as e:
            logger.warning(f"Failed to notify {chat_id}: {e}")

    mark_slot_fired(state, category)
    logger.info(f"[{category}] notified {sent_count}/{len(users)} users")
    save_state(state)

# ─── Catch-up missed slots ────────────────────────────────────────────────────

async def catch_up_missed_slots(application):
    state = load_state()
    now_syria = syria_now()
    logger.info(f"Checking missed slots — Syria time: {now_syria.strftime('%H:%M')}")

    for syria_h, syria_m, category in SCHEDULE:
        if is_slot_fired_today(state, category):
            continue
        slot_syria = now_syria.replace(hour=syria_h, minute=syria_m, second=0, microsecond=0)
        if slot_syria >= now_syria:
            continue

        logger.warning(f"Catching up missed slot: [{category}] was {syria_h:02d}:{syria_m:02d}")
        state = load_state()
        if is_slot_fired_today(state, category):
            continue

        users = get_users(state)
        now = datetime.datetime.utcnow()
        sent_count = 0

        for chat_id_str, user_data in list(users.items()):
            fnr = user_data.get("first_notify_after")
            if fnr:
                try:
                    if now < datetime.datetime.fromisoformat(fnr):
                        continue
                except Exception:
                    pass

            chat_id = int(chat_id_str)
            text, url = build_message(category, user_data)
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(f"{CATEGORIES[category]['emoji']} افتح نت باشا", url=url)
            ]])

            try:
                await application.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                    disable_web_page_preview=True,
                )
                sent_count += 1
            except Exception as e:
                logger.warning(f"Catch-up failed {chat_id}: {e}")

        mark_slot_fired(state, category)
        logger.info(f"Catch-up [{category}] — notified {sent_count} users")
        await asyncio.sleep(2)

    save_state(state)

# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state = load_state()
    register_user(state, chat_id)
    save_state(state)

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 افتح نت باشا", url=APP_URL)
    ]])
    await update.message.reply_text(
        WELCOME_MSG,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    now_syria = syria_now()
    today_str = now_syria.strftime("%Y-%m-%d")
    lines = [f"📅 *{today_str}*", f"🕐 *{now_syria.strftime('%H:%M')} Syria*", ""]
    for syria_h, syria_m, category in SCHEDULE:
        fired = is_slot_fired_today(state, category)
        slot = now_syria.replace(hour=syria_h, minute=syria_m, second=0, microsecond=0)
        if fired:       s = "✅ DONE"
        elif slot < now_syria: s = "⏰ MISSED"
        else:           s = "⏳ PENDING"
        lines.append(f"{CATEGORIES[category]['emoji']} {syria_h:02d}:{syria_m:02d} {category}: {s}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))

    async def post_init(application):
        await catch_up_missed_slots(application)
        for syria_h, syria_m, category in SCHEDULE:
            t = utc_time(syria_h, syria_m)
            application.job_queue.run_daily(
                send_notifications,
                time=t,
                data=category,
                name=f"slot_{category}",
            )
            logger.info(f"Scheduled [{category}] {syria_h:02d}:{syria_m:02d} Syria → {t.hour:02d}:{t.minute:02d} UTC")

        # Clean old slot_fired entries
        state = load_state()
        slots_fired = state.get("slots_fired", {})
        cutoff = (syria_now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        for k in [k for k in slots_fired if k < cutoff]:
            del slots_fired[k]
        save_state(state)

    app.post_init = post_init
    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message"])

if __name__ == "__main__":
    main()
