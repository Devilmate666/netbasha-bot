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
# Each entry: (hour, minute, category)  — one category per slot.
SCHEDULE = [
    # Morning
    ( 6,  0, ["health"]),
    ( 9,  0, ["food"]),
    # Afternoon
    (12, 30, ["music"]),
    (14,  0, ["social"]),
    # Evening
    (17, 30, ["movies"]),
    (19,  0, ["anime"]),
    # Night
    (21,  0, ["tv"]),
    (23,  0, ["sports"]),
    # Late
    ( 0,  0, ["tech"]),
    ( 2,  0, ["books"]),
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

def get_current_slot_cats() -> list[str]:
    """
    Return the categories for the slot that SHOULD have fired most recently
    in Syrian time, so a new user gets contextually appropriate content.
    If it's before the first slot of the day, wrap to the last slot.
    """
    now_syria = syria_now()
    current_minutes = now_syria.hour * 60 + now_syria.minute

    best = None
    best_minutes = -1
    for h, m, cats in SCHEDULE:
        slot_minutes = slot_to_minutes(h, m)
        if slot_minutes <= current_minutes and slot_minutes > best_minutes:
            best = cats
            best_minutes = slot_minutes

    if best is None:
        # Before the first slot today — use the last slot from yesterday
        best = SCHEDULE[-1][2]

    return best


# ─── Notification messages — 10 per category ─────────────────────────────────
CATEGORY_MSGS: dict[str, list] = {

    "health": [
        lambda url: (
            f"☀️ الصبح بدأ — جسمك في انتظارك\n\n"
            f"عشر دقائق حركة بالصبح تفرق عن يوم كامل. دوّر على اللي يناسبك في *نت باشا* وابدأ 💪\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥗 شو أكلت اليوم؟\n\n"
            f"لو ما ضبطت وجباتك، في محتوى بـ *نت باشا* بيساعدك تعرف وين تبدأ — بدون تعقيد 🍎\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💧 آخر مرة شربت مي؟\n\n"
            f"ذكّر نفسك. وإذا بدك تحسّن روتينك اليومي، *نت باشا* فيه محتوى صحي عملي ✅\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🏋️ تمارين بدون جيم ولا معدات\n\n"
            f"في *نت باشا* محتوى للتمارين المنزلية — ابحث عن اللي يناسب مستواك وابدأ من غرفتك 🏠\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"😴 كيف كان نومك؟\n\n"
            f"النوم السيئ بأثر على كل شي. في *نت باشا* نصايح عملية لتحسين جودة نومك 🌙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🧘 التوتر بيراكم — وفي حلول\n\n"
            f"في *نت باشا* محتوى عن إدارة التوتر والاسترخاء — ابحث عن اللي يريحك 🌿\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌞 روتين الصبح بيبني يومك\n\n"
            f"مش لازم يكون معقد. في *نت باشا* أفكار بسيطة لبداية يوم أفضل ☀️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⚖️ الوزن مش الهدف الوحيد\n\n"
            f"الصحة أشمل من الميزان. في *نت باشا* محتوى عن التوازن الغذائي بعيداً عن الحميات القاسية 🍏\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🦷 صحتك بتبدأ من تفاصيل صغيرة\n\n"
            f"في *نت باشا* نصايح وقائية وصحية عامة — ابحث عن موضوع يهمك 🩺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💊 جسمك يستاهل اهتمام\n\n"
            f"مقالات صحية عملية وواضحة في انتظارك على *نت باشا* — ابدأ من اللي بتحتاجه اليوم 🌱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    "food": [
        lambda url: (
            f"🍳 شو ستطبخ اليوم؟\n\n"
            f"إذا ما عندك فكرة، *نت باشا* فيه وصفات سهلة وسريعة — ابحث عن اللي عندك بالمطبخ 👨‍🍳\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🧁 شي حلو لليوم؟\n\n"
            f"في *نت باشا* وصفات حلويات ومعجنات بخطوات واضحة — جرب شي جديد اليوم 🍮\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥗 وجبة خفيفة وسريعة؟\n\n"
            f"سلطات وأكلات سريعة في *نت باشا* — لما ما عندك وقت بس بدك شي لذيذ 🥙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌶️ طعم البيت ما بيعوضه شي\n\n"
            f"وصفات مطبخ الشام بتوابله الأصيلة موجودة على *نت باشا* — ابحث عن طبقك المفضل 🫙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍖 مشاوي ومقبلات على كيفك\n\n"
            f"في *نت باشا* وصفات المشاوي بتفاصيلها الكاملة — لتجهّز شي يستاهل 🔥\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🫖 مشروب دافئ وأنت مرتاح؟\n\n"
            f"وصفات مشروبات تقليدية وعصائر طازجة في *نت باشا* — ابحث عن اللي يناسب جوّك 🧃\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⏱️ عندك ربع ساعة؟ يكفي\n\n"
            f"في *نت باشا* وصفات سريعة وعملية للأيام المشغولة — ما تحتاج تتعب 👩‍🍳\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥦 أكل صحي ما لازم يكون بايخ\n\n"
            f"وصفات متوازنة بمكونات يومية بسيطة في *نت باشا* — ابحث عن شي يعجبك 🍱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥘 طبخ جديد كل أسبوع\n\n"
            f"أطباق رئيسية متنوعة من مطابخ مختلفة في *نت باشا* — جرب شي ما طبخته من قبل 🍽️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"☕ إفطار يستاهل الاستيقاظ\n\n"
            f"أفكار لوجبات إفطار بسيطة ومغذية في *نت باشا* — ابدأ يومك صح 🍳\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    "music": [
        lambda url: (
            f"🎵 وقت الظهر — وقت الموسيقى\n\n"
            f"في *نت باشا* ابحث عن الفنان أو النوع اللي بتحبه وانتقل لعالمه 🎶\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎧 شو بتسمع هالأيام؟\n\n"
            f"في *نت باشا* موسيقى من كل جيل وكل بلد — ابحث واكتشف شي جديد يناسب مزاجك 🎼\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎤 فنان ما سمعته منذ زمان؟\n\n"
            f"ابحث عنه في *نت باشا* — موسيقى عربية وعالمية من أجيال وأنواع مختلفة 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎹 كلاسيكيات ما بتشبع منها\n\n"
            f"في *نت باشا* الطرب العربي الأصيل وكلاسيكيات الفنانين الكبار — ابحث وارجع لها 🕊️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌿 موسيقى وأنت بتشتغل؟\n\n"
            f"الموسيقى الهادئة للتركيز والاسترخاء موجودة في *نت باشا* — ابحث عن النوع اللي يريحك 🎺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🪕 الموسيقى الشرقية لها نكهة تانية\n\n"
            f"في *نت باشا* آلات شرقية وإيقاعات أصيلة — ابحث واكتشف هالعالم 🎻\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎙️ راب، بوب، أو شي ثاني؟\n\n"
            f"الأنواع الحديثة كلها في *نت باشا* — ابحث عن الفنان أو الأغنية اللي ببالك 🥁\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎸 شو مزاجك هلق؟\n\n"
            f"الموسيقى الغربية والعالمية بأنواعها موجودة في *نت باشا* — ابحث ولاقي اللي يناسبك 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎵 اليوم في موضة شو؟\n\n"
            f"ابحث في *نت باشا* عن آخر الأغاني والألبومات — تصفح وشوف شو طلع جديد 🎶\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎼 موسيقى لكل وقت ومزاج\n\n"
            f"سواء شغل أو راحة أو سفر — ابحث في *نت باشا* عن اللي يلوّن وقتك 🎧\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    "social": [
        lambda url: (
            f"📱 شو الناس بتتكلم عنه هلق؟\n\n"
            f"في *نت باشا* روابط مباشرة لتيك توك وإنستغرام ويوتيوب — ابحث وتصفح من مكان واحد 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔍 تدور على حساب أو محتوى معين؟\n\n"
            f"في *نت باشا* ابحث واوصل لحساباتك المفضلة على المنصات مباشرة 🔗\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 ترند اليوم وين؟\n\n"
            f"في *نت باشا* تقدر تتنقل بين تيك توك وإنستغرام ويوتيوب بسهولة لتشوف شو يشتغل 📲\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎞️ بدك تتصفح؟ دور على المنصة اللي بدك\n\n"
            f"في *نت باشا* وصول مباشر للمنصات الكبرى — ابدأ من اللي بيهمك ▶️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"👀 شو شارك الناس اليوم؟\n\n"
            f"تيك توك وإنستغرام ويوتيوب — كل المنصات في متناولك من *نت باشا* 📡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📲 تصفح المنصات من مكان واحد\n\n"
            f"في *نت باشا* وصول مباشر لأكبر المنصات — ما تحتاج تنتقل بين التطبيقات 🔗\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌐 عربي وعالمي — كل شي موجود\n\n"
            f"في *نت باشا* تصفح المحتوى العربي والعالمي من منصاتك المفضلة بسهولة 📱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔴 شو يصير هلق على المنصات؟\n\n"
            f"في *نت باشا* ابحث واوصل لأي منصة تواصل تهمك — تيك توك، إنستغرام، يوتيوب 👁️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💬 بدك تشوف شو بيصير؟\n\n"
            f"من *نت باشا* تقدر تنتقل لأي منصة بسرعة وتتابع اللي بيهمك 📊\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📡 المنصات الكبرى في بوابة واحدة\n\n"
            f"ابحث في *نت باشا* عن الحساب أو المحتوى اللي بتحب، وانتقل له مباشرة 🌟\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    "movies": [
        lambda url: (
            f"🍿 شو بتحب تشوف الليلة؟\n\n"
            f"في *نت باشا* أفلام ومسلسلات عربية وعالمية — ابحث عن اللي ببالك وابدأ 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎭 دراما ولا أكشن؟\n\n"
            f"في *نت باشا* ابحث عن المسلسل أو الفيلم اللي بيناسب مزاجك الليلة 🎥\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📽️ مسلسل بتابعه؟ دور على الحلقة الجديدة\n\n"
            f"في *نت باشا* مسلسلات عربية وأجنبية — ابحث وكمّل من حيث وقفت 🎞️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 فيلم أجنبي هالمرة؟\n\n"
            f"في *نت باشا* إنتاجات من أمريكا وآسيا وأوروبا — ابحث عن شي ما شفته 🗺️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🇹🇷 مسلسل تركي مدبلج؟\n\n"
            f"في *نت باشا* ابحث عن مسلسلك التركي المفضل أو اكتشف واحد جديد 📺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎬 فيلم عربي أصيل الليلة\n\n"
            f"أفلام من مصر والشام والخليج في *نت باشا* — ابحث واشوف شو في عندك 🌙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔍 بتفكر شو تشوف؟\n\n"
            f"ابحث في *نت باشا* — كوميديا، تشويق، رومانسية — لاقي اللي بيناسب وقتك 🎦\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎞️ من الكلاسيكيات للحديث\n\n"
            f"في *نت باشا* مكتبة واسعة من الأفلام والمسلسلات — ابحث وابدأ مشاهدتك 🍿\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⏰ وقت المشاهدة — لا تضيّعه\n\n"
            f"في *نت باشا* أفلام ومسلسلات جاهزة — ابحث عن شي وابدأ هلق 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎭 اختار مزاجك الليلة\n\n"
            f"دراما، أكشن، كوميديا — في *نت باشا* ابحث عن النوع اللي بيناسب شعورك 🌙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    "anime": [
        lambda url: (
            f"🎌 وين وصلت بالأنمي؟\n\n"
            f"في *نت باشا* ابحث عن المسلسل اللي بتتابعه وكمّل من حيث وقفت 🌸\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"⚔️ بدك أكشن يشحن طاقتك؟\n\n"
            f"في *نت باشا* أنمي أكشن ومغامرات من الإنتاج الياباني — ابحث واختار 🗡️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🚀 خيال علمي أو فانتازيا؟\n\n"
            f"في *نت باشا* أعمال أنمي بعوالم خيالية كاملة — ابحث واكتشف عالم جديد 💫\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"✨ قصص عميقة وشخصيات ما تنسى\n\n"
            f"في *نت باشا* أنمي دراما بأعمق من اللي تتوقع — ابحث عن شي يأثر فيك 🎭\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"😄 بدك شي خفيف وكوميدي؟\n\n"
            f"في *نت باشا* أنمي كوميدي يخفف عنك — ابحث واضحك شوي 😂\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎌 كلاسيك الأنمي اللي ما بنسى\n\n"
            f"في *نت باشا* الأعمال الكلاسيكية اللي شكّلت جيل كامل — ابحث وارجع لها 🌺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎥 فيلم أنمي هالليلة؟\n\n"
            f"في *نت باشا* أفلام أنمي يابانية بجودة إنتاجية عالية — ابحث واشوف شو في 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📚 مقتبس من مانغا بتعرفها؟\n\n"
            f"في *نت باشا* أنمي مبني على مانغا مشهورة — ابحث وشوف النسخة المتحركة 🎌\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎒 أنمي مدرسي أو شبابي؟\n\n"
            f"في *نت باشا* أعمال تحكي عن الشباب والمدرسة والصداقة — ابحث واختار 🏫\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🧩 لكل ذوق أنمي يناسبه\n\n"
            f"في *نت باشا* ابحث عن النوع اللي بتحبه — أكشن، دراما، كوميديا، خيال علمي 🎯\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    "tv": [
        lambda url: (
            f"📺 شو عم يبث هلق؟\n\n"
            f"في *نت باشا* قنوات عربية وعالمية ببث مباشر — افتح وشوف شو يمشي 🔴\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📰 شو صار اليوم بالأخبار؟\n\n"
            f"القنوات الإخبارية العربية والدولية بثاً مباشراً في *نت باشا* — افتح وتابع 🗞️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔴 قنوات مباشرة — هلق وليس غداً\n\n"
            f"في *نت باشا* قنوات تبث الآن — افتح التطبيق وشوف اللي يهمك 📡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎉 برامج وترفيه عائلي مباشر\n\n"
            f"قنوات الترفيه والبرامج العائلية شغّالة دلوقتي في *نت باشا* — افتح وشاهد 👨‍👩‍👧‍👦\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🍿 قناة أفلام بثاً مباشراً؟\n\n"
            f"في *نت باشا* قنوات سينما وأفلام ببث مباشر — افتح وشوف شو عم يحكوا 🎬\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌍 قنوات من كل البلاد\n\n"
            f"في *نت باشا* بث مباشر لقنوات من دول مختلفة — افتح وتصفح 📺\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎙️ قناة وثائقية أو متخصصة؟\n\n"
            f"في *نت باشا* قنوات طبخ وسفر ووثائقيات ببث مباشر — افتح وشوف شو يهمك 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📡 الليل الطويل والقنوات مفتوحة\n\n"
            f"في *نت باشا* قنوات ببث مباشر على مدار الساعة — افتح وشوف شو يمشي هلق 🌙\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔴 ما تحتاج تبحث — افتح وشاهد\n\n"
            f"قنوات مباشرة شغّالة الآن في *نت باشا* — افتح التطبيق ودوّر على اللي يعجبك 📲\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📺 كل القنوات في مكان واحد\n\n"
            f"في *نت باشا* بث مباشر لقنوات متنوعة — افتح وتصفح بدون تنقل 🔗\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    "sports": [
        lambda url: (
            f"⚽ في مباريات هالليلة؟\n\n"
            f"في *نت باشا* تابع أخبار الرياضة ونتائج المباريات — افتح وشوف شو صار 🏆\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📊 كيف ترتيب الدوري هلق؟\n\n"
            f"في *نت باشا* ترتيب الدوريات الكبرى ونتائج اليوم — ابحث عن فريقك 🎯\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🏆 شو صار بالرياضة اليوم؟\n\n"
            f"في *نت باشا* أبرز أخبار عالم الرياضة — ابحث عن اللي يهمك ⚡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🎾 مش بس كرة القدم\n\n"
            f"في *نت باشا* رياضات متعددة — سلة، تنس، ملاكمة — ابحث عن رياضتك المفضلة 🏀\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📈 إحصائيات اللاعبين والفرق\n\n"
            f"في *نت باشا* أرقام وإحصائيات مفصلة — ابحث عن اللاعب أو الفريق اللي بتتابعه 📋\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🏅 دوري الأبطال وكأس العالم\n\n"
            f"أخبار البطولات الكبرى في *نت باشا* — ابحث وتابع مجريات البطولة اللي تهمك 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🌙 الليل وقت مباريات دوري الأبطال\n\n"
            f"في *نت باشا* ابحث عن نتيجة المباراة أو الملخص اللي فاتك ⚽\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🥊 الملاكمة والفنون القتالية\n\n"
            f"في *نت باشا* أخبار رياضات المواجهة والفردية — ابحث عن آخر المستجدات 🥋\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🗓️ شو عندنا قادمًا؟\n\n"
            f"في *نت باشا* تابع جدول المباريات القادمة — خطط مسبقاً لما بدك تشاهد 📅\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📰 متابع رياضي يومي؟\n\n"
            f"في *نت باشا* أخبار رياضية موجزة ومحدثة — ابحث وابقى على اطلاع 🏃\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    "tech": [
        lambda url: (
            f"💻 شو الجديد بعالم التقنية؟\n\n"
            f"في *نت باشا* أخبار التكنولوجيا من هواتف وأجهزة وتطبيقات — ابحث واعرف قبل غيرك 📱\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🤖 الذكاء الاصطناعي عم يتغير كل يوم\n\n"
            f"في *نت باشا* آخر مستجدات الذكاء الاصطناعي — ابحث وشوف وين وصل 🧠\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📱 بدك تشتري هاتف جديد؟\n\n"
            f"في *نت باشا* مراجعات ومقارنات الهواتف الجديدة — ابحث وقرر بناءً على معلومات 🔍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🛡️ بياناتك — إنت مسؤول عنها\n\n"
            f"في *نت باشا* مقالات عن الأمن الرقمي والخصوصية — ابحث وتعلم كيف تحمي نفسك 🔒\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"💡 تطبيق جديد ما سمعت فيه؟\n\n"
            f"في *نت باشا* أخبار التطبيقات والمنصات الرقمية الجديدة — ابحث واكتشف 🌐\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🚀 ابتكار تقني ما توقعته\n\n"
            f"في *نت باشا* أبرز الابتكارات التقنية من حول العالم — ابحث وانبهر 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"👨‍💻 مهتم بالبرمجة والتطوير؟\n\n"
            f"في *نت باشا* محتوى للمطورين والمهتمين بالكود — ابحث عن موضوعك 🖥️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📶 الجيل الخامس وشبكات الغد\n\n"
            f"في *نت باشا* أخبار تطور الإنترنت والشبكات — ابحث وشوف وين وصلنا ⚡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🕹️ الألعاب الإلكترونية صناعة ضخمة\n\n"
            f"في *نت باشا* أخبار الجيمينج وصناعة الألعاب — ابحث عن آخر الإصدارات 🎮\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📖 تقنية بالعربي — واضحة ومفهومة\n\n"
            f"في *نت باشا* محتوى تقني مبسط ومكتوب للقارئ العربي — ابحث وتعلم 💻\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
    ],

    "books": [
        lambda url: (
            f"📚 آخر مرة قرأت كتاب؟\n\n"
            f"في *نت باشا* روايات وكتب تطوير وأدب — ابحث عن شي يستحق وقتك 📖\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"✍️ كاتب عربي أعجبك يوماً؟\n\n"
            f"في *نت باشا* أدب عربي وعالمي — ابحث عن اسمه أو اكتشف كاتب جديد 🌍\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🧠 كتاب بيغير طريقة تفكيرك\n\n"
            f"في *نت باشا* كتب تطوير الذات والإنتاجية — ابحث واقرأ شي يفيدك 💡\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🔎 رواية بوليسية تشيل نومك؟\n\n"
            f"في *نت باشا* روايات غموض وإثارة — ابحث وابدأ رحلة لما تنام 🕵️\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🚀 عوالم خيالية تاخذك بعيد\n\n"
            f"في *نت باشا* روايات خيال علمي وفانتازيا — ابحث واكتشف عالم جديد 🌌\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"🕌 الأدب الكلاسيكي العربي ما شاخ\n\n"
            f"في *نت باشا* تراث أدبي عربي وكلاسيكيات — ابحث وارجع لجذورك 📜\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📈 كتب الأعمال والريادة\n\n"
            f"في *نت باشا* كتب تهم رواد الأعمال والمهتمين بالاقتصاد — ابحث عن اللي يفيدك 💼\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"✨ شعر أو نثر — لكل مزاج شي\n\n"
            f"في *نت باشا* مختارات شعرية ونثرية من التراث العربي والمعاصر — ابحث واقرأ 🌹\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📙 شي للأطفال والناشئة؟\n\n"
            f"في *نت باشا* محتوى مناسب للصغار أيضاً — ابحث عن شي يفيدهم 🧒\n\n"
            f"👉 [افتح نت باشا]({url})"
        ),
        lambda url: (
            f"📲 مكتبة في جيبك — مفتوحة دايماً\n\n"
            f"في *نت باشا* محتوى أدبي ومعرفي في أي وقت — ابحث واقرأ من هاتفك 📚\n\n"
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


def register_user(state: dict, chat_id: int):
    users = get_users(state)
    key = str(chat_id)
    if key not in users:
        now = datetime.datetime.utcnow()
        first_notify_after = (now + datetime.timedelta(hours=1)).isoformat()
        users[key] = {
            "joined_at": now.isoformat(),
            "first_notify_after": first_notify_after,  # never notify before this UTC time
            "msg_used": {},
            "slot_queues": {},   # per-slot shuffled queues for category rotation
            "slot_last": {},     # last category used per slot
        }
        logger.info(f"New user registered: {chat_id} — first notification after {first_notify_after} UTC")



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


# ─── Track which slots have fired this bot run, to avoid double-fires ─────────
_slots_fired_this_run: set[str] = set()


# ─── Job: send one notification to all registered users ──────────────────────

async def send_notifications(context: ContextTypes.DEFAULT_TYPE):
    """
    Fired at exact scheduled times. The paired categories are passed via
    context.job.data so no runtime clock-check is needed.

    Guards against double-firing within the same run (e.g. if APScheduler
    fires a past slot immediately on startup).
    """
    slot_cats = context.job.data   # e.g. ["health", "food"]
    slot_key  = "|".join(sorted(slot_cats)) + "@" + context.job.name

    # ── Double-fire guard ──────────────────────────────────────────────────────
    # APScheduler can immediately trigger a run_daily job if its scheduled
    # time has already passed today when the bot first starts.  We record
    # each (slot, utc-date) pair and skip the duplicate.
    fire_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    dedup_key = f"{slot_key}#{fire_date}"
    if dedup_key in _slots_fired_this_run:
        logger.info(f"Skipping duplicate fire for slot {context.job.name} on {fire_date}")
        return
    _slots_fired_this_run.add(dedup_key)
    # ──────────────────────────────────────────────────────────────────────────

    state = load_state()
    users = get_users(state)
    if not users:
        logger.info("No users to notify yet.")
        save_state(state)
        return

    now = datetime.datetime.utcnow()
    sent_count = 0
    for chat_id_str, user_data in list(users.items()):
        # ── 1-hour new-user grace period ─────────────────────────────────────
        # first_notify_after is stored in state so it survives bot restarts.
        # Fall back to joined_at+1h for older state entries that lack the field.
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
                    logger.info(
                        f"Skipping {chat_id_str} — grace period until "
                        f"{first_notify_after_raw} UTC (now {now.isoformat()})"
                    )
                    continue
            except Exception:
                pass
        # ─────────────────────────────────────────────────────────────────────

        chat_id = int(chat_id_str)
        category = slot_cats[0]  # one category per slot
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

    logger.info(f"Slot {context.job.name} done — notified {sent_count}/{len(users)} users.")
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
        # The user's first_notify_after is stored in state (set by register_user).
        # Regular scheduled slots skip this user until that timestamp passes,
        # so no in-memory job is needed — this survives bot restarts automatically.
        logger.info(
            f"New user {chat_id} registered — regular notifications start in 1 hour."
        )



# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    async def post_init(application: Application):
        now_utc = datetime.datetime.utcnow()
        now_syria = syria_now()
        logger.info(
            f"Bot starting — UTC: {now_utc.strftime('%H:%M')}, "
            f"Syria: {now_syria.strftime('%H:%M')}"
        )

        # Schedule one run_daily job per exact time in SCHEDULE (converted to UTC).
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
