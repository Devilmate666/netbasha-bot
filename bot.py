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

# ─── Exact send schedule (Syrian time UTC+3) ─────────────────────────────────
# Each entry: (hour, minute, [categories])  — all times in Syria local time.
# The bot schedules a run_daily job for each time; the job picks one category
# from the paired list (shuffled round-robin) and sends it to all users.
SCHEDULE = [
    # Morning  06:00 – 10:00  →  Health & Food
    ( 6,  0, ["health", "food"]),
    ( 7, 30, ["health", "food"]),
    ( 9,  0, ["health", "food"]),
    # Afternoon 12:30 – 15:30  →  Music & Social
    (12, 30, ["music",  "social"]),
    (14,  0, ["music",  "social"]),
    (15, 30, ["music",  "social"]),
    # Evening  17:30 – 19:00  →  Movies & Anime
    (17, 30, ["movies", "anime"]),
    (18, 15, ["movies", "anime"]),
    (19,  0, ["movies", "anime"]),
    # Night    21:00 – 23:00  →  Channels & Sports
    (21,  0, ["tv",     "sports"]),
    (22,  0, ["tv",     "sports"]),
    (23,  0, ["tv",     "sports"]),
    # Late     00:00 – 02:00  →  Tech & Books
    ( 0,  0, ["tech",   "books"]),
    ( 1,  0, ["tech",   "books"]),
    ( 2,  0, ["tech",   "books"]),
]

