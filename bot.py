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
#          4=غوودي  5=طبخات  6=أكل صحي  7=يمي  8=أطيب أكلة
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
        lambda: (
            "💊 *مقالات طبية موثوقة*\n\n"
            "سؤال طبي يراودك؟ موقع *الطبي* يضم آلاف المقالات المكتوبة من متخصصين — "
            "من أعراض الأمراض إلى طرق الوقاية والعلاج 🩺",
            site_url("health", 0),
            "🩺 اكتشف المقالات الطبية"
        ),
        lambda: (
            "🌍 *منظمة الصحة العالمية*\n\n"
            "المعلومة الصحية الصحيحة تبدأ من مصدرها — "
            "تقارير وتوصيات منظمة الصحة العالمية (WHO) متاحة بالعربي مباشرةً 🌐",
            site_url("health", 1),
            "🌐 تصفّح موقع WHO"
        ),
        lambda: (
            "📋 *دايلي ميديكال*\n\n"
            "أحدث الأبحاث الطبية والأخبار الصحية من حول العالم — "
            "محتوى علمي يتجدد يومياً لمن يتابع كل ما هو جديد في الطب 🔬",
            site_url("health", 2),
            "🔬 تصفّح دايلي ميديكال"
        ),
        lambda: (
            "📖 *دليل الصحة — MSD Manuals*\n\n"
            "المرجع الطبي العالمي الأشمل متاح بالعربي — "
            "ابحث عن أي مرض أو دواء أو حالة طبية بتفصيل كامل 💡",
            site_url("health", 3),
            "💡 ابحث في دليل الصحة"
        ),
        lambda: (
            "🧠 *الصحة النفسية*\n\n"
            "الصحة النفسية بنفس أهمية الجسدية — "
            "مقالات وموارد تساعدك تفهم مشاعرك وتتعامل مع ضغوط الحياة بشكل أفضل 🌿",
            site_url("health", 4),
            "🌿 اقرأ عن الصحة النفسية"
        ),
        lambda: (
            "✨ *الصحة والجمال*\n\n"
            "عناية بالبشرة والجسم من الداخل والخارج — "
            "نصائح وروتين يومي لمن يبحث عن جمال حقيقي يبدأ من الصحة 💅",
            site_url("health", 5),
            "💅 اكتشف نصائح الصحة والجمال"
        ),
    ],

    # ── BOOKS ─────────────────────────────────────────────────────────────────
    "books": [
        lambda: (
            "📗 *مكتبة نور*\n\n"
            "أكبر مكتبة عربية رقمية مجانية — "
            "آلاف الكتب في كل المجالات جاهزة للتحميل الفوري بدون تسجيل 🌟",
            site_url("books", 0),
            "📖 ابحث في نور كتب"
        ),
        lambda: (
            "📚 *مكتبة سهم*\n\n"
            "كتب PDF نادرة وغير متاحة في كثير من المكتبات — "
            "اختارها بنفسك وابدأ القراءة في دقائق 🔍",
            site_url("books", 1),
            "🔍 استكشف مكتبة سهم"
        ),
        lambda: (
            "📖 *كتباتي*\n\n"
            "مكتبة مجانية تضم روايات وكتباً أدبية وعلمية وثقافية — "
            "الكتاب الذي تبحث عنه غالباً موجود هنا 📂",
            site_url("books", 2),
            "📂 تصفّح كتباتي"
        ),
        lambda: (
            "⭐ *المكتبة العربية*\n\n"
            "تصنيف ذكي للكتب العربية من مصادر موثوقة — "
            "ابحث بالعنوان أو الكاتب أو الموضوع واعثر على ما يناسبك 🗂️",
            site_url("books", 3),
            "🗂️ استكشف المكتبة العربية"
        ),
        lambda: (
            "🗄️ *كتابك عندنا*\n\n"
            "محرك بحث متخصص في الكتب العربية — "
            "اكتب اسم الكتاب أو الكاتب وستجد ما تريد في ثوانٍ 🔎",
            site_url("books", 4),
            "🔎 ابحث عن كتابك"
        ),
        lambda: (
            "📰 *مجلة الكتب العربية*\n\n"
            "لمن يتابع عالم الأدب والنشر — "
            "أحدث الإصدارات وأبرز الكتّاب ومراجعات نقدية من المشهد الثقافي العربي 🗞️",
            site_url("books", 5),
            "🗞️ اقرأ أخبار عالم الكتب"
        ),
        lambda: (
            "☕ *قهوة غرب*\n\n"
            "محتوى أدبي وفكري يرافق فنجان قهوتك — "
            "قصص ومقالات ثقافية تجعل كل لحظة هادئة أعمق 🌙",
            site_url("books", 6),
            "🌙 استكشف قهوة غرب"
        ),
    ],

    # ── SPORTS ────────────────────────────────────────────────────────────────
    "sports": [
        lambda: (
            "⚽ *كووورة — أخبار الرياضة*\n\n"
            "المصدر الأول للأخبار الرياضية العربية — نتائج، تشكيلات، انتقالات، "
            "ومواعيد المباريات القادمة كلها في مكان واحد ⚽",
            site_url("sports", 0),
            "⚽ تصفّح كووورة"
        ),
        lambda: (
            "📊 *365 سكور — النتائج المباشرة*\n\n"
            "ترتيبات الدوريات ونتائج المباريات لحظة بلحظة من كل بقاع العالم — "
            "لا تفوّت أي هدف 🏆",
            site_url("sports", 1),
            "🏆 تابع النتائج الآن"
        ),
        lambda: (
            "🔴 *مباريات لايف*\n\n"
            "بث مباشر حصري للمباريات الجارية الآن — "
            "ادخل واختار المباراة التي تريد متابعتها مباشرةً 📺",
            site_url("sports", 2),
            "📺 شاهد البث المباشر"
        ),
        lambda: (
            "⚡ *مباريات لايف*\n\n"
            "بث مباشر للمباريات الجارية الآن — "
            "نفس التغطية الكاملة لكل الملاعب والدوريات 🏟️",
            site_url("sports", 3),
            "🏟️ شاهد المباريات المباشرة"
        ),
        lambda: (
            "📡 *قنوات رياضية مباشرة*\n\n"
            "قنوات beIN Sports وغيرها ببث مباشر — "
            "اختار قناتك المفضلة وتابع أفضل المحتوى الرياضي 🎙️",
            site_url("sports", 4),
            "🎙️ اختار قناتك الرياضية"
        ),
        lambda: (
            "🌍 *رياضة عالمية*\n\n"
            "من كأس العالم إلى دوري الأبطال وكل الرياضات الأولمبية — "
            "متابعة شاملة للحدث الرياضي العالمي 🏅",
            site_url("sports", 5),
            "🏅 اكتشف الرياضة العالمية"
        ),
    ],

    # ── SOCIAL ────────────────────────────────────────────────────────────────
    "social": [
        lambda: (
            "📱 *كل منصاتك في نقرة واحدة*\n\n"
            "فيسبوك، إنستغرام، يوتيوب، تيك توك وأكثر من 10 منصات — "
            "افتحها كلها من نت باشا بدون ما تبحث عن كل تطبيق على حدة 🚀",
            site_url("social", 0),
            "🚀 افتح منصاتك الاجتماعية"
        ),
        lambda: (
            "🐦 *X — تويتر*\n\n"
            "وصّلناك لـ X مباشرةً من نت باشا — "
            "تابع الترندات والنقاشات اللي يتحدث عنها العالم الآن دون تضييع وقت 🔥",
            site_url("social", 1),
            "🔥 افتح X الآن"
        ),
        lambda: (
            "📷 *إنستغرام — في ثانية واحدة*\n\n"
            "نت باشا يوصّلك لإنستغرام فوراً من غير ما تفتح شيء ثاني — "
            "ريلز وستوريز جديدة تنتظرك الآن 🎬",
            site_url("social", 2),
            "🎬 افتح إنستغرام"
        ),
        lambda: (
            "📹 *يوتيوب — من هنا مباشرة*\n\n"
            "نت باشا يجمع كل منصاتك في مكان واحد — "
            "ادخل ليوتيوب الآن وابحث عن أي فيديو بدون خطوات إضافية ▶️",
            site_url("social", 3),
            "▶️ افتح يوتيوب"
        ),
        lambda: (
            "🎵 *تيك توك — وصول فوري*\n\n"
            "بدل ما تدور على التطبيق، نت باشا يفتحه لك مباشرةً — "
            "محتوى لا ينتهي في انتظارك 🎬",
            site_url("social", 4),
            "🎬 افتح تيك توك"
        ),
        lambda: (
            "👻 *سناب شات — ادخل بنقرة*\n\n"
            "قسم التواصل في نت باشا يوصّلك لسناب شات فوراً — "
            "ستوريز أصدقائك ما انتظرت 📸",
            site_url("social", 5),
            "📸 افتح سناب شات"
        ),
        lambda: (
            "🎮 *ديسكورد — سيرفرك بانتظارك*\n\n"
            "وصّلناك مباشرةً لديسكورد من نت باشا — "
            "انضم لسيرفرك وتواصل مع مجتمعك بدون أي تأخير 🔗",
            site_url("social", 6),
            "🔗 افتح ديسكورد"
        ),
        lambda: (
            "🟣 *تويتش — البثوث المباشرة*\n\n"
            "من نت باشا لتويتش في نقرة — "
            "شاهد البثوث الحية الآن من ألعاب وموسيقى وأكثر 🔴",
            site_url("social", 7),
            "🔴 افتح تويتش"
        ),
        lambda: (
            "💼 *لينكد إن — شبكتك المهنية*\n\n"
            "نت باشا يوفر وصول سريع لكل منصاتك بما فيها لينكد إن — "
            "تابع فرص العمل والمحتوى المهني بنقرة واحدة 🌐",
            site_url("social", 8),
            "🌐 افتح لينكد إن"
        ),
        lambda: (
            "💬 *واتساب ويب — من هنا*\n\n"
            "نت باشا يفتح لك واتساب ويب مباشرةً — "
            "راسل أصدقاءك ومجموعاتك بدون ما تمسك هاتفك 📲",
            site_url("social", 9),
            "📲 افتح واتساب ويب"
        ),
        lambda: (
            "🧵 *ثريدز — النقاش بطريقة مختلفة*\n\n"
            "وصّلناك لثريدز مباشرةً — "
            "شارك أفكارك وتابع المحادثات اللي تهمك بضغطة واحدة من نت باشا 💭",
            site_url("social", 10),
            "💭 افتح ثريدز"
        ),
        lambda: (
            "📌 *بينترست — إلهام بنقرة*\n\n"
            "نت باشا يجمع كل منصاتك — بما فيها بينترست — "
            "ابحث عن أفكار الديكور والموضة والطبخ من مكان واحد 🎨",
            site_url("social", 11),
            "🎨 افتح بينترست"
        ),
        lambda: (
            "🤖 *ريديت — كل المجتمعات هنا*\n\n"
            "ادخل لريديت مباشرةً من نت باشا — "
            "آلاف النقاشات والمجتمعات المتخصصة في انتظار أسئلتك 💬",
            site_url("social", 12),
            "💬 افتح ريديت"
        ),
        lambda: (
            "❓ *كورا — الأسئلة والأجوبة*\n\n"
            "من نت باشا لكورا في ثانية واحدة — "
            "ابحث عن إجابة لأي سؤال أو شارك خبرتك مع الآخرين 🔍",
            site_url("social", 13),
            "🔍 افتح كورا"
        ),
        lambda: (
            "🔵 *في كي VK — محتوى لا تجده غيره*\n\n"
            "نت باشا يوصّلك لـ VK مباشرةً — "
            "مجتمعات ومحتوى ضخم لا تجده في المنصات الأخرى 🌐",
            site_url("social", 14),
            "🌐 افتح في كي"
        ),
    ],

    # ── FOOD ──────────────────────────────────────────────────────────────────
    "food": [
        lambda: (
            "🌶️ *المطبخ الشامي الأصيل*\n\n"
            "كبة، محاشي، مقلوبة — "
            "شامي فود يحفظ وصفات المطبخ الشامي بكل تفاصيلها للأجيال القادمة 🍽️",
            site_url("food", 0),
            "🍽️ تصفّح وصفات شامية"
        ),
        lambda: (
            "🍳 *وصفات من كل المطابخ العربية*\n\n"
            "المطبخ المصري، اللبناني، الخليجي، المغربي — "
            "تنوع لا حدود له في موقع واحد 👨‍🍳",
            site_url("food", 1),
            "👨‍🍳 استكشف الوصفات العربية"
        ),
        lambda: (
            "👩‍🍳 *فن الطهي — عالم الطبخ*\n\n"
            "من الباستا الإيطالية إلى السوشي الياباني — "
            "دليل الطبخ العالمي بخطوات مبسطة لكل طموح في المطبخ 🌍",
            site_url("food", 2),
            "🌍 اكتشف مطابخ العالم"
        ),
        lambda: (
            "🍲 *أكل وبس — بساطة المطبخ اليومي*\n\n"
            "وصفات سريعة وعملية لكل يوم — "
            "بدون تعقيد، بدون وقت طويل، فقط طعام لذيذ ومغذٍ 🔥",
            site_url("food", 3),
            "🔥 ابحث عن وصفة اليوم"
        ),
        lambda: (
            "🍰 *غوودي كيتشن — الطهي الاحترافي*\n\n"
            "وصفات موضحة بصور وخطوات دقيقة — "
            "سواء كنت مبتدئاً أو محترفاً ستجد ما يحدّي مهاراتك 🎂",
            site_url("food", 4),
            "🎂 تصفّح وصفات غوودي"
        ),
        lambda: (
            "🥘 *طبخات كوم — الأرشيف الكبير*\n\n"
            "آلاف الوصفات مفهرسة ومصنفة — "
            "ابحث بالمكون أو اسم الطبق وابدأ الطبخ فوراً 🍽️",
            site_url("food", 5),
            "🍽️ ابحث في طبخات كوم"
        ),
        lambda: (
            "🥗 *الطبخ الصحي — نمط حياة*\n\n"
            "وصفات مغذية ومتوازنة لمن يهتم بما يضعه في طبقه — "
            "صحة الجسم تبدأ من اختيار الأكل الصحيح 🥦",
            site_url("food", 6),
            "🥦 استكشف الطبخ الصحي"
        ),
        lambda: (
            "🍱 *يمي — شهية الطبخ اليومي*\n\n"
            "طبخات لذيذة وسهلة مناسبة لكل الأذواق — "
            "اكتشف شو تطبخ اليوم وفاجئ عيلتك 😋",
            site_url("food", 7),
            "😋 اكتشف وصفات يمي"
        ),
        lambda: (
            "🍳 *أطيب أكلة — من كل مطبخ طبق*\n\n"
            "مجموعة ضخمة من أشهى الأطباق العربية والعالمية — "
            "كل وصفة مجربة وموثوقة 🌶️",
            site_url("food", 8),
            "🌶️ تصفّح أطيب أكلة"
        ),
    ],

    # ── TECH ──────────────────────────────────────────────────────────────────
    "tech": [
        lambda: (
            "🛠️ *التقنية السورية*\n\n"
            "أخبار عالم التقنية بعيون عربية — هواتف، حواسيب، "
            "تطبيقات وكل جديد بلهجة تفهمها 💻",
            site_url("tech", 0),
            "💻 تصفّح أخبار التقنية"
        ),
        lambda: (
            "🤖 *ذكاء اصطناعي فوري*\n\n"
            "جرّب نماذج الذكاء الاصطناعي الأقوى في العالم الآن — "
            "بدون تسجيل ولا حساب، فقط اكتب وانطلق 🚀",
            site_url("tech", 1),
            "🚀 جرّب الذكاء الاصطناعي"
        ),
        lambda: (
            "⚙️ *أدوات AI المجانية*\n\n"
            "دليل شامل بأفضل أدوات الذكاء الاصطناعي المجانية — "
            "ابحث عن الأداة التي تحتاجها وابدأ عملك أسرع 🧠",
            site_url("tech", 2),
            "🧠 استكشف أدوات AI"
        ),
        lambda: (
            "📊 *مقارنات الأجهزة*\n\n"
            "قبل ما تشتري أي جهاز، قارن مواصفاته مع المنافسين — "
            "معلومات دقيقة تساعدك تختار الأفضل بسعرك 🔍",
            site_url("tech", 3),
            "🔍 قارن بين الأجهزة"
        ),
        lambda: (
            "📱 *شروحات ومراجعات*\n\n"
            "مراجعات تقنية موضوعية وشروحات عملية — "
            "اقرأ قبل ما تشتري واعرف رأي الخبراء 📖",
            site_url("tech", 4),
            "📖 اقرأ الشروحات والمراجعات"
        ),
        lambda: (
            "📲 *تطبيقات أندرويد المدفوعة مجاناً*\n\n"
            "يوفر تطبيقات أندرويد مدفوعة بالمجان — "
            "حمّل وجرب قبل ما تدفع ⬇️",
            site_url("tech", 5),
            "⬇️ حمّل التطبيقات المدفوعة"
        ),
        lambda: (
            "💻 *برامج كمبيوتر مدفوعة*\n\n"
            "يجمع لك برامج الكمبيوتر الاحترافية — "
            "فوتوشوب، مونتاج، برمجة وأكثر بدون دفع 🖥️",
            site_url("tech", 6),
            "🖥️ ابحث في برامج الكمبيوتر"
        ),
        lambda: (
            "📦 *تطبيقات لكل الأنظمة*\n\n"
            "مكتبة ضخمة من التطبيقات لكل الأجهزة — "
            "ابحث عن أي تطبيق وحمّله بنقرة واحدة 🍎",
            site_url("tech", 7),
            "🍎 تصفّح مكتبة التطبيقات"
        ),
        lambda: (
            "🍎 *متجر تطبيقات آبل*\n\n"
            "App Store الرسمي بالكامل في متناول يدك — "
            "ابحث عن التطبيق الذي يكمل جهازك وحمّله الآن 📱",
            site_url("tech", 8),
            "📱 استكشف App Store"
        ),
    ],

    # ── MOVIES ────────────────────────────────────────────────────────────────
    "movies": [
        lambda: (
            "🎬 *دليل الأفلام — أخبار السينما*\n\n"
            "كل ما يخص السينما والدراما في مكان واحد — "
            "أفضل الأفلام لهذا الموسم وتقييمات موثوقة تساعدك تختار 🎥",
            site_url("movies", 0),
            "🎥 اكتشف دليل الأفلام"
        ),
        lambda: (
            "🎞️ *كيو فيلم — مشاهدة فورية*\n\n"
            "مكتبة أفلام ومسلسلات جاهزة للمشاهدة الآن — "
            "جودة عالية وبدون انتظار 🍿",
            site_url("movies", 1),
            "🍿 شاهد في كيو فيلم"
        ),
        lambda: (
            "🌍 *المصطبة — التنوع العربي والعالمي*\n\n"
            "محتوى لا ينتهي من كل الجنسيات والأنواع — "
            "ابحث بالاسم أو تصفّح القوائم المختارة 🎬",
            site_url("movies", 2),
            "🎬 تصفّح المصطبة"
        ),
        lambda: (
            "🍿 *مدينة الأفلام — اختيارات اليوم*\n\n"
            "موقع متجدد يومياً بأحدث الأفلام والمسلسلات — "
            "ما بتعرف شو تشوف؟ الموقع يختار لك 🎦",
            site_url("movies", 3),
            "🎦 اكتشف مدينة الأفلام"
        ),
        lambda: (
            "📽️ *مسلسلات تايم — الدراما بلا حدود*\n\n"
            "المسلسلات العربية والعالمية والتركية في أرشيف ضخم — "
            "تابع ما يبث وما يستحق المشاهدة 🎞️",
            site_url("movies", 4),
            "🎞️ تصفّح مسلسلات تايم"
        ),
        lambda: (
            "🌹 *قصة عشق — الدراما التركية*\n\n"
            "أشهر المسلسلات التركية مدبلجة ومترجمة للعربي — "
            "من المؤسس عثمان إلى أحدث الدراما الرومانسية 💫",
            site_url("movies", 6),
            "💫 شاهد في قصة عشق"
        ),
        lambda: (
            "⭐ *كيبوراما — الدراما الكورية*\n\n"
            "K-Drama مترجمة بالعربي لمحبي الدراما الكورية — "
            "أحدث الموسم وكلاسيكيات لا تُنسى 🌏",
            site_url("movies", 5),
            "🌏 استكشف كيبوراما"
        ),
        lambda: (
            "🎥 *فشار — مشاهدة مباشرة*\n\n"
            "موقع مشاهدة مباشر وسريع بدون تعقيدات — "
            "ابحث عن فيلمك وابدأ المشاهدة فوراً 🎭",
            site_url("movies", 8),
            "🎭 شاهد في فشار"
        ),
        lambda: (
            "🌟 *أهواك — المحتوى العربي*\n\n"
            "منصة للمحتوى العربي الأصيل والمسلسلات المحلية — "
            "اكتشف نجوم العالم العربي ومحتواهم 📺",
            site_url("movies", 9),
            "📺 اكتشف منصة أهواك"
        ),
    ],

    # ── ANIME ─────────────────────────────────────────────────────────────────
    "anime": [
        lambda: (
            "🎌 *أخبار الأنمي*\n\n"
            "آخر الأخبار والإعلانات عن الأنمي الجديد — "
            "اعرف ما سيُعرض هذا الموسم قبل الجميع 🌸",
            site_url("anime", 0),
            "🌸 تابع أخبار الأنمي"
        ),
        lambda: (
            "📖 *دليل المانغا*\n\n"
            "أوسع دليل للمانغا بالعربي — "
            "ابحث عن مانغا جديدة أو تابع تفاصيل ما تقرأه 📚",
            site_url("anime", 1),
            "📚 تصفّح دليل المانغا"
        ),
        lambda: (
            "📖 *قراءة المانغا مباشرة*\n\n"
            "اقرأ الفصول الجديدة من المانغا مباشرةً في المتصفح — "
            "لا تحميل ولا انتظار، فقط اقرأ 🎌",
            site_url("anime", 2),
            "🎌 اقرأ المانغا الآن"
        ),
        lambda: (
            "🌟 *انمي فور اب — مترجم بالعربي*\n\n"
            "مكتبة ضخمة من الأنمي مترجم للعربي بجودة عالية — "
            "الحلقات الجديدة تُضاف فور صدورها ⚔️",
            site_url("anime", 3),
            "⚔️ شاهد في انمي فور اب"
        ),
        lambda: (
            "⚔️ *انمي بيك — أرشيف شامل*\n\n"
            "من الكلاسيكيات القديمة إلى أحدث الموسم — "
            "أرشيف أنمي ضخم ينتظر استكشافك 🔍",
            site_url("anime", 4),
            "🔍 استكشف انمي بيك"
        ),
        lambda: (
            "🌸 *اوك أنمي — متجدد ومنظم*\n\n"
            "تصميم سهل وأنمي منظم بالموسم والجنس — "
            "ابدأ مشاهدة جديدة أو تابع ما بدأته 🎬",
            site_url("anime", 5),
            "🎬 تابع في اوك أنمي"
        ),
        lambda: (
            "🎯 *ريستو — اختيار متميز*\n\n"
            "مكتبة أنمي منتقاة بعناية — "
            "إذا كنت تبحث عن تجربة مشاهدة مختلفة، هذا هو المكان 🎌",
            site_url("anime", 6),
            "🎌 اكتشف ريستو أنمي"
        ),
        lambda: (
            "🌺 *ويت أنمي — منظم وسريع*\n\n"
            "واجهة نظيفة وأنمي مترجم بدقة — "
            "تصفّح بسرعة واعثر على ما تبحث عنه دون عناء 🔎",
            site_url("anime", 7),
            "🔎 تصفّح ويت أنمي"
        ),
        lambda: (
            "🌙 *أنمي سيلفر — جودة فائقة*\n\n"
            "مكتبة أنمي مختارة بجودة عرض عالية — "
            "لمن يهتم بتفاصيل الصوت والترجمة ويريد تجربة مشاهدة راقية ✨",
            site_url("anime", 8),
            "✨ شاهد في أنمي سيلفر"
        ),
    ],

    # ── MUSIC ─────────────────────────────────────────────────────────────────
    "music": [
        lambda: (
            "🎵 *أنغامي — الموسيقى العربية*\n\n"
            "المنصة الأولى للأغاني العربية الأصيلة — "
            "استمع لأحدث الإصدارات وأشهر الأغاني وأصوات جيلك 🎶",
            site_url("music", 0),
            "🎶 استمع على أنغامي"
        ),
        lambda: (
            "📻 *راديو نت باشا — 24 ساعة*\n\n"
            "راديو موسيقى متواصل لا يتوقف — "
            "موسيقى تختار لك بذوق دقيق من الصباح للنوم 🎧",
            site_url("music", 1),
            "🎧 استمع للراديو الآن"
        ),
        lambda: (
            "📰 *بيلبورد عربية — نبض الموسيقى*\n\n"
            "أحدث الأخبار الموسيقية وقوائم الأغاني الأكثر استماعاً — "
            "من الوطن العربي والعالم 🎵",
            site_url("music", 2),
            "🎵 تابع أخبار الموسيقى"
        ),
        lambda: (
            "⬇️ *تحميل MP3*\n\n"
            "ابحث عن أي أغنية وحمّلها بجودة MP3 فوراً — "
            "أرشيف ضخم يضم ملايين الأغاني العربية والعالمية 🎤",
            site_url("music", 3),
            "🎤 ابحث وحمّل أغنيتك"
        ),
        lambda: (
            "💿 *تحميل ألبومات كاملة*\n\n"
            "حمّل الألبوم بالكامل بضغطة واحدة — "
            "مثالي لمن يريد مكتبة موسيقية محلية دون انقطاع الإنترنت 🎼",
            site_url("music", 4),
            "🎼 حمّل ألبومات كاملة"
        ),
        lambda: (
            "🆕 *أحدث الألبومات*\n\n"
            "الإصدارات الموسيقية الأحدث عربياً وعالمياً — "
            "اكتشف ما صدر حديثاً وسافر مع كل ألبوم جديد 🎵",
            site_url("music", 5),
            "🎵 اكتشف الإصدارات الجديدة"
        ),
        lambda: (
            "🌍 *موسيقى أجنبية مجانية*\n\n"
            "مئات الآلاف من الأغاني العالمية مرخصة ومجانية تماماً — "
            "اكتشف فنانين مستقلين من كل أنحاء العالم 🎸",
            site_url("music", 6),
            "🎸 استكشف موسيقى جامندو"
        ),
    ],

    # ── TV / CHANNELS ─────────────────────────────────────────────────────────
    "tv": [
        lambda: (
            "📺 *دليل البرامج — ماذا يُبث الآن؟*\n\n"
            "اعرف جدول بث كل قناة عربية في الوقت الحالي — "
            "لا تفوّت برنامجك المفضل أبداً 🕐",
            site_url("tv", 0),
            "🕐 تحقق من دليل البرامج"
        ),
        lambda: (
            "📡 *قنوات عربية مباشرة*\n\n"
            "MBC، الجزيرة، روتانا وعشرات القنوات العربية ببث مباشر — "
            "اختار واستمتع بدون تأخير 🔴",
            site_url("tv", 1),
            "🔴 شاهد القنوات العربية"
        ),
        lambda: (
            "📡 *قنوات عربية مباشرة*\n\n"
            "بث مباشر لعشرات القنوات العربية"
            "قنوات ترفيه وثائقية أطفال و المزيد 🔴",
            site_url("tv", 2),
            "🔴 شاهد القنوات العربية"
        ),
        lambda: (
            "🌍 *قنوات عالمية — من كل دولة*\n\n"
            "يجمع قنوات من كل أنحاء العالم ببث مباشر — "
            "أخبار، ثقافة، رياضة عالمية من مصدرها الأصلي 🌐",
            site_url("tv", 3),
            "🌐 تصفّح القنوات العالمية"
        ),
        lambda: (
            "🗺️ *قنوات الدول*\n\n"
            "ابحث عن قنوات أي دولة في العالم وشاهدها مباشرة — "
            "من المغرب للهند، كل دولة موجودة 🌍",
            site_url("tv", 4),
            "🌍 ابحث عن قنوات دولتك"
        ),
        lambda: (
            "🎙️ *إذاعات راديو عربية*\n\n"
            "محطات الراديو العربية المشهورة ببث مباشر — "
            "الأغاني، الأخبار، البرامج الثقافية كلها في راديو واحد 📻",
            site_url("tv", 5),
            "📻 استمع للراديو العربي"
        ),
    ],
}

