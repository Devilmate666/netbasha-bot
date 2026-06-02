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
# Each entry: (hour, minute, category)  — one category per slot.
SCHEDULE = [
    ( 6,  0, "health"),
    ( 9,  0, "food"),
    (12, 30, "music"),
    (14,  0, "social"),
    (17, 30, "movies"),
    (19,  0, "anime"),
    (21,  0, "tv"),
    (23,  0, "sports"),
    ( 0,  0, "tech"),
    ( 2,  0, "books"),
]

SYRIA_UTC_OFFSET = 3  # UTC+3

def syria_now() -> datetime.datetime:
    """Return the current time in Syrian timezone (UTC+3)."""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=SYRIA_UTC_OFFSET)

def utc_time(syria_hour: int, syria_minute: int) -> datetime.time:
    """Convert a Syria-local (UTC+3) time to UTC datetime.time for job scheduling."""
    total = syria_hour * 60 + syria_minute - (SYRIA_UTC_OFFSET * 60)
    total %= 1440
    return datetime.time(total // 60, total % 60)

def slot_to_minutes(syria_hour: int, syria_minute: int) -> int:
    """Convert Syria time to minutes-since-midnight for comparison."""
    return syria_hour * 60 + syria_minute

def get_slot_datetime(syria_hour: int, syria_minute: int, reference: datetime.datetime) -> datetime.datetime:
    """
    Get the datetime for a specific Syria-time slot on the same day as reference.
    Handles midnight wrap (00:00 and 02:00 are next day in UTC but same Syria day).
    """
    syria_ref = syria_now() if reference is None else reference
    slot = syria_ref.replace(hour=syria_hour, minute=syria_minute, second=0, microsecond=0)
    
    # If slot time has passed today, return None (needs next day)
    if slot < syria_ref:
        return None
    
    # Convert to UTC for storage/comparison
    utc_slot = slot - datetime.timedelta(hours=SYRIA_UTC_OFFSET)
    return utc_slot

# ─── Notification messages — 10 per category ─────────────────────────────────
CATEGORY_MSGS: dict[str, list] = {
    "health": [
        lambda url: (
            f"💊 *الصحة أولاً*\n\n"
            f"عشر دقايق حركة بالصبح بتفرق عن يوم كامل. دوّر على اللي بيناسبك في *نت باشا* وابدأ 💪\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥗 *غذاء صحي*\n\n"
            f"لو ما ضبطت وجباتك، في محتوى بـ *نت باشا* بيساعدك تعرف وين تبدأ — بدون تعقيد 🍎\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💧 *شرب الماء*\n\n"
            f"آخر مرة شربت مي؟ ذكّر نفسك. وإذا بدك تحسّن روتينك اليومي، *نت باشا* فيه محتوى صحي عملي ✅\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🏋️ *تمارين منزلية*\n\n"
            f"تمارين بدون جيم ولا معدات في *نت باشا* — ابحث عن اللي يناسب مستواك وابدأ من غرفتك 🏠\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"😴 *جودة النوم*\n\n"
            f"كيف كان نومك؟ النوم السيئ بأثر على كل شي. في *نت باشا* نصايح عملية لتحسين جودة نومك 🌙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🧘 *التوتر والاسترخاء*\n\n"
            f"التوتر بيتراكم — وفي حلول. في *نت باشا* محتوى عن إدارة التوتر والاسترخاء 🌿\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌞 *روتين الصباح*\n\n"
            f"روتين الصبح بيبني يومك. مولازم يكون معقد. في *نت باشا* أفكار بسيطة لبداية يوم أفضل ☀️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⚖️ *التوازن الغذائي*\n\n"
            f"الوزن مش الهدف الوحيد. الصحة أشمل من الميزان. في *نت باشا* محتوى عن التوازن الغذائي 🍏\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🦷 *صحة الوقاية*\n\n"
            f"صحتك بتبدأ من تفاصيل صغيرة. في *نت باشا* نصايح وقائية وصحية عامة 🩺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💊 *العناية بالجسم*\n\n"
            f"جسمك يستاهل اهتمام. مقالات صحية عملية وواضحة في انتظارك على *نت باشا* 🌱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
    "food": [
        lambda url: (
            f"🍳 *طبخ اليوم*\n\n"
            f"شو رح تطبخ اليوم؟ إذا ما عندك فكرة، *نت باشا* فيه وصفات سهلة وسريعة 👨‍🍳\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🧁 *حلويات ومعجنات*\n\n"
            f"شي حلو لليوم؟ في *نت باشا* وصفات حلويات ومعجنات بخطوات واضحة — جرب شي جديد اليوم 🍮\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥗 *وجبات سريعة*\n\n"
            f"وجبة خفيفة وسريعة؟ سلطات وأكلات سريعة في *نت باشا* — إذا ما عندك وقت بس بدك شي لذيذ 🥙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌶️ *مطبخ شامي*\n\n"
            f"طعم البيت ما بيعوضه شي. وصفات مطبخ الشام بتوابله الأصيلة موجودة على *نت باشا* 🫙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍖 *مشاوي ومقبلات*\n\n"
            f"مشاوي ومقبلات على كيفك. في *نت باشا* وصفات المشاوي بتفاصيلها الكاملة 🔥\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🫖 *مشروبات تقليدية*\n\n"
            f"مشروب طيب وأنت مرتاح؟ وصفات مشروبات تقليدية وعصائر طازجة في *نت باشا* 🧃\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⏱️ *طبخ سريع*\n\n"
            f"عندك ربع ساعة؟ وقتك بيكفي. في *نت باشا* وصفات سريعة وعملية للأيام المزدحمة 👩‍🍳\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥦 *أكل صحي*\n\n"
            f"أكل صحي ما لازم يكون ممل. وصفات متوازنة بمكونات يومية بسيطة في *نت باشا* 🍱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥘 *أطباق رئيسية*\n\n"
            f"طبخ جديد كل أسبوع. أطباق رئيسية متنوعة من مطابخ مختلفة في *نت باشا* 🍽️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"☕ *فطور الصباح*\n\n"
            f"فطور بيستاهل تصحى عشانه. أفكار لوجبات إفطار بسيطة ومغذية في *نت باشا* 🍳\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
    "music": [
        lambda url: (
            f"🎵 *وقت الموسيقى*\n\n"
            f"وقت الظهر — وقت الموسيقى. في *نت باشا* ابحث عن الفنان أو النوع الموسيقي اللي بتحبه 🎶\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎧 *مكتشفات موسيقية*\n\n"
            f"شو بتسمع هالأيام؟ في *نت باشا* موسيقى من كل جيل وكل بلد 🎼\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎤 *فنانين قدامى*\n\n"
            f"فنان ما سمعته من زمان؟ ابحث عنه في *نت باشا* — موسيقى عربية وعالمية من أجيال مختلفة 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎹 *كلاسيكيات الطرب*\n\n"
            f"كلاسيكيات ما بتشبع منها. في *نت باشا* الطرب العربي الأصيل وكلاسيكيات الفنانين الكبار 🕊️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌿 *موسيقى للتركيز*\n\n"
            f"موسيقى وأنت بتشتغل؟ الموسيقى الهادئة للتركيز والاسترخاء موجودة في *نت باشا* 🎺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🪕 *موسيقى شرقية*\n\n"
            f"الموسيقى الشرقية لها نكهة تانية. في *نت باشا* آلات شرقية وإيقاعات أصيلة 🎻\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎙️ *أنواع موسيقية حديثة*\n\n"
            f"راب، بوب، روك أو شي ثاني؟ الأنواع الموسيقية الحديثة كلها في *نت باشا* 🥁\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎸 *موسيقى عالمية*\n\n"
            f"شو مزاجك هلق؟ الموسيقى الغربية والعالمية بأنواعها موجودة في *نت باشا* 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎵 *التريندات الموسيقية*\n\n"
            f"شو التريندات بالميوزك اليوم؟ ابحث في *نت باشا* عن آخر الأغاني والألبومات 🎶\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎼 *موسيقى لكل وقت*\n\n"
            f"موسيقى لكل وقت ومزاج. سواء شغل أو راحة أو سفر — ابحث في *نت باشا* عن اللي يلوّن وقتك 🎧\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
    "social": [
        lambda url: (
            f"📱 *وسائل التواصل*\n\n"
            f"عن شو عم تحكي الناس هلق؟ في *نت باشا* روابط مباشرة لتيك توك وإنستغرام ويوتيوب 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔍 *صناع المحتوى*\n\n"
            f"حسابات صناع محتوى أو برامج معينة تهمك؟ في *نت باشا* ابحث واوصل لحساباتك المفضلة 🔗\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 *ترند اليوم*\n\n"
            f"ترند اليوم وين؟ في *نت باشا* تقدر تتنقل بين تيك توك وإنستغرام ويوتيوب بسهولة 📲\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎞️ *تصفح المنصات*\n\n"
            f"بدك تتصفح الميديا؟ في *نت باشا* وصول مباشر للمنصات الكبرى — ابدأ من اللي بيهمك ▶️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"👀 *المحتوى الرائج*\n\n"
            f"شو شارك الناس اليوم؟ كل المنصات في متناولك بمطرح واحد على *نت باشا* 📡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📲 *بوابة المنصات*\n\n"
            f"تصفح المنصات من مكان واحد. في *نت باشا* وصول مباشر لأكبر المنصات 🔗\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌐 *محتوى عربي وعالمي*\n\n"
            f"عربي وعالمي — كل شي موجود. في *نت باشا* تصفح المحتوى العربي والعالمي بسهولة 📱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔴 *أخبار المنصات*\n\n"
            f"شو عم يصير هلق على المنصات العالمية؟ في *نت باشا* ابحث واوصل لأي منصة تهمك 👁️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💬 *متابعة أول بأول*\n\n"
            f"بدك تضل متابع أول بأول؟ من *نت باشا* تقدر تنتقل لأي منصة بسرعة 📊\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📡 *منصات موحدة*\n\n"
            f"المنصات الكبرى في بوابة واحدة. ابحث في *نت باشا* عن الحساب أو المحتوى اللي بتحب 🌟\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
    "movies": [
        lambda url: (
            f"🍿 *ليلة مشاهدة*\n\n"
            f"شو بتحب تشوف الليلة؟ في *نت باشا* أفلام ومسلسلات عربية وعالمية 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎭 *دراما أو أكشن*\n\n"
            f"دراما ولا أكشن؟ في *نت باشا* ابحث عن المسلسل أو الفيلم اللي بيناسب مزاجك 🎥\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📽️ *متابعة مسلسل*\n\n"
            f"مسلسل بتابعه ولا بدك تفوّت ولا حلقة؟ في *نت باشا* مسلسلات عربية وأجنبية 🎞️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 *إنتاجات عالمية*\n\n"
            f"فيلم أجنبي هالمرة ولا دراما كورية؟ في *نت باشا* إنتاجات من كل العالم 🗺️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🇹🇷 *مسلسلات تركية*\n\n"
            f"مسلسل تركي مدبلج؟ في *نت باشا* ابحث عن مسلسلك التركي المفضل 📺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎬 *سينما عربية*\n\n"
            f"فيلم عربي أصيل الليلة. أفلام من مصر والشام والخليج في *نت باشا* 🌙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔍 *اختيار الفيلم*\n\n"
            f"عم تفكر شو بدك تشوف؟ ابحث في *نت باشا* — كوميديا، تشويق، رومانسية 🎦\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎞️ *كلاسيكيات وحديث*\n\n"
            f"من الكلاسيكيات للحديث. في *نت باشا* مكتبة واسعة من الأفلام والمسلسلات 🍿\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⏰ *وقت المشاهدة*\n\n"
            f"وقت المشاهدة — لا تضيّعه. في *نت باشا* أفلام ومسلسلات يومياً بانتظارك 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎭 *اختيار المزاج*\n\n"
            f"اختار موودك الليلة. دراما، أكشن، كوميديا — في *نت باشا* ابحث عن اللي بيناسبك 🌙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
    "anime": [
        lambda url: (
            f"🎌 *متابعة أنمي*\n\n"
            f"وين وصلت بالأنمي؟ في *نت باشا* ابحث عن الأنمي اللي بتتابعه 🌸\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⚔️ *أنمي أكشن*\n\n"
            f"بدك أكشن من أنميات الشونين؟ في *نت باشا* أنميات أكشن ومغامرات يابانية 🗡️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🚀 *خيال علمي وفانتازيا*\n\n"
            f"خيال علمي أو فانتازيا؟ في *نت باشا* أعمال أنمي بعوالم مختلفة 💫\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"✨ *قصص عميقة*\n\n"
            f"قصص عميقة للشباب وشخصيات ما بتنتسى. في *نت باشا* أنميات الدراما 🎭\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"😄 *أنمي كوميدي*\n\n"
            f"بدك شي خفيف وكوميدي؟ في *نت باشا* أنميات كوميديا تخفف عنك 😂\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎌 *كلاسيكيات الأنمي*\n\n"
            f"كلاسيكات الأنمي اللي ما بتنتسى. في *نت باشا* الأعمال الكلاسيكية من التمانينات 🌺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎥 *أفلام أنمي*\n\n"
            f"فيلم أنمي هالليلة؟ في *نت باشا* أفلام أنمي يابانية بجودة عالية 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📚 *مقتبس من مانغا*\n\n"
            f"مقتبس من مانغا بتعرفها؟ في *نت باشا* أنمي مبني على مانغا مشهورة 🎌\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎒 *أنمي مدرسي*\n\n"
            f"أنمي مدرسي أو شبابي؟ في *نت باشا* أعمال عن الشباب والمدرسة 🏫\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🧩 *أنمي لكل ذوق*\n\n"
            f"لكل ذوق أنمي يناسبه. في *نت باشا* ابحث عن النوع اللي بتحبه 🎯\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
    "tv": [
        lambda url: (
            f"📺 *بث مباشر*\n\n"
            f"شو عم ينبث هلق؟ في *نت باشا* قنوات عربية وعالمية ببث مباشر 🔴\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📰 *قنوات إخبارية*\n\n"
            f"شو صار اليوم بالأخبار؟ القنوات الإخبارية ببث مباشر في *نت باشا* 🗞️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔴 *بث حصري*\n\n"
            f"قنوات مباشرة — بشكل حصري. في *نت باشا* قنوات تبث الآن 📡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎉 *برامج ترفيهية*\n\n"
            f"برامج وترفيه عائلي مباشر. قنوات الترفيه شغّالة الآن في *نت باشا* 👨‍👩‍👧‍👦\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍿 *قنوات أفلام*\n\n"
            f"قناة أفلام ببث مباشر؟ في *نت باشا* قنوات سينما وأفلام 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 *قنوات عالمية*\n\n"
            f"قنوات من كل البلاد. في *نت باشا* بث مباشر لقنوات من دول مختلفة 📺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎙️ *قنوات متخصصة*\n\n"
            f"قناة وثائقية أو متخصصة؟ في *نت باشا* قنوات طبخ وسفر ووثائقيات 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📡 *ليلة تلفزيونية*\n\n"
            f"الليل الطويل والقنوات مفتوحة. في *نت باشا* قنوات تبث على مدار الساعة 🌙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔴 *تلفزيون بجيبك*\n\n"
            f"ما تحتاج تبحث — شاشة التلفزيون بجيبك. قنوات مباشرة في *نت باشا* 📲\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📺 *كل القنوات بمكان واحد*\n\n"
            f"كل القنوات في مكان واحد. في *نت باشا* بث مباشر لمجموعة متنوعة 🔗\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
    "sports": [
        lambda url: (
            f"⚽ *المباريات الليلة*\n\n"
            f"في مباريات هالليلة؟ في *نت باشا* تابع أخبار الرياضة ونتائج المباريات 🏆\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📊 *ترتيب الدوري*\n\n"
            f"كيف ترتيب الدوري هلق؟ في *نت باشا* ترتيب الدوريات الكبرى 🎯\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🏆 *أخبار الرياضة*\n\n"
            f"شو صار بالرياضة اليوم؟ في *نت باشا* أبرز أخبار عالم الرياضة ⚡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎾 *رياضات متعددة*\n\n"
            f"مش بس كرة القدم. في *نت باشا* رياضات متعددة — سلة، تنس، ملاكمة 🏀\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📈 *إحصائيات وبيانات*\n\n"
            f"إحصائيات اللاعبين والفرق. في *نت باشا* أرقام وإحصائيات مفصلة 📋\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🏅 *بطولات كبرى*\n\n"
            f"دوري الأبطال وكأس العالم. أخبار البطولات الكبرى في *نت باشا* 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌙 *مواسم رياضية*\n\n"
            f"رياضة بتحبها؟ في *نت باشا* ابحث عن نتيجة المباراة أو الملخص ⚽\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥊 *فنون قتالية*\n\n"
            f"الملاكمة والفنون القتالية. في *نت باشا* أخبار رياضات المواجهة 🥋\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🗓️ *جدول المباريات*\n\n"
            f"شو الجديد بعالم الرياضة؟ في *نت باشا* تابع جدول المباريات القادمة 📅\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📰 *متابع رياضي*\n\n"
            f"متابع رياضي يومي؟ في *نت باشا* أخبار رياضية موجزة ومحدثة 🏃\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
    "tech": [
        lambda url: (
            f"💻 *أخبار التقنية*\n\n"
            f"شو الجديد بعالم التقنية؟ في *نت باشا* أخبار التكنولوجيا والهواتف 📱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🤖 *الذكاء الاصطناعي*\n\n"
            f"الذكاء الاصطناعي عم يتغير كل يوم. في *نت باشا* آخر مستجدات الذكاء الاصطناعي 🧠\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📱 *مراجعات الهواتف*\n\n"
            f"بدك تشتري هاتف جديد؟ في *نت باشا* مراجعات ومقارنات الهواتف الجديدة 🔍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🛡️ *الأمن السيبراني*\n\n"
            f"بياناتك — إنت مسؤول عنها. في *نت باشا* مقالات عن الأمن والخصوصية 🔒\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💡 *تطبيقات جديدة*\n\n"
            f"تطبيق جديد ما سمعت فيه؟ في *نت باشا* أخبار التطبيقات والمنصات 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🚀 *ابتكارات تقنية*\n\n"
            f"ابتكار تقني ما توقعته. في *نت باشا* أبرز الابتكارات حول العالم 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"👨‍💻 *برمجة وتطوير*\n\n"
            f"مهتم بالبرمجة والتطوير؟ في *نت باشا* محتوى للمطورين 🖥️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📶 *شبكات الجيل الخامس*\n\n"
            f"الجيل الخامس وشبكات الغد. في *نت باشا* أخبار تطور الإنترنت ⚡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🕹️ *ألعاب إلكترونية*\n\n"
            f"الألعاب الإلكترونية صناعة ضخمة. في *نت باشا* أخبار الجيمينج 🎮\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📖 *تقنية بالعربي*\n\n"
            f"تقنية بالعربي — واضحة ومفهومة. في *نت باشا* محتوى تقني مبسط 💻\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],
    "books": [
        lambda url: (
            f"📚 *وقت القراءة*\n\n"
            f"آخر مرة قرأت كتاب؟ في *نت باشا* روايات وكتب تطوير وأدب 📖\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"✍️ *أدب عربي*\n\n"
            f"كاتب عربي أعجبك يوماً؟ في *نت باشا* أدب عربي وعالمي 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🧠 *تطوير الذات*\n\n"
            f"كتاب بيغير طريقة تفكيرك. في *نت باشا* كتب تطوير الذات والإنتاجية 💡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔎 *روايات بوليسية*\n\n"
            f"رواية بوليسية تشد انتباهك؟ في *نت باشا* روايات غموض وإثارة 🕵️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🚀 *خيال علمي*\n\n"
            f"عوالم خيالية تاخذك بعيد. في *نت باشا* روايات خيال علمي وفانتازيا 🌌\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🕌 *أدب كلاسيكي*\n\n"
            f"الأدب الكلاسيكي العربي ما شاخ. في *نت باشا* تراث أدبي عربي 📜\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📈 *كتب الأعمال*\n\n"
            f"كتب الأعمال والريادة. في *نت باشا* كتب تهم رواد الأعمال 💼\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"✨ *شعر ونثر*\n\n"
            f"شعر أو نثر — لكل مزاج شي. في *نت باشا* مختارات شعرية ونثرية 🌹\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📙 *كتب للأطفال*\n\n"
            f"شي للأطفال والناشئة؟ في *نت باشا* محتوى مناسب للصغار 🧒\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📲 *مكتبة بجيبك*\n\n"
            f"مكتبة في جيبك — مفتوحة دايماً. في *نت باشا* محتوى أدبي ومعرفي 📚\n\n"
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
    """Track which slots have been sent today. Format: {'2026-05-30': {'06:00': True, '09:00': True}}"""
    return state.setdefault("slots_fired", {})


def mark_slot_fired(state: dict, slot_key: str):
    """Mark a specific slot as sent for today."""
    today = syria_now().strftime("%Y-%m-%d")
    slots_fired = get_slots_fired(state)
    if today not in slots_fired:
        slots_fired[today] = {}
    slots_fired[today][slot_key] = True
    save_state(state)


def is_slot_fired_today(state: dict, slot_key: str) -> bool:
    """Check if a slot has already been sent today."""
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
    """Pick a message variant for the category (no repeats until all used)."""
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
    """
    Fired at exact scheduled times. The category is passed via context.job.data.
    Uses persistent tracking to ensure each slot fires exactly once per day.
    """
    category = context.job.data  # Single category string
    slot_key = f"{category}"     # e.g., "health"
    
    # Load current state
    state = load_state()
    
    # ── Check if this slot already fired today ──────────────────────────────────
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
        # ── 1-hour new-user grace period ─────────────────────────────────────
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
    
    # ── Mark this slot as fired for today ──────────────────────────────────────
    if sent_count > 0 or users:
        # Even if no users got messages (all in grace period), still mark as fired
        mark_slot_fired(state, slot_key)
        logger.info(f"Slot [{category}] marked as fired for today — notified {sent_count}/{len(users)} users")
    else:
        logger.info(f"Slot [{category}] had no eligible users (all in grace period)")
    
    save_state(state)


# ─── Catch-up function for missed slots on restart ───────────────────────────

async def catch_up_missed_slots(application: Application):
    """
    On bot startup, check if any scheduled slots for today have already passed
    but haven't been marked as fired. Send them immediately.
    """
    state = load_state()
    now_syria = syria_now()
    today_str = now_syria.strftime("%Y-%m-%d")
    
    logger.info(f"Checking for missed slots on {today_str} at {now_syria.strftime('%H:%M')} Syria time")
    
    missed_slots = []
    
    for syria_h, syria_m, category in SCHEDULE:
        slot_key = category
        
        # Check if already fired today
        if is_slot_fired_today(state, slot_key):
            logger.info(f"Slot [{category}] already fired today — skipping catch-up")
            continue
        
        # Create the datetime for this slot today in Syria time
        slot_syria = now_syria.replace(hour=syria_h, minute=syria_m, second=0, microsecond=0)
        
        # Handle midnight wrap (00:00 and 02:00 are technically next calendar day in UTC)
        # But in Syria time, they're still the same day
        if syria_h < 6 and now_syria.hour < 6:
            # Early morning slots (00:00, 02:00) - still same Syria day
            pass
        elif syria_h < 6 and now_syria.hour >= 6:
            # We're past 6 AM, the early morning slots already passed
            slot_syria = slot_syria  # Keep as is
        
        # If this slot time has already passed today
        if slot_syria < now_syria:
            logger.warning(f"Slot [{category}] scheduled at {syria_h:02d}:{syria_m:02d} has PASSED — will fire immediately")
            missed_slots.append((category, slot_syria))
    
    # Fire missed slots immediately (in order)
    for category, scheduled_time in missed_slots:
        logger.info(f"Catching up missed slot: [{category}] (was scheduled at {scheduled_time.strftime('%H:%M')} Syria time)")
        
        # Create a fake context with just the category
        # We need to manually call send_notifications with the category
        state = load_state()  # Reload to get latest
        if not is_slot_fired_today(state, category):
            users = get_users(state)
            now = datetime.datetime.utcnow()
            sent_count = 0
            
            for chat_id_str, user_data in list(users.items()):
                # Check grace period
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
            
            # Mark as fired
            if sent_count > 0 or users:
                mark_slot_fired(state, category)
                logger.info(f"Catch-up completed for [{category}] — notified {sent_count} users")
        
        await asyncio.sleep(2)  # Small delay between catch-up messages
    
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
    """Check today's schedule status."""
    state = load_state()
    now_syria = syria_now()
    today_str = now_syria.strftime("%Y-%m-%d")
    
    status_lines = [f"📅 *Today: {today_str}*", f"🕐 *Current Syria time: {now_syria.strftime('%H:%M')}*", ""]
    
    for syria_h, syria_m, category in SCHEDULE:
        slot_key = category
        fired = is_slot_fired_today(state, slot_key)
        slot_time = f"{syria_h:02d}:{syria_m:02d}"
        
        # Determine if slot is pending, done, or missed
        slot_syria = now_syria.replace(hour=syria_h, minute=syria_m, second=0, microsecond=0)
        
        if fired:
            status = "✅ *DONE*"
        elif slot_syria < now_syria:
            status = "⏰ *MISSED* (will catch up)"
        else:
            status = "⏳ *PENDING*"
        
        emoji = CATEGORIES[category]["emoji"]
        status_lines.append(f"{emoji} {slot_time} {category}: {status}")
    
    await update.message.reply_text(
        "\n".join(status_lines),
        parse_mode="Markdown"
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))  # New status command
    
    async def post_init(application: Application):
        now_utc = datetime.datetime.utcnow()
        now_syria = syria_now()
        logger.info(f"Bot starting — UTC: {now_utc.strftime('%H:%M')}, Syria: {now_syria.strftime('%H:%M')}")
        
        # ── FIRST: Catch up any missed slots from today ──────────────────────────
        await catch_up_missed_slots(application)
        
        # ── SECOND: Schedule all future slots for today and beyond ───────────────
        for syria_h, syria_m, category in SCHEDULE:
            t = utc_time(syria_h, syria_m)
            
            # Schedule the job
            application.job_queue.run_daily(
                send_notifications,
                time=t,
                data=category,  # Pass single category
                name=f"slot_{category}_{syria_h:02d}{syria_m:02d}",
            )
            logger.info(f"Scheduled [{category}] at {syria_h:02d}:{syria_m:02d} Syria ({t.hour:02d}:{t.minute:02d} UTC)")
        
        # ── THIRD: Clean up old slot_fired entries (keep only last 7 days) ───────
        state = load_state()
        slots_fired = state.get("slots_fired", {})
        if slots_fired:
            # Keep only last 7 days
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