def utc_time(syria_hour: int, syria_minute: int) -> datetime.time:
    """Convert a Syria-local (UTC+3) time to UTC datetime.time for job scheduling."""
    total = syria_hour * 60 + syria_minute - 180   # subtract 3 h
    total %= 1440                                    # wrap around midnight
    return datetime.time(total // 60, total % 60)


# ─── Notification messages — 10 per category ─────────────────────────────────
CATEGORY_MSGS: dict[str, list] = {

    "health": [
        lambda url: (
            f"💊 *صحة ولياقة بدنية*\n\n"
            f"قسم الصحة في *نت باشا* يضم مقالات ونصائح حول التغذية السليمة، النوم الصحي، واللياقة البدنية 🌿\n\n"
            f"👉 [افتح قسم الصحة]({url})"
        ),
        lambda url: (
            f"💪 *نصائح اللياقة البدنية*\n\n"
            f"في *نت باشا* ستجد تمارين وإرشادات للحفاظ على نشاطك اليومي، مناسبة لمختلف المستويات 🏃\n\n"
            f"👉 [تصفح قسم الصحة]({url})"
        ),
        lambda url: (
            f"🥗 *التغذية الصحية*\n\n"
            f"نصائح حول الوجبات المتوازنة وأهمية شرب الماء وتناول الفيتامينات — كلها في قسم الصحة بـ *نت باشا* 🍎\n\n"
            f"👉 [اقرأ عن التغذية]({url})"
        ),
        lambda url: (
            f"😴 *النوم الصحي مهم*\n\n"
            f"مقالات عن تحسين جودة النوم وعادات ما قبل النوم متوفرة في قسم الصحة على *نت باشا* 🌙\n\n"
            f"👉 [اكتشف قسم الصحة]({url})"
        ),
        lambda url: (
            f"🧘 *الصحة النفسية والاسترخاء*\n\n"
            f"مقالات حول إدارة التوتر والتأمل والاسترخاء — جزء من محتوى قسم الصحة في *نت باشا* 🌸\n\n"
            f"👉 [تصفح المحتوى الصحي]({url})"
        ),
        lambda url: (
            f"🏋️ *تمارين منزلية*\n\n"
            f"قسم الصحة في *نت باشا* يتضمن تمارين يمكن ممارستها في المنزل دون الحاجة لمعدات 🏠\n\n"
            f"👉 [شاهد التمارين]({url})"
        ),
        lambda url: (
            f"💧 *العادات اليومية الصحية*\n\n"
            f"من شرب الماء إلى المشي اليومي — محتوى قسم الصحة في *نت باشا* يغطي العادات البسيطة المفيدة ✅\n\n"
            f"👉 [افتح قسم الصحة]({url})"
        ),
        lambda url: (
            f"🍏 *الوزن الصحي والتوازن الغذائي*\n\n"
            f"مقالات حول الحفاظ على وزن صحي وتجنب الأنظمة الغذائية المتطرفة — في قسم الصحة بـ *نت باشا* ⚖️\n\n"
            f"👉 [اقرأ المزيد]({url})"
        ),
        lambda url: (
            f"🦷 *الصحة العامة والوقاية*\n\n"
            f"نصائح وقائية ومعلومات صحية عامة متاحة لك في قسم الصحة على *نت باشا* 🩺\n\n"
            f"👉 [تصفح قسم الصحة]({url})"
        ),
        lambda url: (
            f"🌞 *ابدأ يومك بنشاط*\n\n"
            f"اقتراحات لروتين الصباح والعادات التي تساعدك على البدء بطاقة — ضمن محتوى الصحة في *نت باشا* ☀️\n\n"
            f"👉 [افتح قسم الصحة]({url})"
        ),
    ],

    "food": [
        lambda url: (
            f"🍲 *وصفات المطبخ العربي*\n\n"
            f"قسم الطبخ في *نت باشا* يضم وصفات من مختلف المطابخ العربية موضحة بالمقادير وخطوات التحضير 👨‍🍳\n\n"
            f"👉 [افتح قسم الطبخ]({url})"
        ),
        lambda url: (
            f"🥘 *أطباق رئيسية متنوعة*\n\n"
            f"ستجد في قسم الطبخ بـ *نت باشا* وصفات للأطباق الرئيسية مرتبة حسب نوع المطبخ وسهولة التحضير 🍽️\n\n"
            f"👉 [تصفح الوصفات]({url})"
        ),
        lambda url: (
            f"🧁 *حلويات ومعجنات*\n\n"
            f"وصفات الحلويات العربية والمعجنات متوفرة في قسم الطبخ على *نت باشا* مع تفاصيل المقادير 🍮\n\n"
            f"👉 [شاهد وصفات الحلويات]({url})"
        ),
        lambda url: (
            f"🥗 *سلطات وأطباق خفيفة*\n\n"
            f"قسم الطبخ في *نت باشا* يتضمن وصفات للسلطات والأكلات الخفيفة المناسبة لوجبة سريعة 🥙\n\n"
            f"👉 [اكتشف الأطباق الخفيفة]({url})"
        ),
        lambda url: (
            f"🍳 *وصفات الإفطار*\n\n"
            f"أفكار لوجبات الإفطار البسيطة والمغذية موجودة في قسم الطبخ بـ *نت باشا* ☕\n\n"
            f"👉 [افتح قسم الطبخ]({url})"
        ),
        lambda url: (
            f"🌶️ *مطبخ الشام والتوابل*\n\n"
            f"وصفات المطبخ الشامي بتوابله وأطباقه الأصيلة حاضرة في قسم الطبخ على *نت باشا* 🫙\n\n"
            f"👉 [تصفح مطبخ الشام]({url})"
        ),
        lambda url: (
            f"🍖 *مشاوي ومقبلات*\n\n"
            f"وصفات المشاوي والمقبلات بتفاصيلها الكاملة متاحة في قسم الطبخ بـ *نت باشا* 🔥\n\n"
            f"👉 [شاهد وصفات المشاوي]({url})"
        ),
        lambda url: (
            f"🫖 *مشروبات ساخنة وباردة*\n\n"
            f"وصفات المشروبات التقليدية والعصائر الطازجة جزء من محتوى قسم الطبخ في *نت باشا* 🧃\n\n"
            f"👉 [اكتشف المشروبات]({url})"
        ),
        lambda url: (
            f"👩‍🍳 *وصفات سريعة وعملية*\n\n"
            f"في قسم الطبخ بـ *نت باشا* ستجد وصفات مختصرة الوقت مناسبة لجداول الحياة المشغولة ⏱️\n\n"
            f"👉 [افتح الوصفات السريعة]({url})"
        ),
        lambda url: (
            f"🍱 *وصفات صحية ومتوازنة*\n\n"
            f"قسم الطبخ في *نت باشا* يضم وصفات مراعية للتوازن الغذائي بمكونات يومية بسيطة 🥦\n\n"
            f"👉 [تصفح قسم الطبخ]({url})"
        ),
    ],

    "music": [
        lambda url: (
            f"🎵 *موسيقى عربية وعالمية*\n\n"
            f"قسم الموسيقى في *نت باشا* يضم أغاني من مختلف الأجيال والأنواع، عربية وعالمية 🎶\n\n"
            f"👉 [افتح قسم الموسيقى]({url})"
        ),
        lambda url: (
            f"🎧 *أغاني متعددة الأنواع*\n\n"
            f"من الطرب الكلاسيكي إلى الموسيقى الحديثة — تجد في *نت باشا* محتوى يناسب أذواق مختلفة 🎼\n\n"
            f"👉 [تصفح قسم الموسيقى]({url})"
        ),
        lambda url: (
            f"🎤 *أغاني عربية متنوعة*\n\n"
            f"قسم الموسيقى بـ *نت باشا* يغطي أعمالاً من فنانين عرب من مختلف الدول والتوجهات الفنية 🌍\n\n"
            f"👉 [استمع الآن]({url})"
        ),
        lambda url: (
            f"🎸 *موسيقى بلا حدود*\n\n"
            f"الموسيقى الغربية والعالمية متوفرة أيضاً في قسم الموسيقى بـ *نت باشا* بأنواع متعددة 🌐\n\n"
            f"👉 [اكتشف الموسيقى العالمية]({url})"
        ),
        lambda url: (
            f"🎹 *كلاسيكيات الطرب العربي*\n\n"
            f"أعمال الفنانين الكبار وكلاسيكيات الطرب العربي جزء من مكتبة الموسيقى في *نت باشا* 🕊️\n\n"
            f"👉 [تصفح الكلاسيكيات]({url})"
        ),
        lambda url: (
            f"🎺 *موسيقى للتركيز والاسترخاء*\n\n"
            f"أنواع الموسيقى الهادئة والأصوات المريحة موجودة في قسم الموسيقى على *نت باشا* 🌿\n\n"
            f"👉 [افتح قسم الموسيقى]({url})"
        ),
        lambda url: (
            f"🎻 *موسيقى شرقية أصيلة*\n\n"
            f"الموسيقى الشرقية بآلاتها التقليدية متاحة ضمن محتوى قسم الموسيقى بـ *نت باشا* 🪕\n\n"
            f"👉 [استمع للموسيقى الشرقية]({url})"
        ),
        lambda url: (
            f"🥁 *إيقاعات وأنواع متجددة*\n\n"
            f"الأنواع الموسيقية الحديثة من راب وبوب وغيرها متوفرة في قسم الموسيقى بـ *نت باشا* 🎙️\n\n"
            f"👉 [تصفح الأنواع الحديثة]({url})"
        ),
        lambda url: (
            f"🎵 *مكتبة موسيقية واسعة*\n\n"
            f"*نت باشا* يجمع لك محتوى موسيقياً متنوعاً يمكنك تصفحه واختيار ما يناسب وقتك 🎶\n\n"
            f"👉 [افتح قسم الموسيقى]({url})"
        ),
        lambda url: (
            f"🎧 *أغاني مناسبة لكل وقت*\n\n"
            f"سواء كنت في العمل أو الراحة، قسم الموسيقى في *نت باشا* يوفر لك محتوى لكل مزاج 🎼\n\n"
            f"👉 [استمع الآن]({url})"
        ),
    ],

    "social": [
        lambda url: (
            f"📱 *محتوى منصات التواصل الاجتماعي*\n\n"
            f"قسم التواصل في *نت باشا* يجمع محتوى من تيك توك وإنستغرام ويوتيوب في تطبيق واحد 📲\n\n"
            f"👉 [افتح قسم التواصل]({url})"
        ),
        lambda url: (
            f"🌐 *تصفح المنصات بسهولة*\n\n"
            f"بدلاً من فتح تطبيقات متعددة، *نت باشا* يتيح لك الوصول لمحتوى المنصات المختلفة من مكان واحد 🔗\n\n"
            f"👉 [تصفح قسم التواصل]({url})"
        ),
        lambda url: (
            f"📲 *فيديوهات من تيك توك وإنستغرام*\n\n"
            f"قسم التواصل الاجتماعي بـ *نت باشا* يعرض محتوى مرئياً من أبرز المنصات 🎥\n\n"
            f"👉 [شاهد المحتوى]({url})"
        ),
        lambda url: (
            f"📊 *محتوى متنوع من المنصات*\n\n"
            f"من التعليمي إلى الترفيهي، قسم التواصل في *نت باشا* يضم محتوى من عدة منصات 🌍\n\n"
            f"👉 [اكتشف قسم التواصل]({url})"
        ),
        lambda url: (
            f"🔔 *تابع المنصات من مكان واحد*\n\n"
            f"*نت باشا* يسهّل متابعة محتوى التواصل الاجتماعي دون الحاجة للتنقل بين تطبيقات مختلفة 📡\n\n"
            f"👉 [افتح قسم التواصل]({url})"
        ),
        lambda url: (
            f"🎞️ *ريلز وفيديوهات قصيرة*\n\n"
            f"الفيديوهات القصيرة من مختلف المنصات متاحة في قسم التواصل الاجتماعي بـ *نت باشا* ▶️\n\n"
            f"👉 [تصفح الفيديوهات]({url})"
        ),
        lambda url: (
            f"📱 *محتوى عربي وعالمي*\n\n"
            f"قسم التواصل في *نت باشا* لا يقتصر على محتوى بعينه — عربي وعالمي، ترفيهي وتثقيفي 🌐\n\n"
            f"👉 [اكتشف المحتوى]({url})"
        ),
        lambda url: (
            f"🤝 *منصة متعددة في تطبيق واحد*\n\n"
            f"الفكرة الأساسية لقسم التواصل في *نت باشا* هي تجميع محتوى عدة منصات بشكل مريح 📲\n\n"
            f"👉 [جرّب قسم التواصل]({url})"
        ),
        lambda url: (
            f"🌟 *محتوى مقتبس من الفضاء الرقمي*\n\n"
            f"في *نت باشا* ستجد محتوى متنوعاً من إنستغرام وتيك توك ويوتيوب مرتباً في قسم واحد 🔍\n\n"
            f"👉 [افتح قسم التواصل]({url})"
        ),
        lambda url: (
            f"💬 *تابع ما يشاهده الناس*\n\n"
            f"قسم التواصل الاجتماعي في *نت باشا* يمنحك نظرة على ما يُشارك عبر المنصات الكبرى 👀\n\n"
            f"👉 [تصفح قسم التواصل]({url})"
        ),
    ],

    "movies": [
        lambda url: (
            f"🎬 *أفلام ومسلسلات متنوعة*\n\n"
            f"قسم الأفلام والمسلسلات في *نت باشا* يضم محتوى عربياً وعالمياً من أنواع مختلفة 🍿\n\n"
            f"👉 [افتح قسم الأفلام]({url})"
        ),
        lambda url: (
            f"📽️ *مسلسلات عربية وأجنبية*\n\n"
            f"ستجد في *نت باشا* مسلسلات من مختلف الدول والأنواع — دراما، كوميديا، تشويق وغيرها 🎭\n\n"
            f"👉 [تصفح المسلسلات]({url})"
        ),
        lambda url: (
            f"🎥 *أفلام من عدة أنواع*\n\n"
            f"الأكشن، الرومانسية، الرعب، والكوميديا — قسم الأفلام في *نت باشا* يغطي أنواعاً متعددة 🎞️\n\n"
            f"👉 [تصفح الأفلام]({url})"
        ),
        lambda url: (
            f"🌍 *إنتاجات من حول العالم*\n\n"
            f"قسم الأفلام والمسلسلات في *نت باشا* لا يقتصر على إنتاج واحد — عربي، أمريكي، وآسيوي 🗺️\n\n"
            f"👉 [اكتشف المحتوى]({url})"
        ),
        lambda url: (
            f"🎬 *محتوى مرئي لكل الأذواق*\n\n"
            f"من الأفلام الكلاسيكية إلى المسلسلات الحديثة — مكتبة *نت باشا* تضم خيارات متنوعة 🎦\n\n"
            f"👉 [افتح قسم الأفلام]({url})"
        ),
        lambda url: (
            f"📺 *مسلسلات تركية ومدبلجة*\n\n"
            f"المسلسلات التركية والمدبلجة للعربية جزء من محتوى قسم الأفلام والمسلسلات بـ *نت باشا* 🇹🇷\n\n"
            f"👉 [تصفح المسلسلات]({url})"
        ),
        lambda url: (
            f"🎭 *دراما وتشويق*\n\n"
            f"عشاق الدراما والتشويق يجدون في قسم الأفلام بـ *نت باشا* محتوى يناسب اهتمامهم 🔍\n\n"
            f"👉 [افتح قسم الأفلام]({url})"
        ),
        lambda url: (
            f"🎬 *أفلام عربية أصيلة*\n\n"
            f"الأفلام العربية من مصر والشام والخليج متوفرة في قسم الأفلام والمسلسلات بـ *نت باشا* 🌙\n\n"
            f"👉 [شاهد الأفلام العربية]({url})"
        ),
        lambda url: (
            f"🍿 *وقت مناسب للمشاهدة*\n\n"
            f"قسم الأفلام والمسلسلات في *نت باشا* متاح لتصفح ومشاهدة المحتوى في أي وقت يناسبك ⏰\n\n"
            f"👉 [تصفح قسم الأفلام]({url})"
        ),
        lambda url: (
            f"🎞️ *أفلام بجودة متعددة*\n\n"
            f"*نت باشا* يوفر خيارات جودة مناسبة لمختلف الاتصالات في قسم الأفلام والمسلسلات 📶\n\n"
            f"👉 [افتح قسم الأفلام]({url})"
        ),
    ],

    "anime": [
        lambda url: (
            f"🎌 *أنمي مترجم للعربية*\n\n"
            f"قسم الأنمي في *نت باشا* يضم مسلسلات وأفلام أنمي مترجمة إلى العربية من أنواع مختلفة 🌸\n\n"
            f"👉 [افتح قسم الأنمي]({url})"
        ),
        lambda url: (
            f"⚔️ *أنمي أكشن ومغامرات*\n\n"
            f"ستجد في قسم الأنمي بـ *نت باشا* أعمالاً من نوع الأكشن والمغامرة من الإنتاج الياباني 🗡️\n\n"
            f"👉 [تصفح أنمي الأكشن]({url})"
        ),
        lambda url: (
            f"💫 *أنمي خيال علمي وفانتازيا*\n\n"
            f"أعمال الخيال العلمي والفانتازيا في عالم الأنمي متوفرة في قسم الأنمي بـ *نت باشا* 🚀\n\n"
            f"👉 [اكتشف أنمي الفانتازيا]({url})"
        ),
        lambda url: (
            f"🎭 *أنمي دراما وشخصيات معقدة*\n\n"
            f"قسم الأنمي بـ *نت باشا* يضم أعمالاً درامية بقصص عميقة وشخصيات متطورة ✨\n\n"
            f"👉 [تصفح أنمي الدراما]({url})"
        ),
        lambda url: (
            f"😄 *أنمي كوميدي وخفيف*\n\n"
            f"الأنمي الكوميدي والخفيف بجانب أنواع أخرى متوفر في قسم الأنمي على *نت باشا* 😂\n\n"
            f"👉 [افتح قسم الأنمي]({url})"
        ),
        lambda url: (
            f"🏫 *أنمي مدرسي وشبابي*\n\n"
            f"أعمال الأنمي التي تدور في الوسط المدرسي والشبابي موجودة في قسم الأنمي بـ *نت باشا* 🎒\n\n"
            f"👉 [تصفح الأنمي المدرسي]({url})"
        ),
        lambda url: (
            f"🌺 *كلاسيكيات الأنمي*\n\n"
            f"الأعمال الكلاسيكية من عالم الأنمي التي تركت أثراً واضحاً موجودة في *نت باشا* 🎌\n\n"
            f"👉 [اكتشف الكلاسيكيات]({url})"
        ),
        lambda url: (
            f"🎬 *أفلام أنمي يابانية*\n\n"
            f"بجانب المسلسلات، قسم الأنمي في *نت باشا* يضم أفلام أنمي ذات جودة إنتاجية عالية 🎥\n\n"
            f"👉 [شاهد أفلام الأنمي]({url})"
        ),
        lambda url: (
            f"🧩 *أنمي لمختلف الأعمار*\n\n"
            f"قسم الأنمي بـ *نت باشا* يشمل أعمالاً تناسب أعماراً مختلفة وأذواقاً متعددة 🎯\n\n"
            f"👉 [تصفح قسم الأنمي]({url})"
        ),
        lambda url: (
            f"📖 *أنمي مقتبس من مانغا*\n\n"
            f"العديد من أعمال الأنمي المقتبسة من المانغا المشهورة متوفرة في قسم الأنمي بـ *نت باشا* 📚\n\n"
            f"👉 [افتح قسم الأنمي]({url})"
        ),
    ],

    "tv": [
        lambda url: (
            f"📺 *قنوات تلفزيونية مباشرة*\n\n"
            f"قسم القنوات في *نت باشا* يوفر بثاً مباشراً لعدد من القنوات العربية والعالمية 🔴\n\n"
            f"👉 [افتح قسم القنوات]({url})"
        ),
        lambda url: (
            f"🌍 *قنوات من دول متعددة*\n\n"
            f"ستجد في قسم القنوات بـ *نت باشا* بثاً مباشراً لقنوات من مختلف الدول والتخصصات 📡\n\n"
            f"👉 [تصفح القنوات]({url})"
        ),
        lambda url: (
            f"📰 *قنوات إخبارية مباشرة*\n\n"
            f"القنوات الإخبارية العربية والدولية متاحة في قسم القنوات المباشرة بـ *نت باشا* 🗞️\n\n"
            f"👉 [شاهد القنوات الإخبارية]({url})"
        ),
        lambda url: (
            f"🎉 *قنوات ترفيهية وعائلية*\n\n"
            f"قنوات الترفيه والبرامج العائلية جزء من قسم القنوات المباشرة على *نت باشا* 👨‍👩‍👧‍👦\n\n"
            f"👉 [افتح القنوات الترفيهية]({url})"
        ),
        lambda url: (
            f"🏟️ *قنوات رياضية مباشرة*\n\n"
            f"القنوات الرياضية المتخصصة في البث الحي متوفرة في قسم القنوات بـ *نت باشا* ⚽\n\n"
            f"👉 [شاهد القنوات الرياضية]({url})"
        ),
        lambda url: (
            f"🔴 *مشاهدة مباشرة بلا تأخير*\n\n"
            f"قسم القنوات في *نت باشا* مصمم لتوفير بث مباشر بجودة مقبولة واستقرار جيد 📶\n\n"
            f"👉 [افتح قسم القنوات]({url})"
        ),
        lambda url: (
            f"🌐 *قنوات دولية بلغات متعددة*\n\n"
            f"بعض القنوات الدولية بلغات مختلفة متاحة في قسم القنوات المباشرة بـ *نت باشا* 🗺️\n\n"
            f"👉 [تصفح القنوات الدولية]({url})"
        ),
        lambda url: (
            f"📺 *متابعة البرامج في وقتها*\n\n"
            f"البث المباشر للقنوات يتيح لك متابعة البرامج والأخبار في وقتها المحدد عبر *نت باشا* ⏱️\n\n"
            f"👉 [افتح القنوات المباشرة]({url})"
        ),
        lambda url: (
            f"🎬 *قنوات أفلام وسينما*\n\n"
            f"القنوات المتخصصة في عرض الأفلام متوفرة ضمن قسم القنوات المباشرة في *نت باشا* 🍿\n\n"
            f"👉 [شاهد قنوات الأفلام]({url})"
        ),
        lambda url: (
            f"📡 *قنوات مباشرة على مدار الساعة*\n\n"
            f"قسم القنوات في *نت باشا* متاح للمشاهدة في أي وقت خلال اليوم أو الليل 🌙\n\n"
            f"👉 [افتح قسم القنوات]({url})"
        ),
    ],

    "sports": [
        lambda url: (
            f"⚽ *أخبار رياضية متنوعة*\n\n"
            f"قسم الرياضة في *نت باشا* يغطي أخبار كرة القدم والرياضات الأخرى من مختلف الدوريات 🏆\n\n"
            f"👉 [افتح قسم الرياضة]({url})"
        ),
        lambda url: (
            f"🏆 *ترتيب الدوريات والنتائج*\n\n"
            f"ترتيب الدوريات الكبرى ونتائج المباريات متوفرة في قسم الرياضة بـ *نت باشا* 📊\n\n"
            f"👉 [تابع الدوريات]({url})"
        ),
        lambda url: (
            f"🎯 *أبرز أحداث عالم الرياضة*\n\n"
            f"قسم الرياضة في *نت باشا* يجمع أبرز ما يحدث في عالم الرياضة من أخبار وتقارير ⚡\n\n"
            f"👉 [اقرأ أخبار الرياضة]({url})"
        ),
        lambda url: (
            f"🏀 *رياضات متعددة في مكان واحد*\n\n"
            f"من كرة القدم إلى السلة والتنس — قسم الرياضة بـ *نت باشا* لا يقتصر على رياضة واحدة 🎾\n\n"
            f"👉 [تصفح قسم الرياضة]({url})"
        ),
        lambda url: (
            f"📋 *إحصائيات اللاعبين والفرق*\n\n"
            f"إحصائيات مفصلة عن الفرق واللاعبين الكبار جزء من محتوى قسم الرياضة بـ *نت باشا* 📈\n\n"
            f"👉 [اطلع على الإحصائيات]({url})"
        ),
        lambda url: (
            f"🌍 *بطولات عالمية وقارية*\n\n"
            f"أخبار البطولات الكبرى كدوري الأبطال وكأس العالم حاضرة في قسم الرياضة بـ *نت باشا* 🏅\n\n"
            f"👉 [تابع البطولات]({url})"
        ),
        lambda url: (
            f"⚽ *كرة القدم العربية والعالمية*\n\n"
            f"الدوريات العربية والعالمية الكبرى مغطاة في قسم الرياضة على *نت باشا* 🌙\n\n"
            f"👉 [افتح قسم الرياضة]({url})"
        ),
        lambda url: (
            f"🥊 *رياضات فردية وجماعية*\n\n"
            f"أخبار الملاكمة والفنون القتالية والرياضات الفردية موجودة في قسم الرياضة بـ *نت باشا* 🥋\n\n"
            f"👉 [تصفح قسم الرياضة]({url})"
        ),
        lambda url: (
            f"📅 *مواعيد المباريات القادمة*\n\n"
            f"جداول المباريات ومواعيدها متاحة في قسم الرياضة بـ *نت باشا* للتخطيط المسبق 🗓️\n\n"
            f"👉 [اطلع على الجدول]({url})"
        ),
        lambda url: (
            f"🏃 *الرياضة والمتابعة اليومية*\n\n"
            f"قسم الرياضة في *نت باشا* مصمم لمتابع الرياضة اليومية بأخبار موجزة ومحدثة 📰\n\n"
            f"👉 [افتح قسم الرياضة]({url})"
        ),
    ],

    "tech": [
        lambda url: (
            f"💻 *أخبار التقنية والتكنولوجيا*\n\n"
            f"قسم التقنية في *نت باشا* يغطي أخبار عالم التكنولوجيا من هواتف وأجهزة وتطبيقات 📱\n\n"
            f"👉 [افتح قسم التقنية]({url})"
        ),
        lambda url: (
            f"🤖 *ذكاء اصطناعي وتطورات تقنية*\n\n"
            f"مستجدات الذكاء الاصطناعي وتطبيقاته في الحياة اليومية جزء من محتوى قسم التقنية بـ *نت باشا* 🧠\n\n"
            f"👉 [اقرأ عن الذكاء الاصطناعي]({url})"
        ),
        lambda url: (
            f"📱 *مراجعات الهواتف والأجهزة*\n\n"
            f"مراجعات ومقارنات الهواتف الذكية والأجهزة الجديدة متوفرة في قسم التقنية بـ *نت باشا* 🔍\n\n"
            f"👉 [تصفح المراجعات]({url})"
        ),
        lambda url: (
            f"🔒 *الأمن الرقمي والخصوصية*\n\n"
            f"مقالات حول حماية البيانات والأمن الرقمي للمستخدمين جزء من قسم التقنية في *نت باشا* 🛡️\n\n"
            f"👉 [اقرأ عن الأمن الرقمي]({url})"
        ),
        lambda url: (
            f"🌐 *تطبيقات ومنصات رقمية*\n\n"
            f"أخبار التطبيقات الجديدة والمنصات الرقمية الناشئة متوفرة في قسم التقنية بـ *نت باشا* 💡\n\n"
            f"👉 [اكتشف أخبار التطبيقات]({url})"
        ),
        lambda url: (
            f"🚀 *ابتكارات تقنية حول العالم*\n\n"
            f"أبرز الابتكارات والاكتشافات في عالم التقنية مغطاة في قسم التقنية بـ *نت باشا* 🌍\n\n"
            f"👉 [افتح قسم التقنية]({url})"
        ),
        lambda url: (
            f"🖥️ *البرمجة وعالم المطورين*\n\n"
            f"محتوى يهم المطورين والمهتمين بالبرمجة متاح ضمن قسم التقنية في *نت باشا* 👨‍💻\n\n"
            f"👉 [تصفح محتوى التقنية]({url})"
        ),
        lambda url: (
            f"⚡ *سرعة الإنترنت والشبكات*\n\n"
            f"أخبار الجيل الخامس وتطور شبكات الإنترنت ضمن المحتوى التقني في *نت باشا* 📶\n\n"
            f"👉 [اقرأ أخبار الشبكات]({url})"
        ),
        lambda url: (
            f"🎮 *الألعاب الإلكترونية والتقنية*\n\n"
            f"أخبار الألعاب الإلكترونية وصناعة الجيمينج جزء من قسم التقنية في *نت باشا* 🕹️\n\n"
            f"👉 [اكتشف أخبار الألعاب]({url})"
        ),
        lambda url: (
            f"💻 *تقنية بالعربي*\n\n"
            f"قسم التقنية في *نت باشا* يقدم المحتوى التقني بأسلوب مبسط ومفهوم للقارئ العربي 📖\n\n"
            f"👉 [افتح قسم التقنية]({url})"
        ),
    ],

    "books": [
        lambda url: (
            f"📚 *كتب وروايات متنوعة*\n\n"
            f"قسم الكتب في *نت باشا* يضم روايات وكتب تطوير ذات وأدب عربي وعالمي 📖\n\n"
            f"👉 [افتح قسم الكتب]({url})"
        ),
        lambda url: (
            f"✍️ *الأدب العربي والعالمي*\n\n"
            f"أعمال أدبية من الكتّاب العرب والعالميين متوفرة في قسم الكتب بـ *نت باشا* 🌍\n\n"
            f"👉 [تصفح الأدب العربي]({url})"
        ),
        lambda url: (
            f"🧠 *كتب تطوير الذات*\n\n"
            f"كتب ومقالات التطوير الشخصي وتحسين الإنتاجية موجودة في قسم الكتب بـ *نت باشا* 💡\n\n"
            f"👉 [اكتشف كتب التطوير]({url})"
        ),
        lambda url: (
            f"🕵️ *روايات الغموض والإثارة*\n\n"
            f"الروايات البوليسية وقصص الغموض والإثارة جزء من مكتبة *نت باشا* للكتب 🔎\n\n"
            f"👉 [تصفح روايات الإثارة]({url})"
        ),
        lambda url: (
            f"🌌 *الخيال العلمي والفانتازيا*\n\n"
            f"روايات الخيال العلمي والفانتازيا متوفرة في قسم الكتب بـ *نت باشا* لمحبي هذا النوع 🚀\n\n"
            f"👉 [افتح قسم الكتب]({url})"
        ),
        lambda url: (
            f"📜 *الأدب الكلاسيكي والتراثي*\n\n"
            f"الأعمال الأدبية الكلاسيكية والتراثية العربية موجودة في قسم الكتب على *نت باشا* 🕌\n\n"
            f"👉 [اقرأ الأدب الكلاسيكي]({url})"
        ),
        lambda url: (
            f"💼 *كتب الأعمال والاقتصاد*\n\n"
            f"كتب الأعمال والريادة والاقتصاد جزء من محتوى قسم الكتب في *نت باشا* 📈\n\n"
            f"👉 [تصفح كتب الأعمال]({url})"
        ),
        lambda url: (
            f"🌹 *الشعر والنثر العربي*\n\n"
            f"مختارات شعرية ونثرية من التراث العربي والأدب المعاصر في قسم الكتب بـ *نت باشا* ✨\n\n"
            f"👉 [اقرأ الشعر والنثر]({url})"
        ),
        lambda url: (
            f"🧒 *كتب للناشئة والأطفال*\n\n"
            f"قسم الكتب في *نت باشا* يتضمن محتوى مناسباً للأطفال والناشئة أيضاً 📙\n\n"
            f"👉 [افتح قسم الكتب]({url})"
        ),
        lambda url: (
            f"📚 *مكتبة رقمية في جيبك*\n\n"
            f"قسم الكتب في *نت باشا* يتيح الوصول إلى محتوى أدبي ومعرفي متنوع من هاتفك 📲\n\n"
            f"👉 [تصفح المكتبة]({url})"
        ),
    ],
}

ALL_CATEGORIES = list(CATEGORIES.keys())


WELCOME_MSG = """\
👋 *أهلاً بك في نت باشا!*

*نت باشا* هو تطبيقك العربي الشامل الذي يجمع لك كل شيء في مكان واحد:

🎬 أفلام ومسلسلات عربية وعالمية
📺 قنوات مباشرة على مدار الساعة
⚽ أخبار رياضية ونتائج المباريات
🎌 أنمي مترجم للعربية
🎵 موسيقى وأغاني لكل الأذواق
🍲 وصفات طبخ من مختلف المطابخ
💊 مقالات صحة ولياقة بدنية
📚 كتب وروايات متنوعة
💻 أخبار التقنية والذكاء الاصطناعي
📱 محتوى من منصات التواصل الاجتماعي

ستصلك تنبيهات دورية عن محتوى التطبيق حسب وقت اليوم 🔔

نت باشا — كل ما تحتاجه في مكان واحد 👇\
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


def register_user(state: dict, chat_id: int):
    users = get_users(state)
    key = str(chat_id)
    if key not in users:
        users[key] = {
            "joined_at": datetime.datetime.utcnow().isoformat(),
            "msg_used": {},
            "slot_queues": {},   # per-slot shuffled queues for category rotation
            "slot_last": {},     # last category used per slot
        }
        logger.info(f"New user registered: {chat_id}")


def pick_category_for_slot(user_data: dict, slot_cats: list[str]) -> str:
    """
    Round-robin through the allowed categories for the current time slot,
    shuffled each cycle. Each slot has its own independent queue so rotations
    don't interfere with each other.
    """
    slot_key  = "|".join(sorted(slot_cats))   # stable key for this slot group
    queues    = user_data.setdefault("slot_queues", {})
    lasts     = user_data.setdefault("slot_last",   {})
    queue     = queues.get(slot_key, [])
    last_cat  = lasts.get(slot_key)

    if not queue:
        new_queue = slot_cats[:]
        random.shuffle(new_queue)
        if last_cat and new_queue[0] == last_cat:
            new_queue.append(new_queue.pop(0))
        queue = new_queue

    if last_cat and len(queue) > 1 and queue[0] == last_cat:
        for j in range(1, len(queue)):
            if queue[j] != last_cat:
                queue[0], queue[j] = queue[j], queue[0]
                break

    picked = queue.pop(0)
    queues[slot_key]   = queue
    lasts[slot_key]    = picked
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
    """
    Fired at exact scheduled times. The paired categories are passed via
    context.job.data so no runtime clock-check is needed.
    """
    slot_cats = context.job.data   # e.g. ["health", "food"]

    state = load_state()
    users = get_users(state)
    if not users:
        logger.info("No users to notify yet.")
        save_state(state)
        return

    now = datetime.datetime.utcnow()
    for chat_id_str, user_data in list(users.items()):
        joined_at = user_data.get("joined_at")
        if joined_at:
            try:
                age = (now - datetime.datetime.fromisoformat(joined_at)).total_seconds()
                if age < 3600:
                    logger.info(f"Skipping {chat_id_str} — joined {int(age)}s ago.")
                    continue
            except Exception:
                pass

        chat_id  = int(chat_id_str)
        category = pick_category_for_slot(user_data, slot_cats)
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
        # Send first notification after 1 hour using the first scheduled slot's categories
        first_cats = SCHEDULE[0][2]
        context.job_queue.run_once(
            _first_notification,
            when=3600,
            chat_id=chat_id,
            data=first_cats,
            name=f"first_{chat_id}",
        )
        logger.info(f"First notification for {chat_id} scheduled in 1 h.")


async def _first_notification(context: ContextTypes.DEFAULT_TYPE):
    """Send the very first notification for a new user using whatever slot_cats are passed."""
    chat_id   = context.job.chat_id
    slot_cats = context.job.data

    state     = load_state()
    users     = get_users(state)
    user_data = users.get(str(chat_id))
    if not user_data:
        return

    category = pick_category_for_slot(user_data, slot_cats)
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
        # Schedule one run_daily job per exact time in SCHEDULE (UTC converted).
        for syria_h, syria_m, cats in SCHEDULE:
            t = utc_time(syria_h, syria_m)
            application.job_queue.run_daily(
                send_notifications,
                time=t,
                data=cats,
                name=f"slot_{syria_h:02d}{syria_m:02d}",
            )
            logger.info(
                f"Scheduled [{', '.join(cats)}] at {syria_h:02d}:{syria_m:02d} Syria "
                f"({t.hour:02d}:{t.minute:02d} UTC)"
            )

    app.post_init = post_init

    logger.info("Bot is running...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message"],
    )


if __name__ == "__main__":
    main()