WELCOME_MSG = """\
👋 *أهلاً بك في نت باشا!*
**نت باشا - الإنترنت بين يديك في مكان واحد**

تعبت من التنقل بين عشرات المواقع والتطبيقات للعثور على المحتوى الذي تبحث عنه؟

**نت باشا** هو تطبيق  يجمع لك أفضل المصادر العربية والعالمية في منصة واحدة سهلة وسريعة، لتصل إلى المحتوى الذي تريده بضغطة زر، دون إعلانات مزعجة ودون إضاعة للوقت.

### ماذا يقدم لك نت باشا؟

🔹 أحدث الأخبار والمحتوى المحدث باستمرار
🔹 وصول سريع ومنظم لأقوى المواقع العالمية والعربية
🔹 واجهة بسيطة وسهلة الاستخدام داخل تيليغرام
🔹 تجربة خالية من الإعلانات المزعجة
🔹 كل ما تحتاجه في مكان واحد

### الأقسام المتوفرة:

🎬 الأفلام
📺 القنوات المباشرة
⚽ الرياضة
🎌 الأنمي والمانغا
🎵 الموسيقى
🍔 الطعام
💪 الصحة
📱 تطبيقات التواصل الاجتماعي
📚 الكتب
💻 التقنية

يحتوي كل قسم على مجموعة مختارة من المواقع والمصادر الموثوقة لتسهيل الوصول إلى المحتوى بأسرع طريقة ممكنة.

### الاشتراك

💎 اشتراك رمزي يناسب الجميع
🎁 تجربة مجانية لمدة 24 ساعة للمستخدمين الجدد

**نت باشا** ليس مجرد دليل مواقع، بل بوابتك الذكية للوصول إلى الإنترنت بشكل أسرع وأسهل وأكثر تنظيماً. افتح وابدأ 👇\
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
    """Pick a variant, return (text, url, btn_label). No repeats until all used."""
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
    result = msg_list[idx]()
    # Support both (text, url) and (text, url, btn_label)
    if len(result) == 3:
        text, url, btn_label = result
    else:
        text, url = result
        btn_label = f"{CATEGORIES[category]['emoji']} {CATEGORIES[category]['label']}"
    return text, url, btn_label

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
        text, url, btn_label = build_message(category, user_data)

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(btn_label, url=url)
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
            text, url, btn_label = build_message(category, user_data)
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(btn_label, url=url)
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
