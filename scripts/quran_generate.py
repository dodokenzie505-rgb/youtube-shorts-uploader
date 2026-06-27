"""
Script de génération de vidéos Quran Daily Reel.
Extrait de quran_reel_v7-5_corrige.ipynb — appelé par daily_upload.py.
"""
import subprocess, sys, os
from pathlib import Path

# Installation des dépendances système si nécessaire
def _ensure_installed():
    import shutil
    if not shutil.which("ffmpeg"):
        subprocess.run(["sudo", "apt-get", "install", "-y", "-q", "ffmpeg"], check=True)
    amiri_path = "/usr/share/fonts/truetype/fonts-hosny-amiri/Amiri-Regular.ttf"
    if not os.path.exists(amiri_path):
        subprocess.run(["sudo", "apt-get", "install", "-y", "-q", "fonts-hosny-amiri"], check=True)
    try:
        import PIL
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"], check=True)
    try:
        import whisper
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "openai-whisper", "-q"], check=True)

_ensure_installed()

import subprocess, sys, importlib, shutil

def _ensure_installed():
    # ── ffmpeg ──────────────────────────────────────────────────────────────
    if not shutil.which("ffmpeg"):
        print("📦 Installation ffmpeg...")
        subprocess.run(["apt-get", "install", "-y", "-q", "ffmpeg"], check=True)
        print("✅ ffmpeg OK")
    else:
        print("✅ ffmpeg déjà présent")

    # ── fonts-hosny-amiri ────────────────────────────────────────────────────
    amiri_path = "/usr/share/fonts/truetype/fonts-hosny-amiri/Amiri-Regular.ttf"
    import os
    if not os.path.exists(amiri_path):
        print("📦 Installation polices arabes...")
        subprocess.run(["apt-get", "install", "-y", "-q", "fonts-hosny-amiri"], check=True)
        print("✅ Polices OK")
    else:
        print("✅ Polices arabes déjà présentes")

    # ── Pillow ───────────────────────────────────────────────────────────────
    try:
        import PIL
        print("✅ Pillow déjà présent")
    except ImportError:
        print("📦 Installation Pillow...")
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"], check=True)
        print("✅ Pillow OK")

    # ── openai-whisper ───────────────────────────────────────────────────────
    try:
        import whisper
        print("✅ Whisper déjà présent")
    except ImportError:
        print("📦 Installation Whisper (peut prendre ~1 min)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "openai-whisper", "-q"], check=True)
        print("✅ Whisper OK")

_ensure_installed()
print("\n🚀 Démarrage de la génération...\n")

import os, sys, math, subprocess, datetime, json, random, time, hashlib, unicodedata, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import urllib.request

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")
_whisper_model = None
_WHISPER_OK    = False

def _load_whisper():
    global _whisper_model, _WHISPER_OK
    if _whisper_model is not None:
        return _WHISPER_OK
    try:
        import whisper
        print(f"   🎙  Chargement Whisper '{WHISPER_MODEL_SIZE}'...")
        _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
        _WHISPER_OK    = True
        print(f"   ✅ Whisper prêt")
    except ImportError:
        print("   ⚠  Whisper non installé")
        _WHISPER_OK = False
    except Exception as e:
        print(f"   ⚠  Whisper erreur : {e}")
        _WHISPER_OK = False
    return _WHISPER_OK

W, H      = 1080, 1920
FPS       = 24
# v7 : PAS de limite de durée — on joue TOUS les versets du passage sans coupure
MAX_DUR   = None   # Pas de limite : la récitation n'est jamais coupée
BREATH    = 0.40   # Silence naturel entre versets (respecte le rythme de la récitation)
ACCOUNT   = os.getenv("IG_HANDLE", "@quranreminders14")
OUT_DIR   = Path("quran_out")
for d in [OUT_DIR, OUT_DIR / "frames", OUT_DIR / "cache"]:
    d.mkdir(exist_ok=True)

def make_seed():
    raw = f"{time.time_ns()}_{os.urandom(16).hex()}_{os.getpid()}"
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16) % (2 ** 31)

RUN_SEED = make_seed()
RNG      = random.Random(RUN_SEED)

# ═══════════════════════════════════════════════════════════════════════════
# PASSAGES — 35 thèmes avec plusieurs versets chacun
# ═══════════════════════════════════════════════════════════════════════════
PASSAGES = [
    # 0 ─ Al-Fatiha complète
    {"title": "Al-Fatiha", "verses": [
        {"ar": "بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيمِ",   "en": "In the name of Allah,\nthe Most Gracious, the Most Merciful.",  "ref": "1:1",  "surah": 1,  "ayah": 1},
        {"ar": "الْحَمْدُ لِلّٰهِ رَبِّ الْعَالَمِينَ",    "en": "All praise is due to Allah,\nLord of all the worlds.",            "ref": "1:2",  "surah": 1,  "ayah": 2},
        {"ar": "الرَّحْمٰنِ الرَّحِيمِ",                   "en": "The Most Gracious,\nthe Most Merciful.",                         "ref": "1:3",  "surah": 1,  "ayah": 3},
        {"ar": "مَالِكِ يَوْمِ الدِّينِ",                  "en": "Master of the Day of Judgment.",                                 "ref": "1:4",  "surah": 1,  "ayah": 4},
        {"ar": "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "en": "It is You we worship\nand You we ask for help.",                "ref": "1:5",  "surah": 1,  "ayah": 5},
        {"ar": "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ",       "en": "Guide us to the straight path.",                                 "ref": "1:6",  "surah": 1,  "ayah": 6},
        {"ar": "صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ", "en": "The path of those You have blessed,\nnot those who have earned anger\nnor those who are astray.", "ref": "1:7", "surah": 1, "ayah": 7},
    ]},

    # 1 ─ La patience et l'espoir — Al-Inshirah
    {"title": "La patience et l'espoir", "verses": [
        {"ar": "أَلَمْ نَشْرَحْ لَكَ صَدْرَكَ",             "en": "Did We not expand\nfor you your chest?",                         "ref": "94:1", "surah": 94, "ayah": 1},
        {"ar": "وَوَضَعْنَا عَنكَ وِزْرَكَ",               "en": "And removed from you\nyour burden?",                              "ref": "94:2", "surah": 94, "ayah": 2},
        {"ar": "الَّذِي أَنقَضَ ظَهْرَكَ",                 "en": "Which had weighed\nheavily upon your back?",                      "ref": "94:3", "surah": 94, "ayah": 3},
        {"ar": "وَرَفَعْنَا لَكَ ذِكْرَكَ",                "en": "And raised high\nyour repute?",                                    "ref": "94:4", "surah": 94, "ayah": 4},
        {"ar": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا",           "en": "For indeed, with hardship\nwill be ease.",                        "ref": "94:5", "surah": 94, "ayah": 5},
        {"ar": "إِنَّ مَعَ الْعُسْرِ يُسْرًا",             "en": "Indeed, with hardship\nwill be ease.",                            "ref": "94:6", "surah": 94, "ayah": 6},
        {"ar": "فَإِذَا فَرَغْتَ فَانصَبْ",                "en": "So when you have finished\nyour duties, then stand up.",           "ref": "94:7", "surah": 94, "ayah": 7},
        {"ar": "وَإِلَىٰ رَبِّكَ فَارْغَبْ",               "en": "And to your Lord\ndirect your longing.",                          "ref": "94:8", "surah": 94, "ayah": 8},
    ]},

    # 2 ─ La confiance en Allah — At-Talaq
    {"title": "La confiance en Allah", "verses": [
        {"ar": "وَمَن يَتَّقِ اللّٰهَ يَجْعَل لَّهُ مَخْرَجًا", "en": "And whoever fears Allah,\nHe will make for him a way out.", "ref": "65:2", "surah": 65, "ayah": 2},
        {"ar": "وَيَرْزُقْهُ مِنْ حَيْثُ لَا يَحْتَسِبُ",       "en": "And will provide for him\nfrom where he does not expect.",  "ref": "65:3", "surah": 65, "ayah": 3},
        {"ar": "وَمَن يَتَوَكَّلْ عَلَى اللّٰهِ فَهُوَ حَسْبُهُ", "en": "Whoever relies upon Allah —\nHe is sufficient for him.", "ref": "65:3b","surah": 65, "ayah": 3},
        {"ar": "إِنَّ اللّٰهَ بَالِغُ أَمْرِهِ",              "en": "Indeed, Allah will accomplish\nHis purpose.",                  "ref": "65:3c","surah": 65, "ayah": 3},
        {"ar": "قَدْ جَعَلَ اللّٰهُ لِكُلِّ شَيْءٍ قَدْرًا",  "en": "Allah has already set\na decreed extent for everything.", "ref": "65:3d","surah": 65, "ayah": 3},
    ]},

    # 3 ─ Al-Ikhlas complète
    {"title": "Al-Ikhlas — La Pureté", "verses": [
        {"ar": "قُلْ هُوَ اللّٰهُ أَحَدٌ",               "en": "Say: He is Allah, [who is] One.",               "ref": "112:1", "surah": 112, "ayah": 1},
        {"ar": "اللّٰهُ الصَّمَدُ",                      "en": "Allah, the Eternal Refuge.",                    "ref": "112:2", "surah": 112, "ayah": 2},
        {"ar": "لَمْ يَلِدْ وَلَمْ يُولَدْ",             "en": "He neither begets\nnor is born.",                "ref": "112:3", "surah": 112, "ayah": 3},
        {"ar": "وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ",      "en": "Nor is there to Him\nany equivalent.",           "ref": "112:4", "surah": 112, "ayah": 4},
    ]},

    # 4 ─ Ayat Al-Kursi
    {"title": "Ayat Al-Kursi", "verses": [
        {"ar": "اللّٰهُ لَا إِلٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ", "en": "Allah — there is no deity except Him,\nthe Ever-Living, the Sustainer.", "ref": "2:255a", "surah": 2, "ayah": 255},
        {"ar": "لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ",       "en": "Neither drowsiness overtakes Him\nnor sleep.",                     "ref": "2:255b", "surah": 2, "ayah": 255},
        {"ar": "لَّهُ مَا فِي السَّمٰوَاتِ وَمَا فِي الْأَرْضِ", "en": "To Him belongs whatever is\nin the heavens and earth.",       "ref": "2:255c", "surah": 2, "ayah": 255},
        {"ar": "مَن ذَا الَّذِي يَشْفَعُ عِندَهُ إِلَّا بِإِذْنِهِ", "en": "Who is it that can intercede\nwith Him except by His permission?", "ref": "2:255d", "surah": 2, "ayah": 255},
        {"ar": "يَعْلَمُ مَا بَيْنَ أَيْدِيهِمْ وَمَا خَلْفَهُمْ", "en": "He knows what is before them\nand what is behind them.",        "ref": "2:255e", "surah": 2, "ayah": 255},
        {"ar": "وَلَا يُحِيطُونَ بِشَيْءٍ مِّنْ عِلْمِهِ إِلَّا بِمَا شَاءَ", "en": "And they encompass nothing\nof His knowledge except what He wills.", "ref": "2:255f", "surah": 2, "ayah": 255},
        {"ar": "وَسِعَ كُرْسِيُّهُ السَّمٰوَاتِ وَالْأَرْضَ", "en": "His Throne extends over\nthe heavens and the earth.",          "ref": "2:255g", "surah": 2, "ayah": 255},
        {"ar": "وَلَا يَئُودُهُ حِفْظُهُمَا وَهُوَ الْعَلِيُّ الْعَظِيمُ", "en": "And their preservation does not tire Him.\nHe is the Most High, the Most Great.", "ref": "2:255h", "surah": 2, "ayah": 255},
    ]},

    # 5 ─ Lumière et guidance
    {"title": "Lumière et guidance", "verses": [
        {"ar": "اللّٰهُ نُورُ السَّمٰوَاتِ وَالْأَرْضِ",   "en": "Allah is the Light\nof the heavens and the earth.",              "ref": "24:35a", "surah": 24, "ayah": 35},
        {"ar": "مَثَلُ نُورِهِ كَمِشْكَاةٍ فِيهَا مِصْبَاحٌ", "en": "The example of His light is like\na niche within which is a lamp.",    "ref": "24:35b", "surah": 24, "ayah": 35},
        {"ar": "الْمِصْبَاحُ فِي زُجَاجَةٍ",               "en": "The lamp is within glass.",                                     "ref": "24:35c", "surah": 24, "ayah": 35},
        {"ar": "الزُّجَاجَةُ كَأَنَّهَا كَوْكَبٌ دُرِّيٌّ", "en": "The glass is like a brilliant star.",                           "ref": "24:35d", "surah": 24, "ayah": 35},
        {"ar": "يَهْدِي اللّٰهُ لِنُورِهِ مَن يَشَاءُ",    "en": "Allah guides to His light\nwhom He wills.",                       "ref": "24:35e", "surah": 24, "ayah": 35},
    ]},

    # 6 ─ La création — Sourate Qaf
    {"title": "La grandeur de la création", "verses": [
        {"ar": "أَفَلَمْ يَنظُرُوا إِلَى السَّمَاءِ فَوْقَهُمْ", "en": "Do they not look at the sky above them —", "ref": "50:6a", "surah": 50, "ayah": 6},
        {"ar": "كَيْفَ بَنَيْنَاهَا وَزَيَّنَّاهَا",           "en": "how We have built it\nand adorned it?",                          "ref": "50:6b", "surah": 50, "ayah": 6},
        {"ar": "وَمَا لَهَا مِن فُرُوجٍ",                     "en": "And there are no rifts\nwithin it.",                             "ref": "50:6c", "surah": 50, "ayah": 6},
        {"ar": "وَالْأَرْضَ مَدَدْنَاهَا وَأَلْقَيْنَا فِيهَا رَوَاسِيَ", "en": "And the earth — We spread it out\nand cast therein firmly set mountains.", "ref": "50:7a", "surah": 50, "ayah": 7},
        {"ar": "وَأَنبَتْنَا فِيهَا مِن كُلِّ زَوْجٍ بَهِيجٍ", "en": "And We caused to grow therein\nevery beautiful kind of plant.", "ref": "50:7b", "surah": 50, "ayah": 7},
    ]},

    # 7 ─ La miséricorde divine — Az-Zumar 53
    {"title": "La miséricorde divine", "verses": [
        {"ar": "قُلْ يَا عِبَادِيَ الَّذِينَ أَسْرَفُوا عَلَىٰ أَنفُسِهِمْ", "en": "Say: O My servants who have\ntransgressed against themselves,", "ref": "39:53a", "surah": 39, "ayah": 53},
        {"ar": "لَا تَقْنَطُوا مِن رَّحْمَةِ اللّٰهِ",       "en": "do not despair\nof the mercy of Allah.",                         "ref": "39:53b", "surah": 39, "ayah": 53},
        {"ar": "إِنَّ اللّٰهَ يَغْفِرُ الذُّنُوبَ جَمِيعًا", "en": "Indeed, Allah forgives\nall sins.",                              "ref": "39:53c", "surah": 39, "ayah": 53},
        {"ar": "إِنَّهُ هُوَ الْغَفُورُ الرَّحِيمُ",          "en": "Indeed, it is He who is\nthe Forgiving, the Merciful.",           "ref": "39:53d", "surah": 39, "ayah": 53},
    ]},

    # 8 ─ Al-Falaq — L'aube
    {"title": "Al-Falaq — L'Aube", "verses": [
        {"ar": "قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ",             "en": "Say: I seek refuge\nin the Lord of the daybreak,",               "ref": "113:1", "surah": 113, "ayah": 1},
        {"ar": "مِن شَرِّ مَا خَلَقَ",                       "en": "From the evil\nof what He created,",                           "ref": "113:2", "surah": 113, "ayah": 2},
        {"ar": "وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ",           "en": "And from the evil\nof darkness when it settles,",               "ref": "113:3", "surah": 113, "ayah": 3},
        {"ar": "وَمِن شَرِّ النَّفَّاثَاتِ فِي الْعُقَدِ",   "en": "And from the evil\nof those who blow on knots,",                "ref": "113:4", "surah": 113, "ayah": 4},
        {"ar": "وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ",           "en": "And from the evil\nof an envier when he envies.",               "ref": "113:5", "surah": 113, "ayah": 5},
    ]},

    # 9 ─ An-Nas — Les hommes
    {"title": "An-Nas — Les Hommes", "verses": [
        {"ar": "قُلْ أَعُوذُ بِرَبِّ النَّاسِ",              "en": "Say: I seek refuge\nin the Lord of mankind,",                    "ref": "114:1", "surah": 114, "ayah": 1},
        {"ar": "مَلِكِ النَّاسِ",                             "en": "The Sovereign of mankind,",                                     "ref": "114:2", "surah": 114, "ayah": 2},
        {"ar": "إِلٰهِ النَّاسِ",                             "en": "The God of mankind,",                                           "ref": "114:3", "surah": 114, "ayah": 3},
        {"ar": "مِن شَرِّ الْوَسْوَاسِ الْخَنَّاسِ",         "en": "From the evil\nof the retreating whisperer,",                   "ref": "114:4", "surah": 114, "ayah": 4},
        {"ar": "الَّذِي يُوَسْوِسُ فِي صُدُورِ النَّاسِ",    "en": "Who whispers in the hearts\nof mankind,",                       "ref": "114:5", "surah": 114, "ayah": 5},
        {"ar": "مِنَ الْجِنَّةِ وَالنَّاسِ",                 "en": "From among the jinn\nand mankind.",                             "ref": "114:6", "surah": 114, "ayah": 6},
    ]},

    # 10 ─ La gratitude — Ibrahim 7
    {"title": "La gratitude", "verses": [
        {"ar": "وَإِذْ تَأَذَّنَ رَبُّكُمْ",                 "en": "And when your Lord proclaimed:",                                 "ref": "14:7a", "surah": 14, "ayah": 7},
        {"ar": "لَئِن شَكَرْتُمْ لَأَزِيدَنَّكُمْ",         "en": "If you are grateful,\nI will surely increase you in favor.",    "ref": "14:7b", "surah": 14, "ayah": 7},
        {"ar": "وَلَئِن كَفَرْتُمْ إِنَّ عَذَابِي لَشَدِيدٌ", "en": "But if you deny,\nindeed, My punishment is severe.", "ref": "14:7c", "surah": 14, "ayah": 7},
        {"ar": "فَإِنَّ اللّٰهَ لَغَنِيٌّ حَمِيدٌ",         "en": "Indeed, Allah is Free of need\nand Praiseworthy.",               "ref": "14:8b", "surah": 14, "ayah": 8},
    ]},

    # 11 ─ Al-Mulk — La Royauté
    {"title": "Al-Mulk — La Royauté", "verses": [
        {"ar": "تَبَارَكَ الَّذِي بِيَدِهِ الْمُلْكُ وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "en": "Blessed is He in whose hand is dominion,\nand He is over all things competent.", "ref": "67:1", "surah": 67, "ayah": 1},
        {"ar": "الَّذِي خَلَقَ الْمَوْتَ وَالْحَيَاةَ",     "en": "He who created death\nand life to test you —",                   "ref": "67:2a", "surah": 67, "ayah": 2},
        {"ar": "لِيَبْلُوَكُمْ أَيُّكُمْ أَحْسَنُ عَمَلًا", "en": "which of you is best in deed.",                                  "ref": "67:2b", "surah": 67, "ayah": 2},
        {"ar": "وَهُوَ الْعَزِيزُ الْغَفُورُ",               "en": "And He is the Exalted in Might,\nthe Forgiving.",               "ref": "67:2c", "surah": 67, "ayah": 2},
        {"ar": "الَّذِي خَلَقَ سَبْعَ سَمٰوَاتٍ طِبَاقًا",  "en": "He who created seven heavens\nin layers.",                       "ref": "67:3a", "surah": 67, "ayah": 3},
        {"ar": "مَّا تَرَىٰ فِي خَلْقِ الرَّحْمٰنِ مِن تَفَاوُتٍ", "en": "You do not see in the creation\nof the Most Merciful any inconsistency.", "ref": "67:3b", "surah": 67, "ayah": 3},
    ]},

    # 12 ─ Al-Baqarah 286 — Le pardon
    {"title": "Le pardon et la miséricorde", "verses": [
        {"ar": "لَا يُكَلِّفُ اللّٰهُ نَفْسًا إِلَّا وُسْعَهَا", "en": "Allah does not burden a soul\nbeyond that it can bear.", "ref": "2:286a", "surah": 2, "ayah": 286},
        {"ar": "رَبَّنَا لَا تُؤَاخِذْنَا إِن نَّسِينَا أَوْ أَخْطَأْنَا", "en": "Our Lord, do not impose blame on us\nif we have forgotten or erred.", "ref": "2:286b", "surah": 2, "ayah": 286},
        {"ar": "رَبَّنَا وَلَا تَحْمِلْ عَلَيْنَا إِصْرًا",    "en": "Our Lord, and lay not upon us\na burden like that You laid upon those before us.", "ref": "2:286c", "surah": 2, "ayah": 286},
        {"ar": "رَبَّنَا وَلَا تُحَمِّلْنَا مَا لَا طَاقَةَ لَنَا بِهِ", "en": "Our Lord, and burden us not\nwith that which we have no ability to bear.", "ref": "2:286d", "surah": 2, "ayah": 286},
        {"ar": "وَاعْفُ عَنَّا وَاغْفِرْ لَنَا وَارْحَمْنَا", "en": "And pardon us,\nforgive us, and have mercy upon us.",           "ref": "2:286e", "surah": 2, "ayah": 286},
        {"ar": "أَنتَ مَوْلَانَا فَانصُرْنَا عَلَى الْقَوْمِ الْكَافِرِينَ", "en": "You are our protector,\nso give us victory over the disbelieving people.", "ref": "2:286f", "surah": 2, "ayah": 286},
    ]},

    # 13 ─ Rappel du Seigneur — Ar-Ra'd 28
    {"title": "La paix du cœur", "verses": [
        {"ar": "الَّذِينَ آمَنُوا وَتَطْمَئِنُّ قُلُوبُهُم بِذِكْرِ اللّٰهِ", "en": "Those who believe and whose hearts\nare assured by the remembrance of Allah.", "ref": "13:28a", "surah": 13, "ayah": 28},
        {"ar": "أَلَا بِذِكْرِ اللّٰهِ تَطْمَئِنُّ الْقُلُوبُ", "en": "Unquestionably, by the remembrance\nof Allah, hearts are assured.", "ref": "13:28b", "surah": 13, "ayah": 28},
        {"ar": "الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ",   "en": "Those who believed\nand did righteous deeds —",                  "ref": "13:29a", "surah": 13, "ayah": 29},
        {"ar": "طُوبَىٰ لَهُمْ وَحُسْنُ مَآبٍ",               "en": "Happiness is for them\nand a beautiful place of return.",          "ref": "13:29b", "surah": 13, "ayah": 29},
    ]},

    # 14 ─ Yusuf 87 — Ne pas désespérer
    {"title": "Ne jamais désespérer", "verses": [
        {"ar": "يَا بَنِيَّ اذْهَبُوا فَتَحَسَّسُوا مِن يُوسُفَ وَأَخِيهِ", "en": "O my sons, go and search\nfor Joseph and his brother,", "ref": "12:87a", "surah": 12, "ayah": 87},
        {"ar": "وَلَا تَيْأَسُوا مِن رَّوْحِ اللّٰهِ", "en": "and do not despair\nof relief from Allah.", "ref": "12:87b", "surah": 12, "ayah": 87},
        {"ar": "إِنَّهُ لَا يَيْأَسُ مِن رَّوْحِ اللّٰهِ إِلَّا الْقَوْمُ الْكَافِرُونَ", "en": "Indeed, no one despairs\nof relief from Allah except\nthe disbelieving people.", "ref": "12:87c", "surah": 12, "ayah": 87},
    ]},

    # 15 ─ Al-Baqarah 153 — Patience et prière
    {"title": "La patience et la prière", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ", "en": "O you who have believed,\nseek help through patience\nand prayer.", "ref": "2:153a", "surah": 2, "ayah": 153},
        {"ar": "إِنَّ اللّٰهَ مَعَ الصَّابِرِينَ", "en": "Indeed, Allah is with\nthe patient.", "ref": "2:153b", "surah": 2, "ayah": 153},
    ]},

    # 16 ─ Al-Hajj 46 — Le cœur qui voit
    {"title": "Le cœur qui comprend", "verses": [
        {"ar": "أَفَلَمْ يَسِيرُوا فِي الْأَرْضِ", "en": "Have they not traveled\nthrough the land?", "ref": "22:46a", "surah": 22, "ayah": 46},
        {"ar": "فَتَكُونَ لَهُمْ قُلُوبٌ يَعْقِلُونَ بِهَا", "en": "So that their hearts\nmay reason with it,", "ref": "22:46b", "surah": 22, "ayah": 46},
        {"ar": "فَإِنَّهَا لَا تَعْمَى الْأَبْصَارُ", "en": "For indeed, it is not the eyes\nthat are blinded,", "ref": "22:46c", "surah": 22, "ayah": 46},
        {"ar": "وَلَٰكِن تَعْمَى الْقُلُوبُ الَّتِي فِي الصُّدُورِ", "en": "But it is the hearts,\nwhich are in the chests,\nthat are blinded.", "ref": "22:46d", "surah": 22, "ayah": 46},
    ]},

    # 17 ─ Al-Imran 173 — La confiance absolue
    {"title": "Hasbunallah", "verses": [
        {"ar": "الَّذِينَ قَالَ لَهُمُ النَّاسُ إِنَّ النَّاسَ قَدْ جَمَعُوا لَكُمْ", "en": "Those to whom people said:\nthe people have gathered\nagainst you,", "ref": "3:173a", "surah": 3, "ayah": 173},
        {"ar": "فَاخْشَوْهُمْ فَزَادَهُمْ إِيمَانًا", "en": "So fear them —\nbut it only increased them\nin faith,", "ref": "3:173b", "surah": 3, "ayah": 173},
        {"ar": "وَقَالُوا حَسْبُنَا اللّٰهُ وَنِعْمَ الْوَكِيلُ", "en": "And they said:\nAllah is sufficient for us,\nand He is the best disposer.", "ref": "3:173c", "surah": 3, "ayah": 173},
    ]},

    # 18 ─ Az-Zumar 9 — La science et l'adoration
    {"title": "Savoir et se prosterner", "verses": [
        {"ar": "أَمَّنْ هُوَ قَانِتٌ آنَاءَ اللَّيْلِ سَاجِدًا وَقَائِمًا", "en": "Is one who is devout in hours\nof the night, prostrating\nand standing in prayer,", "ref": "39:9a", "surah": 39, "ayah": 9},
        {"ar": "يَحْذَرُ الْآخِرَةَ وَيَرْجُو رَحْمَةَ رَبِّهِ", "en": "Fearing the Hereafter\nand hoping for the mercy\nof his Lord?", "ref": "39:9b", "surah": 39, "ayah": 9},
        {"ar": "قُلْ هَلْ يَسْتَوِي الَّذِينَ يَعْلَمُونَ وَالَّذِينَ لَا يَعْلَمُونَ", "en": "Say: Are those who know\nequal to those who do not know?", "ref": "39:9c", "surah": 39, "ayah": 9},
    ]},

    # 19 ─ Al-Imran 8 — Ne pas faire dévier les cœurs
    {"title": "Affermir les cœurs", "verses": [
        {"ar": "رَبَّنَا لَا تُزِغْ قُلُوبَنَا بَعْدَ إِذْ هَدَيْتَنَا", "en": "Our Lord, do not let\nour hearts deviate after\nYou have guided us,", "ref": "3:8a", "surah": 3, "ayah": 8},
        {"ar": "وَهَبْ لَنَا مِن لَّدُنكَ رَحْمَةً", "en": "And grant us from Yourself\nmercy.", "ref": "3:8b", "surah": 3, "ayah": 8},
        {"ar": "إِنَّكَ أَنتَ الْوَهَّابُ", "en": "Indeed, You are the Bestower.", "ref": "3:8c", "surah": 3, "ayah": 8},
    ]},

    # 20 ─ Al-Muzzammil 8 — Invoquer et se confier
    {"title": "Se tourner vers Allah", "verses": [
        {"ar": "وَاذْكُرِ اسْمَ رَبِّكَ وَتَبَتَّلْ إِلَيْهِ تَبْتِيلًا", "en": "And remember the name\nof your Lord and devote yourself\nto Him with complete devotion.", "ref": "73:8", "surah": 73, "ayah": 8},
        {"ar": "رَّبُّ الْمَشْرِقِ وَالْمَغْرِبِ لَا إِلَٰهَ إِلَّا هُوَ", "en": "Lord of the East and the West —\nthere is no deity except Him,", "ref": "73:9a", "surah": 73, "ayah": 9},
        {"ar": "فَاتَّخِذْهُ وَكِيلًا", "en": "So take Him as Disposer\nof your affairs.", "ref": "73:9b", "surah": 73, "ayah": 9},
    ]},

    # 21 ─ Al-Baqarah 186 — Allah répond
    {"title": "Allah entend ta prière", "verses": [
        {"ar": "وَإِذَا سَأَلَكَ عِبَادِي عَنِّي فَإِنِّي قَرِيبٌ", "en": "And when My servants ask you\nabout Me — indeed I am near.", "ref": "2:186a", "surah": 2, "ayah": 186},
        {"ar": "أُجِيبُ دَعْوَةَ الدَّاعِ إِذَا دَعَانِ", "en": "I respond to the invocation\nof the supplicant when he calls Me.", "ref": "2:186b", "surah": 2, "ayah": 186},
        {"ar": "فَلْيَسْتَجِيبُوا لِي وَلْيُؤْمِنُوا بِي", "en": "So let them respond to Me\nand believe in Me,", "ref": "2:186c", "surah": 2, "ayah": 186},
        {"ar": "لَعَلَّهُمْ يَرْشُدُونَ", "en": "That they may be guided.", "ref": "2:186d", "surah": 2, "ayah": 186},
    ]},

    # 22 ─ Fussilat 30 — Les anges descendent
    {"title": "Les anges et les croyants", "verses": [
        {"ar": "إِنَّ الَّذِينَ قَالُوا رَبُّنَا اللّٰهُ ثُمَّ اسْتَقَامُوا", "en": "Indeed, those who said\nour Lord is Allah and then\nstayed on course —", "ref": "41:30a", "surah": 41, "ayah": 30},
        {"ar": "تَتَنَزَّلُ عَلَيْهِمُ الْمَلَائِكَةُ", "en": "The angels will descend\nupon them,", "ref": "41:30b", "surah": 41, "ayah": 30},
        {"ar": "أَلَّا تَخَافُوا وَلَا تَحْزَنُوا", "en": "Saying: do not fear\nand do not grieve,", "ref": "41:30c", "surah": 41, "ayah": 30},
        {"ar": "وَأَبْشِرُوا بِالْجَنَّةِ الَّتِي كُنتُمْ تُوعَدُونَ", "en": "But receive good tidings\nof Paradise which you\nwere promised.", "ref": "41:30d", "surah": 41, "ayah": 30},
    ]},

    # 23 ─ Al-Hashr 22-23 — Les noms d'Allah
    {"title": "Les beaux noms d'Allah", "verses": [
        {"ar": "هُوَ اللّٰهُ الَّذِي لَا إِلَٰهَ إِلَّا هُوَ", "en": "He is Allah — there is no deity\nexcept Him,", "ref": "59:22a", "surah": 59, "ayah": 22},
        {"ar": "عَالِمُ الْغَيْبِ وَالشَّهَادَةِ", "en": "Knower of the unseen\nand the witnessed.", "ref": "59:22b", "surah": 59, "ayah": 22},
        {"ar": "هُوَ الرَّحْمَٰنُ الرَّحِيمُ", "en": "He is the Most Gracious,\nthe Most Merciful.", "ref": "59:22c", "surah": 59, "ayah": 22},
        {"ar": "هُوَ اللّٰهُ الَّذِي لَا إِلَٰهَ إِلَّا هُوَ الْمَلِكُ الْقُدُّوسُ السَّلَامُ", "en": "He is Allah — no deity except Him,\nthe Sovereign, the Pure,\nthe Perfection.", "ref": "59:23a", "surah": 59, "ayah": 23},
        {"ar": "الْمُؤْمِنُ الْمُهَيْمِنُ الْعَزِيزُ الْجَبَّارُ الْمُتَكَبِّرُ", "en": "The Grantor of security,\nthe Overseer, the Exalted,\nthe Compeller, the Superior.", "ref": "59:23b", "surah": 59, "ayah": 23},
    ]},

    # 24 ─ Al-Duha — Le matin
    {"title": "Al-Duha — Le Matin", "verses": [
        {"ar": "وَالضُّحَىٰ", "en": "By the morning brightness,", "ref": "93:1", "surah": 93, "ayah": 1},
        {"ar": "وَاللَّيْلِ إِذَا سَجَىٰ", "en": "And by the night when it covers with darkness,", "ref": "93:2", "surah": 93, "ayah": 2},
        {"ar": "مَا وَدَّعَكَ رَبُّكَ وَمَا قَلَىٰ", "en": "Your Lord has not taken leave of you,\nnor has He detested you.", "ref": "93:3", "surah": 93, "ayah": 3},
        {"ar": "وَلَلْآخِرَةُ خَيْرٌ لَّكَ مِنَ الْأُولَىٰ", "en": "And the Hereafter is better for you\nthan the first life.", "ref": "93:4", "surah": 93, "ayah": 4},
        {"ar": "وَلَسَوْفَ يُعْطِيكَ رَبُّكَ فَتَرْضَىٰ", "en": "And your Lord is going to give you,\nand you will be satisfied.", "ref": "93:5", "surah": 93, "ayah": 5},
        {"ar": "أَلَمْ يَجِدْكَ يَتِيمًا فَآوَىٰ", "en": "Did He not find you an orphan\nand give refuge?", "ref": "93:6", "surah": 93, "ayah": 6},
        {"ar": "وَوَجَدَكَ ضَالًّا فَهَدَىٰ", "en": "And He found you lost\nand guided you,", "ref": "93:7", "surah": 93, "ayah": 7},
        {"ar": "وَوَجَدَكَ عَائِلًا فَأَغْنَىٰ", "en": "And He found you poor\nand made you self-sufficient.", "ref": "93:8", "surah": 93, "ayah": 8},
    ]},

    # 25 ─ Al-Kahf 10 — La caverne
    {"title": "Réfuge et guidance", "verses": [
        {"ar": "إِذْ أَوَى الْفِتْيَةُ إِلَى الْكَهْفِ فَقَالُوا", "en": "When the youths retreated\nto the cave and said:", "ref": "18:10a", "surah": 18, "ayah": 10},
        {"ar": "رَبَّنَا آتِنَا مِن لَّدُنكَ رَحْمَةً", "en": "Our Lord, grant us\nfrom Yourself mercy,", "ref": "18:10b", "surah": 18, "ayah": 10},
        {"ar": "وَهَيِّئْ لَنَا مِنْ أَمْرِنَا رَشَدًا", "en": "And prepare for us\nfrom our affair right guidance.", "ref": "18:10c", "surah": 18, "ayah": 10},
    ]},

    # 26 ─ Al-Zilzalah — Le Séisme
    {"title": "Al-Zilzalah — Le Séisme", "verses": [
        {"ar": "إِذَا زُلْزِلَتِ الْأَرْضُ زِلْزَالَهَا", "en": "When the earth is shaken\nwith its final earthquake,", "ref": "99:1", "surah": 99, "ayah": 1},
        {"ar": "وَأَخْرَجَتِ الْأَرْضُ أَثْقَالَهَا", "en": "And the earth brings out\nits burdens,", "ref": "99:2", "surah": 99, "ayah": 2},
        {"ar": "وَقَالَ الْإِنسَانُ مَا لَهَا", "en": "And man says:\nwhat is wrong with it?", "ref": "99:3", "surah": 99, "ayah": 3},
        {"ar": "يَوْمَئِذٍ تُحَدِّثُ أَخْبَارَهَا", "en": "That day, it will report\nits news,", "ref": "99:4", "surah": 99, "ayah": 4},
        {"ar": "بِأَنَّ رَبَّكَ أَوْحَىٰ لَهَا", "en": "Because your Lord\nhas inspired it.", "ref": "99:5", "surah": 99, "ayah": 5},
        {"ar": "يَوْمَئِذٍ يَصْدُرُ النَّاسُ أَشْتَاتًا لِّيُرَوْا أَعْمَالَهُمْ", "en": "That day, the people will depart\nseparated to be shown\nthe result of their deeds.", "ref": "99:6", "surah": 99, "ayah": 6},
        {"ar": "فَمَن يَعْمَلْ مِثْقَالَ ذَرَّةٍ خَيْرًا يَرَهُ", "en": "Whoever does an atom's weight\nof good will see it,", "ref": "99:7", "surah": 99, "ayah": 7},
        {"ar": "وَمَن يَعْمَلْ مِثْقَالَ ذَرَّةٍ شَرًّا يَرَهُ", "en": "And whoever does an atom's weight\nof evil will see it.", "ref": "99:8", "surah": 99, "ayah": 8},
    ]},

    # 27 ─ Al-Asr — Le Temps
    {"title": "Al-Asr — Le Temps", "verses": [
        {"ar": "وَالْعَصْرِ", "en": "By time,", "ref": "103:1", "surah": 103, "ayah": 1},
        {"ar": "إِنَّ الْإِنسَانَ لَفِي خُسْرٍ", "en": "Indeed, mankind is in loss,", "ref": "103:2", "surah": 103, "ayah": 2},
        {"ar": "إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ", "en": "Except for those who have believed\nand done righteous deeds,", "ref": "103:3", "surah": 103, "ayah": 3},
        {"ar": "وَتَوَاصَوْا بِالْحَقِّ وَتَوَاصَوْا بِالصَّبْرِ", "en": "And advised each other to truth\nand advised each other to patience.", "ref": "103:3b", "surah": 103, "ayah": 3},
    ]},

    # 28 ─ Al-Qadr — La Nuit du Destin
    {"title": "Laylat Al-Qadr", "verses": [
        {"ar": "إِنَّا أَنزَلْنَاهُ فِي لَيْلَةِ الْقَدْرِ", "en": "Indeed, We sent it down\nduring the Night of Decree.", "ref": "97:1", "surah": 97, "ayah": 1},
        {"ar": "وَمَا أَدْرَاكَ مَا لَيْلَةُ الْقَدْرِ", "en": "And what can make you know\nwhat is the Night of Decree?", "ref": "97:2", "surah": 97, "ayah": 2},
        {"ar": "لَيْلَةُ الْقَدْرِ خَيْرٌ مِّنْ أَلْفِ شَهْرٍ", "en": "The Night of Decree is better\nthan a thousand months.", "ref": "97:3", "surah": 97, "ayah": 3},
        {"ar": "تَنَزَّلُ الْمَلَائِكَةُ وَالرُّوحُ فِيهَا بِإِذْنِ رَبِّهِم", "en": "The angels and the Spirit descend\ntherein by permission of their Lord.", "ref": "97:4", "surah": 97, "ayah": 4},
        {"ar": "سَلَامٌ هِيَ حَتَّىٰ مَطْلَعِ الْفَجْرِ", "en": "Peace it is until\nthe emergence of dawn.", "ref": "97:5", "surah": 97, "ayah": 5},
    ]},

    # 29 ─ Ar-Rahman — Le Bienfaiteur (55:1-13, consécutifs)
    {"title": "Ar-Rahman — Le Bienfaiteur", "verses": [
        {"ar": "الرَّحْمَٰنُ", "en": "The Most Merciful", "ref": "55:1", "surah": 55, "ayah": 1},
        {"ar": "عَلَّمَ الْقُرْآنَ", "en": "Taught the Qur'an,", "ref": "55:2", "surah": 55, "ayah": 2},
        {"ar": "خَلَقَ الْإِنسَانَ", "en": "Created man,", "ref": "55:3", "surah": 55, "ayah": 3},
        {"ar": "عَلَّمَهُ الْبَيَانَ", "en": "Taught him eloquence.", "ref": "55:4", "surah": 55, "ayah": 4},
        {"ar": "الشَّمْسُ وَالْقَمَرُ بِحُسْبَانٍ", "en": "The sun and the moon\nrun on precise courses.", "ref": "55:5", "surah": 55, "ayah": 5},
        {"ar": "وَالنَّجْمُ وَالشَّجَرُ يَسْجُدَانِ", "en": "And the stars and trees\nprostrate themselves.", "ref": "55:6", "surah": 55, "ayah": 6},
        {"ar": "وَالسَّمَاءَ رَفَعَهَا وَوَضَعَ الْمِيزَانَ", "en": "And the sky He raised\nand He set the balance.", "ref": "55:7", "surah": 55, "ayah": 7},
        {"ar": "أَلَّا تَطْغَوْا فِي الْمِيزَانِ", "en": "That you do not transgress\nthe balance.", "ref": "55:8", "surah": 55, "ayah": 8},
        {"ar": "وَأَقِيمُوا الْوَزْنَ بِالْقِسْطِ وَلَا تُخْسِرُوا الْمِيزَانَ", "en": "And establish weight in justice\nand do not make deficient the balance.", "ref": "55:9", "surah": 55, "ayah": 9},
        {"ar": "وَالْأَرْضَ وَضَعَهَا لِلْأَنَامِ", "en": "And the earth He laid\nfor the creatures.", "ref": "55:10", "surah": 55, "ayah": 10},
        {"ar": "فِيهَا فَاكِهَةٌ وَالنَّخْلُ ذَاتُ الْأَكْمَامِ", "en": "Therein is fruit\nand palm trees with sheaths,", "ref": "55:11", "surah": 55, "ayah": 11},
        {"ar": "وَالْحَبُّ ذُو الْعَصْفِ وَالرَّيْحَانُ", "en": "And grain with husks\nand fragrant plants.", "ref": "55:12", "surah": 55, "ayah": 12},
        {"ar": "فَبِأَيِّ آلَاءِ رَبِّكُمَا تُكَذِّبَانِ", "en": "So which of the favors\nof your Lord would you deny?", "ref": "55:13", "surah": 55, "ayah": 13},
    ]},

    # 30 ─ Al-Insan — La générosité des croyants
    {"title": "La générosité sincère", "verses": [
        {"ar": "وَيُطْعِمُونَ الطَّعَامَ عَلَىٰ حُبِّهِ مِسْكِينًا وَيَتِيمًا وَأَسِيرًا", "en": "And they give food, in spite of love for it,\nto the needy, the orphan, and the captive,", "ref": "76:8", "surah": 76, "ayah": 8},
        {"ar": "إِنَّمَا نُطْعِمُكُمْ لِوَجْهِ اللّٰهِ", "en": "Saying: we feed you\nonly for the countenance of Allah.", "ref": "76:9a", "surah": 76, "ayah": 9},
        {"ar": "لَا نُرِيدُ مِنكُمْ جَزَاءً وَلَا شُكُورًا", "en": "We wish not from you\nreward or gratitude.", "ref": "76:9b", "surah": 76, "ayah": 9},
        {"ar": "إِنَّا نَخَافُ مِن رَّبِّنَا يَوْمًا عَبُوسًا قَمْطَرِيرًا", "en": "Indeed, we fear from our Lord\na Day austere and distressful.", "ref": "76:10", "surah": 76, "ayah": 10},
    ]},

    # 31 ─ Al-Baqarah 45-46 — La patience et la salat
    {"title": "La salat, lien avec Allah", "verses": [
        {"ar": "وَاسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ", "en": "And seek help through\npatience and prayer.", "ref": "2:45a", "surah": 2, "ayah": 45},
        {"ar": "وَإِنَّهَا لَكَبِيرَةٌ إِلَّا عَلَى الْخَاشِعِينَ", "en": "And indeed it is difficult\nexcept for the humbly submissive.", "ref": "2:45b", "surah": 2, "ayah": 45},
        {"ar": "الَّذِينَ يَظُنُّونَ أَنَّهُم مُّلَاقُو رَبِّهِمْ", "en": "Who are certain that they\nwill meet their Lord,", "ref": "2:46a", "surah": 2, "ayah": 46},
        {"ar": "وَأَنَّهُمْ إِلَيْهِ رَاجِعُونَ", "en": "And that they will\nreturn to Him.", "ref": "2:46b", "surah": 2, "ayah": 46},
    ]},

    # 32 ─ Ibrahim 24-25 — La bonne parole
    {"title": "La bonne parole", "verses": [
        {"ar": "أَلَمْ تَرَ كَيْفَ ضَرَبَ اللّٰهُ مَثَلًا كَلِمَةً طَيِّبَةً", "en": "Have you not considered how\nAllah presents an example —\na good word,", "ref": "14:24a", "surah": 14, "ayah": 24},
        {"ar": "كَشَجَرَةٍ طَيِّبَةٍ أَصْلُهَا ثَابِتٌ وَفَرْعُهَا فِي السَّمَاءِ", "en": "Like a good tree,\nwhose root is firmly fixed\nand its branches are toward the sky,", "ref": "14:24b", "surah": 14, "ayah": 24},
        {"ar": "تُؤْتِي أُكُلَهَا كُلَّ حِينٍ بِإِذْنِ رَبِّهَا", "en": "Producing its fruit\nevery season\nby permission of its Lord.", "ref": "14:25a", "surah": 14, "ayah": 25},
        {"ar": "وَيَضْرِبُ اللّٰهُ الْأَمْثَالَ لِلنَّاسِ لَعَلَّهُمْ يَتَذَكَّرُونَ", "en": "And Allah presents examples\nfor the people that perhaps\nthey will be reminded.", "ref": "14:25b", "surah": 14, "ayah": 25},
    ]},

    # 33 ─ Al-Qiyamah — La Résurrection
    {"title": "La Résurrection", "verses": [
        {"ar": "لَا أُقْسِمُ بِيَوْمِ الْقِيَامَةِ", "en": "I swear by the Day\nof Resurrection,", "ref": "75:1", "surah": 75, "ayah": 1},
        {"ar": "وَلَا أُقْسِمُ بِالنَّفْسِ اللَّوَّامَةِ", "en": "And I swear by the\nself-reproaching soul.", "ref": "75:2", "surah": 75, "ayah": 2},
        {"ar": "أَيَحْسَبُ الْإِنسَانُ أَلَّن نَّجْمَعَ عِظَامَهُ", "en": "Does man think that We will not\nassemble his bones?", "ref": "75:3", "surah": 75, "ayah": 3},
        {"ar": "بَلَىٰ قَادِرِينَ عَلَىٰ أَن نُّسَوِّيَ بَنَانَهُ", "en": "Yes, We are able to put\ntogether even his fingertips.", "ref": "75:4", "surah": 75, "ayah": 4},
    ]},

    # 34 ─ Al-Fajr — L'Aurore
    {"title": "Al-Fajr — L'Aurore", "verses": [
        {"ar": "يَا أَيَّتُهَا النَّفْسُ الْمُطْمَئِنَّةُ", "en": "O reassured soul,", "ref": "89:27", "surah": 89, "ayah": 27},
        {"ar": "ارْجِعِي إِلَىٰ رَبِّكِ رَاضِيَةً مَّرْضِيَّةً", "en": "Return to your Lord\nwell-pleased and pleasing to Him,", "ref": "89:28", "surah": 89, "ayah": 28},
        {"ar": "فَادْخُلِي فِي عِبَادِي", "en": "And enter among\nMy servants,", "ref": "89:29", "surah": 89, "ayah": 29},
        {"ar": "وَادْخُلِي جَنَّتِي", "en": "And enter My Paradise.", "ref": "89:30", "surah": 89, "ayah": 30},
    ]},

    # 35 ─ Al-Kawthar — L'Abondance
    {"title": "Al-Kawthar — L'Abondance", "verses": [
        {"ar": "إِنَّا أَعْطَيْنَاكَ الْكَوْثَرَ", "en": "Indeed, We have granted you\nAl-Kawthar.", "ref": "108:1", "surah": 108, "ayah": 1},
        {"ar": "فَصَلِّ لِرَبِّكَ وَانْحَرْ", "en": "So pray to your Lord\nand sacrifice.", "ref": "108:2", "surah": 108, "ayah": 2},
        {"ar": "إِنَّ شَانِئَكَ هُوَ الْأَبْتَرُ", "en": "Indeed, your enemy is\nthe one cut off.", "ref": "108:3", "surah": 108, "ayah": 3},
    ]},

    # 36 ─ An-Nasr — Le Secours
    {"title": "An-Nasr — Le Secours", "verses": [
        {"ar": "إِذَا جَاءَ نَصْرُ اللّٰهِ وَالْفَتْحُ", "en": "When the victory of Allah\nhas come and the conquest,", "ref": "110:1", "surah": 110, "ayah": 1},
        {"ar": "وَرَأَيْتَ النَّاسَ يَدْخُلُونَ فِي دِينِ اللّٰهِ أَفْوَاجًا", "en": "And you see the people entering\ninto the religion of Allah in multitudes,", "ref": "110:2", "surah": 110, "ayah": 2},
        {"ar": "فَسَبِّحْ بِحَمْدِ رَبِّكَ وَاسْتَغْفِرْهُ إِنَّهُ كَانَ تَوَّابًا", "en": "Then exalt Him with praise of your Lord\nand ask forgiveness of Him. Indeed, He is ever Accepting of repentance.", "ref": "110:3", "surah": 110, "ayah": 3},
    ]},

    # 37 ─ At-Tin — Le Figuier
    {"title": "At-Tin — Le Figuier", "verses": [
        {"ar": "لَقَدْ خَلَقْنَا الْإِنسَانَ فِي أَحْسَنِ تَقْوِيمٍ", "en": "We have certainly created man\nin the best of stature.", "ref": "95:4", "surah": 95, "ayah": 4},
        {"ar": "ثُمَّ رَدَدْنَاهُ أَسْفَلَ سَافِلِينَ", "en": "Then We return him\nto the lowest of the low,", "ref": "95:5", "surah": 95, "ayah": 5},
        {"ar": "إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ فَلَهُمْ أَجْرٌ غَيْرُ مَمْنُونٍ", "en": "Except for those who believe\nand do righteous deeds — for they\nwill have a reward uninterrupted.", "ref": "95:6", "surah": 95, "ayah": 6},
    ]},

    # 38 ─ Al-Layl 5-7 — Les chemins de la facilité
    {"title": "Les chemins de la facilité", "verses": [
        {"ar": "فَأَمَّا مَنْ أَعْطَىٰ وَاتَّقَىٰ", "en": "As for he who gives\nand fears Allah", "ref": "92:5", "surah": 92, "ayah": 5},
        {"ar": "وَصَدَّقَ بِالْحُسْنَىٰ", "en": "And believes in\nthe best [reward],", "ref": "92:6", "surah": 92, "ayah": 6},
        {"ar": "فَسَنُيَسِّرُهُ لِلْيُسْرَىٰ", "en": "We will ease him\ntoward ease.", "ref": "92:7", "surah": 92, "ayah": 7},
    ]},

    # 39 ─ Al-Baqarah 152 — Le souvenir mutuel
    {"title": "Le souvenir mutuel", "verses": [
        {"ar": "فَاذْكُرُونِي أَذْكُرْكُمْ", "en": "So remember Me;\nI will remember you.", "ref": "2:152a", "surah": 2, "ayah": 152},
        {"ar": "وَاشْكُرُوا لِي وَلَا تَكْفُرُونِ", "en": "And be grateful to Me\nand do not deny Me.", "ref": "2:152b", "surah": 2, "ayah": 152},
    ]},

    # 40 ─ At-Tawbah 51 — Ce qu'Allah a écrit
    {"title": "Ce qu'Allah a écrit pour nous", "verses": [
        {"ar": "قُل لَّن يُصِيبَنَا إِلَّا مَا كَتَبَ اللّٰهُ لَنَا", "en": "Say: Nothing will befall us\nexcept what Allah has decreed for us;", "ref": "9:51a", "surah": 9, "ayah": 51},
        {"ar": "هُوَ مَوْلَانَا وَعَلَى اللّٰهِ فَلْيَتَوَكَّلِ الْمُؤْمِنُونَ", "en": "He is our protector. And upon Allah\nlet the believers rely.", "ref": "9:51b", "surah": 9, "ayah": 51},
    ]},

    # 41 ─ Ar-Ra'd 11 — Allah ne change pas l'état d'un peuple
    {"title": "Le changement vient de soi", "verses": [
        {"ar": "إِنَّ اللّٰهَ لَا يُغَيِّرُ مَا بِقَوْمٍ حَتَّىٰ يُغَيِّرُوا مَا بِأَنفُسِهِمْ", "en": "Indeed, Allah will not change the condition\nof a people until they change\nwhat is in themselves.", "ref": "13:11", "surah": 13, "ayah": 11},
    ]},

    # 42 ─ Al-Baqarah 255 (suite) — complète avec Ayat Al-Kursi déjà faite séparée
    # 42 ─ Al-Anfal 2-4 — Les vrais croyants
    {"title": "Les vrais croyants", "verses": [
        {"ar": "إِنَّمَا الْمُؤْمِنُونَ الَّذِينَ إِذَا ذُكِرَ اللّٰهُ وَجِلَتْ قُلُوبُهُمْ", "en": "The believers are only those who,\nwhen Allah is mentioned,\ntheir hearts become fearful,", "ref": "8:2a", "surah": 8, "ayah": 2},
        {"ar": "وَإِذَا تُلِيَتْ عَلَيْهِمْ آيَاتُهُ زَادَتْهُمْ إِيمَانًا", "en": "And when His verses are recited to them,\nit increases them in faith,", "ref": "8:2b", "surah": 8, "ayah": 2},
        {"ar": "وَعَلَىٰ رَبِّهِمْ يَتَوَكَّلُونَ", "en": "And upon their Lord\nthey rely.", "ref": "8:2c", "surah": 8, "ayah": 2},
        {"ar": "الَّذِينَ يُقِيمُونَ الصَّلَاةَ وَمِمَّا رَزَقْنَاهُمْ يُنفِقُونَ", "en": "Those who establish prayer\nand spend from what We\nhave provided them.", "ref": "8:3", "surah": 8, "ayah": 3},
        {"ar": "أُولَٰئِكَ هُمُ الْمُؤْمِنُونَ حَقًّا", "en": "Those are the believers, truly.", "ref": "8:4a", "surah": 8, "ayah": 4},
        {"ar": "لَّهُمْ دَرَجَاتٌ عِندَ رَبِّهِمْ وَمَغْفِرَةٌ وَرِزْقٌ كَرِيمٌ", "en": "For them are degrees of honor\nwith their Lord, and forgiveness\nand noble provision.", "ref": "8:4b", "surah": 8, "ayah": 4},
    ]},

    # 43 ─ Al-Hujurat 10-13 — La fraternité et l'honneur
    {"title": "La fraternité en Islam", "verses": [
        {"ar": "إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ", "en": "The believers are but brothers,", "ref": "49:10a", "surah": 49, "ayah": 10},
        {"ar": "فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ", "en": "So make peace between\nyour brothers,", "ref": "49:10b", "surah": 49, "ayah": 10},
        {"ar": "وَاتَّقُوا اللّٰهَ لَعَلَّكُمْ تُرْحَمُونَ", "en": "And fear Allah that you may\nreceive mercy.", "ref": "49:10c", "surah": 49, "ayah": 10},
        {"ar": "يَا أَيُّهَا النَّاسُ إِنَّا خَلَقْنَاكُم مِّن ذَكَرٍ وَأُنثَىٰ", "en": "O mankind, indeed We have created you\nfrom male and female,", "ref": "49:13a", "surah": 49, "ayah": 13},
        {"ar": "وَجَعَلْنَاكُمْ شُعُوبًا وَقَبَائِلَ لِتَعَارَفُوا", "en": "And made you peoples and tribes\nthat you may know one another.", "ref": "49:13b", "surah": 49, "ayah": 13},
        {"ar": "إِنَّ أَكْرَمَكُمْ عِندَ اللّٰهِ أَتْقَاكُمْ", "en": "Indeed, the most noble of you\nbefore Allah is the most righteous.", "ref": "49:13c", "surah": 49, "ayah": 13},
    ]},

    # 44 ─ Yunus 62-64 — Les alliés d'Allah
    {"title": "Les alliés d'Allah — Awliya", "verses": [
        {"ar": "أَلَا إِنَّ أَوْلِيَاءَ اللّٰهِ لَا خَوْفٌ عَلَيْهِمْ وَلَا هُمْ يَحْزَنُونَ", "en": "Unquestionably, the allies of Allah —\nthere will be no fear concerning them,\nnor will they grieve.", "ref": "10:62", "surah": 10, "ayah": 62},
        {"ar": "الَّذِينَ آمَنُوا وَكَانُوا يَتَّقُونَ", "en": "Those who believed\nand were fearing Allah.", "ref": "10:63", "surah": 10, "ayah": 63},
        {"ar": "لَهُمُ الْبُشْرَىٰ فِي الْحَيَاةِ الدُّنْيَا وَفِي الْآخِرَةِ", "en": "For them are good tidings\nin worldly life and in the Hereafter.", "ref": "10:64a", "surah": 10, "ayah": 64},
        {"ar": "لَا تَبْدِيلَ لِكَلِمَاتِ اللّٰهِ", "en": "There is no change in the words\nof Allah.", "ref": "10:64b", "surah": 10, "ayah": 64},
    ]},

    # 45 ─ Az-Zumar 23 — Le meilleur des discours
    {"title": "Le Coran, meilleur discours", "verses": [
        {"ar": "اللّٰهُ نَزَّلَ أَحْسَنَ الْحَدِيثِ كِتَابًا مُّتَشَابِهًا مَّثَانِيَ", "en": "Allah has sent down the best statement:\na consistent Book wherein\nis reiteration.", "ref": "39:23a", "surah": 39, "ayah": 23},
        {"ar": "تَقْشَعِرُّ مِنْهُ جُلُودُ الَّذِينَ يَخْشَوْنَ رَبَّهُمْ", "en": "The skins shudder therefrom\nof those who fear their Lord,", "ref": "39:23b", "surah": 39, "ayah": 23},
        {"ar": "ثُمَّ تَلِينُ جُلُودُهُمْ وَقُلُوبُهُمْ إِلَىٰ ذِكْرِ اللّٰهِ", "en": "Then their skins and hearts soften\nto the remembrance of Allah.", "ref": "39:23c", "surah": 39, "ayah": 23},
        {"ar": "ذَٰلِكَ هُدَى اللّٰهِ يَهْدِي بِهِ مَن يَشَاءُ", "en": "That is the guidance of Allah\nby which He guides whom He wills.", "ref": "39:23d", "surah": 39, "ayah": 23},
    ]},

    # 46 ─ Al-Isra 23-24 — Les parents
    {"title": "Le respect des parents", "verses": [
        {"ar": "وَقَضَىٰ رَبُّكَ أَلَّا تَعْبُدُوا إِلَّا إِيَّاهُ", "en": "And your Lord has decreed that you\nnot worship except Him,", "ref": "17:23a", "surah": 17, "ayah": 23},
        {"ar": "وَبِالْوَالِدَيْنِ إِحْسَانًا", "en": "And to parents, good treatment.", "ref": "17:23b", "surah": 17, "ayah": 23},
        {"ar": "إِمَّا يَبْلُغَنَّ عِندَكَ الْكِبَرَ أَحَدُهُمَا أَوْ كِلَاهُمَا", "en": "Whether one or both of them reach old\nage with you,", "ref": "17:23c", "surah": 17, "ayah": 23},
        {"ar": "فَلَا تَقُل لَّهُمَا أُفٍّ وَلَا تَنْهَرْهُمَا", "en": "Do not say to them a word of disrespect\nnor repel them,", "ref": "17:23d", "surah": 17, "ayah": 23},
        {"ar": "وَقُل لَّهُمَا قَوْلًا كَرِيمًا", "en": "But say to them words of\nnoble kindness.", "ref": "17:23e", "surah": 17, "ayah": 23},
        {"ar": "وَاخْفِضْ لَهُمَا جَنَاحَ الذُّلِّ مِنَ الرَّحْمَةِ", "en": "And lower to them the wing\nof humility out of mercy,", "ref": "17:24a", "surah": 17, "ayah": 24},
        {"ar": "وَقُل رَّبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا", "en": "And say: My Lord, have mercy upon them\nas they brought me up when I was small.", "ref": "17:24b", "surah": 17, "ayah": 24},
    ]},

    # 47 ─ Al-Muzzammil 20 — La prière de nuit
    {"title": "La prière de nuit — Tahajjud", "verses": [
        {"ar": "إِنَّ رَبَّكَ يَعْلَمُ أَنَّكَ تَقُومُ أَدْنَىٰ مِن ثُلُثَيِ اللَّيْلِ", "en": "Indeed, your Lord knows that you stand\npraying almost two thirds of the night,", "ref": "73:20a", "surah": 73, "ayah": 20},
        {"ar": "وَنِصْفَهُ وَثُلُثَهُ وَطَائِفَةٌ مِّنَ الَّذِينَ مَعَكَ", "en": "And half of it and a third of it,\nand a group of those with you.", "ref": "73:20b", "surah": 73, "ayah": 20},
        {"ar": "وَأَقِيمُوا الصَّلَاةَ وَآتُوا الزَّكَاةَ", "en": "And establish prayer\nand give Zakah,", "ref": "73:20c", "surah": 73, "ayah": 20},
        {"ar": "وَمَا تُقَدِّمُوا لِأَنفُسِكُم مِّنْ خَيْرٍ تَجِدُوهُ عِندَ اللّٰهِ", "en": "And whatever good you put forward\nfor yourselves — you will find it\nwith Allah.", "ref": "73:20d", "surah": 73, "ayah": 20},
        {"ar": "إِنَّ اللّٰهَ غَفُورٌ رَّحِيمٌ", "en": "Indeed, Allah is Forgiving\nand Merciful.", "ref": "73:20e", "surah": 73, "ayah": 20},
    ]},

    # 48 ─ Al-Baqarah 2-5 — Le Livre sans doute
    {"title": "Le guide des pieux", "verses": [
        {"ar": "ذَٰلِكَ الْكِتَابُ لَا رَيْبَ فِيهِ", "en": "This is the Book about which\nthere is no doubt,", "ref": "2:2a", "surah": 2, "ayah": 2},
        {"ar": "هُدًى لِّلْمُتَّقِينَ", "en": "A guidance for those\nconscious of Allah.", "ref": "2:2b", "surah": 2, "ayah": 2},
        {"ar": "الَّذِينَ يُؤْمِنُونَ بِالْغَيْبِ وَيُقِيمُونَ الصَّلَاةَ", "en": "Who believe in the unseen,\nestablish prayer,", "ref": "2:3a", "surah": 2, "ayah": 3},
        {"ar": "وَمِمَّا رَزَقْنَاهُمْ يُنفِقُونَ", "en": "And spend from what We\nhave provided them.", "ref": "2:3b", "surah": 2, "ayah": 3},
        {"ar": "أُولَٰئِكَ عَلَىٰ هُدًى مِّن رَّبِّهِمْ", "en": "Those are upon guidance\nfrom their Lord,", "ref": "2:5a", "surah": 2, "ayah": 5},
        {"ar": "وَأُولَٰئِكَ هُمُ الْمُفْلِحُونَ", "en": "And it is those who\nare the successful.", "ref": "2:5b", "surah": 2, "ayah": 5},
    ]},

    # 49 ─ Fussilat 33 — La meilleure parole
    {"title": "Appeler vers Allah", "verses": [
        {"ar": "وَمَنْ أَحْسَنُ قَوْلًا مِّمَّن دَعَا إِلَى اللّٰهِ", "en": "And who is better in speech\nthan one who calls to Allah,", "ref": "41:33a", "surah": 41, "ayah": 33},
        {"ar": "وَعَمِلَ صَالِحًا", "en": "And does righteousness,", "ref": "41:33b", "surah": 41, "ayah": 33},
        {"ar": "وَقَالَ إِنَّنِي مِنَ الْمُسْلِمِينَ", "en": "And says: Indeed, I am\nof the Muslims?", "ref": "41:33c", "surah":41, "ayah": 33},
    ]},

    # 50 ─ Al-Imran 185 — Chaque âme goûtera la mort
    {"title": "L'épreuve de ce monde", "verses": [
        {"ar": "كُلُّ نَفْسٍ ذَائِقَةُ الْمَوْتِ", "en": "Every soul will taste death.", "ref": "3:185a", "surah": 3, "ayah": 185},
        {"ar": "وَإِنَّمَا تُوَفَّوْنَ أُجُورَكُمْ يَوْمَ الْقِيَامَةِ", "en": "And you will only be given\nyour full compensation\non the Day of Resurrection.", "ref": "3:185b", "surah": 3, "ayah": 185},
        {"ar": "فَمَن زُحْزِحَ عَنِ النَّارِ وَأُدْخِلَ الْجَنَّةَ فَقَدْ فَازَ", "en": "So whoever is kept away from the Fire\nand admitted to Paradise\nhas attained his desire.", "ref": "3:185c", "surah": 3, "ayah": 185},
        {"ar": "وَمَا الْحَيَاةُ الدُّنْيَا إِلَّا مَتَاعُ الْغُرُورِ", "en": "And what is the life of this world\nexcept the enjoyment of delusion.", "ref": "3:185d", "surah": 3, "ayah": 185},
    ]},

    # 51 ─ Al-Kahf 46 — Les richesses passagères
    {"title": "Les vraies richesses", "verses": [
        {"ar": "الْمَالُ وَالْبَنُونَ زِينَةُ الْحَيَاةِ الدُّنْيَا", "en": "Wealth and children are\nthe adornment of worldly life.", "ref": "18:46a", "surah": 18, "ayah": 46},
        {"ar": "وَالْبَاقِيَاتُ الصَّالِحَاتُ خَيْرٌ عِندَ رَبِّكَ ثَوَابًا", "en": "But the enduring good deeds are better\nto your Lord for reward,", "ref": "18:46b", "surah": 18, "ayah": 46},
        {"ar": "وَخَيْرٌ أَمَلًا", "en": "And better for one's hope.", "ref": "18:46c", "surah": 18, "ayah": 46},
    ]},

    # 52 ─ Al-Imran 26-27 — La souveraineté d'Allah
    {"title": "Allah donne et reprend", "verses": [
        {"ar": "قُلِ اللّٰهُمَّ مَالِكَ الْمُلْكِ", "en": "Say: O Allah, Owner of Sovereignty,", "ref": "3:26a", "surah": 3, "ayah": 26},
        {"ar": "تُؤْتِي الْمُلْكَ مَن تَشَاءُ وَتَنزِعُ الْمُلْكَ مِمَّن تَشَاءُ", "en": "You give sovereignty to whom You will\nand You take sovereignty from whom You will.", "ref": "3:26b", "surah": 3, "ayah": 26},
        {"ar": "وَتُعِزُّ مَن تَشَاءُ وَتُذِلُّ مَن تَشَاءُ", "en": "You honor whom You will\nand You humble whom You will.", "ref": "3:26c", "surah": 3, "ayah": 26},
        {"ar": "بِيَدِكَ الْخَيْرُ إِنَّكَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "en": "In Your hand is all good.\nIndeed, You are over all things competent.", "ref": "3:26d", "surah": 3, "ayah": 26},
    ]},

    # 53 ─ Al-Mu'minun 1-11 — Les croyants qui réussissent
    {"title": "Les croyants qui réussissent", "verses": [
        {"ar": "قَدْ أَفْلَحَ الْمُؤْمِنُونَ", "en": "Certainly will the believers\nhave succeeded:", "ref": "23:1", "surah": 23, "ayah": 1},
        {"ar": "الَّذِينَ هُمْ فِي صَلَاتِهِمْ خَاشِعُونَ", "en": "They who are during their prayer\nhumbly submissive,", "ref": "23:2", "surah": 23, "ayah": 2},
        {"ar": "وَالَّذِينَ هُمْ عَنِ اللَّغْوِ مُعْرِضُونَ", "en": "And they who turn away\nfrom ill speech,", "ref": "23:3", "surah": 23, "ayah": 3},
        {"ar": "وَالَّذِينَ هُمْ لِلزَّكَاةِ فَاعِلُونَ", "en": "And they who are observant\nof Zakah,", "ref": "23:4", "surah": 23, "ayah": 4},
        {"ar": "أُولَٰئِكَ هُمُ الْوَارِثُونَ", "en": "Those are the inheritors,", "ref": "23:10", "surah": 23, "ayah": 10},
        {"ar": "الَّذِينَ يَرِثُونَ الْفِرْدَوْسَ هُمْ فِيهَا خَالِدُونَ", "en": "Who will inherit al-Firdaus.\nThey will abide therein eternally.", "ref": "23:11", "surah": 23, "ayah": 11},
    ]},

    # 54 ─ Al-Baqarah 163 — L'Unique
    {"title": "Allah, l'Unique", "verses": [
        {"ar": "وَإِلَٰهُكُمْ إِلَٰهٌ وَاحِدٌ", "en": "And your God is one God.", "ref": "2:163a", "surah": 2, "ayah": 163},
        {"ar": "لَّا إِلَٰهَ إِلَّا هُوَ الرَّحْمَٰنُ الرَّحِيمُ", "en": "There is no deity worthy of worship\nexcept Him, the Most Gracious,\nthe Most Merciful.", "ref": "2:163b", "surah": 2, "ayah": 163},
    ]},

    # 55 ─ An-Nahl 97 — La bonne vie
    {"title": "La vie bonne", "verses": [
        {"ar": "مَنْ عَمِلَ صَالِحًا مِّن ذَكَرٍ أَوْ أُنثَىٰ وَهُوَ مُؤْمِنٌ", "en": "Whoever does righteousness,\nwhether male or female,\nwhile being a believer —", "ref": "16:97a", "surah": 16, "ayah": 97},
        {"ar": "فَلَنُحْيِيَنَّهُ حَيَاةً طَيِّبَةً", "en": "We will surely cause him\nto live a good life.", "ref": "16:97b", "surah": 16, "ayah": 97},
        {"ar": "وَلَنَجْزِيَنَّهُمْ أَجْرَهُم بِأَحْسَنِ مَا كَانُوا يَعْمَلُونَ", "en": "And We will surely give them\ntheir reward according to the best\nof what they used to do.", "ref": "16:97c", "surah": 16, "ayah": 97},
    ]},

    # 56 ─ Al-Ahzab 41-43 — Abondance de dhikr
    {"title": "Abondance du dhikr", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا اذْكُرُوا اللّٰهَ ذِكْرًا كَثِيرًا", "en": "O you who have believed,\nremember Allah with much remembrance,", "ref": "33:41", "surah": 33, "ayah": 41},
        {"ar": "وَسَبِّحُوهُ بُكْرَةً وَأَصِيلًا", "en": "And exalt Him morning\nand afternoon.", "ref": "33:42", "surah": 33, "ayah": 42},
        {"ar": "هُوَ الَّذِي يُصَلِّي عَلَيْكُمْ وَمَلَائِكَتُهُ", "en": "It is He who confers blessing upon you,\nand His angels,", "ref": "33:43a", "surah": 33, "ayah": 43},
        {"ar": "لِيُخْرِجَكُم مِّنَ الظُّلُمَاتِ إِلَى النُّورِ", "en": "That He may bring you out\nfrom darkness into the light.", "ref": "33:43b", "surah": 33, "ayah": 43},
        {"ar": "وَكَانَ بِالْمُؤْمِنِينَ رَحِيمًا", "en": "And ever is He, to the believers,\nMerciful.", "ref": "33:43c", "surah": 33, "ayah": 43},
    ]},

    # 57 ─ Ibrahim 40-41 — Dua d'Ibrahim
    {"title": "La prière d'Ibrahim", "verses": [
        {"ar": "رَبِّ اجْعَلْنِي مُقِيمَ الصَّلَاةِ وَمِن ذُرِّيَّتِي", "en": "My Lord, make me an establisher of prayer,\nand my descendants.", "ref": "14:40a", "surah": 14, "ayah": 40},
        {"ar": "رَبَّنَا وَتَقَبَّلْ دُعَاءِ", "en": "Our Lord, and accept my supplication.", "ref": "14:40b", "surah": 14, "ayah": 40},
        {"ar": "رَبَّنَا اغْفِرْ لِي وَلِوَالِدَيَّ وَلِلْمُؤْمِنِينَ", "en": "Our Lord, forgive me\nand my parents and the believers.", "ref": "14:41a", "surah": 14, "ayah": 41},
        {"ar": "يَوْمَ يَقُومُ الْحِسَابُ", "en": "On the Day when the account\nis established.", "ref": "14:41b", "surah": 14, "ayah": 41},
    ]},

    # 58 ─ Al-Ghashiyah — La Déferlante
    {"title": "Al-Ghashiyah — La Déferlante", "verses": [
        {"ar": "وُجُوهٌ يَوْمَئِذٍ خَاشِعَةٌ", "en": "Faces, that Day, will be humbled,", "ref": "88:2", "surah": 88, "ayah": 2},
        {"ar": "وُجُوهٌ يَوْمَئِذٍ نَّاعِمَةٌ", "en": "And faces, that Day, will be in delight,", "ref": "88:8", "surah": 88, "ayah": 8},
        {"ar": "لِّسَعْيِهَا رَاضِيَةٌ", "en": "Satisfied with their effort,", "ref": "88:9", "surah": 88, "ayah": 9},
        {"ar": "فِي جَنَّةٍ عَالِيَةٍ", "en": "In an elevated garden,", "ref": "88:10", "surah": 88, "ayah": 10},
        {"ar": "أَفَلَا يَنظُرُونَ إِلَى الْإِبِلِ كَيْفَ خُلِقَتْ", "en": "Then do they not look at the camels —\nhow they are created?", "ref": "88:17", "surah": 88, "ayah": 17},
        {"ar": "وَإِلَى السَّمَاءِ كَيْفَ رُفِعَتْ", "en": "And at the sky —\nhow it is raised?", "ref": "88:18", "surah": 88, "ayah": 18},
        {"ar": "وَإِلَى الْجِبَالِ كَيْفَ نُصِبَتْ", "en": "And at the mountains —\nhow they are erected?", "ref": "88:19", "surah": 88, "ayah": 19},
        {"ar": "وَإِلَى الْأَرْضِ كَيْفَ سُطِحَتْ", "en": "And at the earth —\nhow it is spread out?", "ref": "88:20", "surah": 88, "ayah": 20},
    ]},

    # 59 ─ Al-Qasas 24 — Dua de Musa
    {"title": "La dua de Musa", "verses": [
        {"ar": "رَبِّ إِنِّي لِمَا أَنزَلْتَ إِلَيَّ مِنْ خَيْرٍ فَقِيرٌ", "en": "My Lord, indeed I am\nfor whatever good You would send down\nto me, in need.", "ref": "28:24", "surah": 28, "ayah": 24},
    ]},

    # 60 ─ Sad 35 — Dua de Sulayman
    {"title": "La dua de Sulayman", "verses": [
        {"ar": "رَبِّ اغْفِرْ لِي وَهَبْ لِي مُلْكًا لَّا يَنبَغِي لِأَحَدٍ مِّن بَعْدِي", "en": "My Lord, forgive me and grant me\na kingdom such as will not belong\nto anyone after me.", "ref": "38:35a", "surah": 38, "ayah": 35},
        {"ar": "إِنَّكَ أَنتَ الْوَهَّابُ", "en": "Indeed, You are the Bestower.", "ref": "38:35b", "surah": 38, "ayah": 35},
    ]},

    # 61 ─ Al-Anbiya 83-84 — Dua d'Ayyoub
    {"title": "La dua d'Ayyoub — patience dans l'épreuve", "verses": [
        {"ar": "وَأَيُّوبَ إِذْ نَادَىٰ رَبَّهُ أَنِّي مَسَّنِيَ الضُّرُّ", "en": "And remember Job, when he called\nto his Lord: Indeed, adversity has touched me,", "ref": "21:83a", "surah": 21, "ayah": 83},
        {"ar": "وَأَنتَ أَرْحَمُ الرَّاحِمِينَ", "en": "And you are the most Merciful\nof the merciful.", "ref": "21:83b", "surah": 21, "ayah": 83},
        {"ar": "فَاسْتَجَبْنَا لَهُ فَكَشَفْنَا مَا بِهِ مِن ضُرٍّ", "en": "So We responded to him\nand removed what afflicted him of adversity.", "ref": "21:84a", "surah": 21, "ayah": 84},
        {"ar": "وَآتَيْنَاهُ أَهْلَهُ وَمِثْلَهُم مَّعَهُمْ رَحْمَةً مِّنْ عِندِنَا", "en": "And We gave back his family\nand the like thereof with them\nas mercy from Us.", "ref": "21:84b", "surah": 21, "ayah": 84},
    ]},

    # 62 ─ Al-Anbiya 87 — Dua de Yunus (Dhul-Nun)
    {"title": "La dua de Yunus — sortir des ténèbres", "verses": [
        {"ar": "وَذَا النُّونِ إِذ ذَّهَبَ مُغَاضِبًا", "en": "And remember the man of the fish,\nwhen he went away in anger,", "ref": "21:87a", "surah": 21, "ayah": 87},
        {"ar": "فَنَادَىٰ فِي الظُّلُمَاتِ أَن لَّا إِلَٰهَ إِلَّا أَنتَ سُبْحَانَكَ", "en": "And called out in the darkness:\nThere is no deity except You;\nexalted are You.", "ref": "21:87b", "surah": 21, "ayah": 87},
        {"ar": "إِنِّي كُنتُ مِنَ الظَّالِمِينَ", "en": "Indeed, I have been\nof the wrongdoers.", "ref": "21:87c", "surah": 21, "ayah": 87},
        {"ar": "فَاسْتَجَبْنَا لَهُ وَنَجَّيْنَاهُ مِنَ الْغَمِّ", "en": "So We responded to him\nand saved him from the distress.", "ref": "21:88a", "surah": 21, "ayah": 88},
        {"ar": "وَكَذَٰلِكَ نُنجِي الْمُؤْمِنِينَ", "en": "And thus do We save\nthe believers.", "ref": "21:88b", "surah": 21, "ayah": 88},
    ]},

    # 63 ─ Al-Baqarah 201 — La meilleure dua
    {"title": "La meilleure dua", "verses": [
        {"ar": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً", "en": "Our Lord, give us in this world\nthat which is good,", "ref": "2:201a", "surah": 2, "ayah": 201},
        {"ar": "وَفِي الْآخِرَةِ حَسَنَةً", "en": "And in the Hereafter\nthat which is good,", "ref": "2:201b", "surah": 2, "ayah": 201},
        {"ar": "وَقِنَا عَذَابَ النَّارِ", "en": "And protect us from\nthe punishment of the Fire.", "ref": "2:201c", "surah": 2, "ayah": 201},
    ]},

    # 64 ─ Al-Furqan 63-76 — Les serviteurs du Tout-Miséricordieux
    {"title": "Les serviteurs du Miséricordieux", "verses": [
        {"ar": "وَعِبَادُ الرَّحْمَٰنِ الَّذِينَ يَمْشُونَ عَلَى الْأَرْضِ هَوْنًا", "en": "And the servants of the Most Merciful\nare those who walk upon the earth easily,", "ref": "25:63a", "surah": 25, "ayah": 63},
        {"ar": "وَإِذَا خَاطَبَهُمُ الْجَاهِلُونَ قَالُوا سَلَامًا", "en": "And when the ignorant address them\nharshly, they say words of peace.", "ref": "25:63b", "surah": 25, "ayah": 63},
        {"ar": "وَالَّذِينَ يَبِيتُونَ لِرَبِّهِمْ سُجَّدًا وَقِيَامًا", "en": "And those who spend the night\nfor their Lord prostrating\nand standing in prayer.", "ref": "25:64", "surah": 25, "ayah": 64},
        {"ar": "وَالَّذِينَ يَقُولُونَ رَبَّنَا اصْرِفْ عَنَّا عَذَابَ جَهَنَّمَ", "en": "And those who say:\nOur Lord, avert from us\nthe punishment of Hell.", "ref": "25:65a", "surah": 25, "ayah": 65},
        {"ar": "إِنَّ عَذَابَهَا كَانَ غَرَامًا", "en": "Indeed, its punishment is\na calamity.", "ref": "25:65b", "surah": 25, "ayah": 65},
    ]},

    # 65 ─ Al-Anfal 45-46 — Steadfastness
    {"title": "La fermeté au combat", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا إِذَا لَقِيتُمْ فِئَةً فَاثْبُتُوا", "en": "O you who have believed,\nwhen you encounter a company,\nstand firm.", "ref": "8:45a", "surah": 8, "ayah": 45},
        {"ar": "وَاذْكُرُوا اللّٰهَ كَثِيرًا لَّعَلَّكُمْ تُفْلِحُونَ", "en": "And remember Allah much\nthat you may be successful.", "ref": "8:45b", "surah": 8, "ayah": 45},
        {"ar": "وَأَطِيعُوا اللّٰهَ وَرَسُولَهُ وَلَا تَنَازَعُوا فَتَفْشَلُوا", "en": "And obey Allah and His messenger\nand do not dispute,\nlest you fail.", "ref": "8:46a", "surah": 8, "ayah": 46},
        {"ar": "وَاصْبِرُوا إِنَّ اللّٰهَ مَعَ الصَّابِرِينَ", "en": "And be patient. Indeed,\nAllah is with the patient.", "ref": "8:46b", "surah": 8, "ayah": 46},
    ]},

    # 66 ─ Al-Maidah 35 — Se rapprocher d'Allah
    {"title": "Se rapprocher d'Allah — Tawassul", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا اتَّقُوا اللّٰهَ", "en": "O you who have believed,\nfear Allah,", "ref": "5:35a", "surah": 5, "ayah": 35},
        {"ar": "وَابْتَغُوا إِلَيْهِ الْوَسِيلَةَ", "en": "And seek the means\nof nearness to Him,", "ref": "5:35b", "surah": 5, "ayah": 35},
        {"ar": "وَجَاهِدُوا فِي سَبِيلِهِ لَعَلَّكُمْ تُفْلِحُونَ", "en": "And strive in His cause\nthat you may succeed.", "ref": "5:35c", "surah": 5, "ayah": 35},
    ]},

    # 67 ─ Al-Jumu'ah 9-10 — La prière du vendredi
    {"title": "La prière du vendredi", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا إِذَا نُودِيَ لِلصَّلَاةِ مِن يَوْمِ الْجُمُعَةِ", "en": "O you who have believed,\nwhen the call to prayer is made\non Friday,", "ref": "62:9a", "surah": 62, "ayah": 9},
        {"ar": "فَاسْعَوْا إِلَىٰ ذِكْرِ اللّٰهِ وَذَرُوا الْبَيْعَ", "en": "Then proceed to the remembrance of Allah\nand leave trade.", "ref": "62:9b", "surah": 62, "ayah": 9},
        {"ar": "ذَٰلِكُمْ خَيْرٌ لَّكُمْ إِن كُنتُمْ تَعْلَمُونَ", "en": "That is better for you,\nif you only knew.", "ref": "62:9c", "surah": 62, "ayah": 9},
        {"ar": "فَإِذَا قُضِيَتِ الصَّلَاةُ فَانتَشِرُوا فِي الْأَرْضِ", "en": "And when the prayer has been concluded,\ndisperse through the land,", "ref": "62:10a", "surah": 62, "ayah": 10},
        {"ar": "وَابْتَغُوا مِن فَضْلِ اللّٰهِ وَاذْكُرُوا اللّٰهَ كَثِيرًا", "en": "And seek from the bounty of Allah,\nand remember Allah often,", "ref": "62:10b", "surah": 62, "ayah": 10},
        {"ar": "لَّعَلَّكُمْ تُفْلِحُونَ", "en": "That you may succeed.", "ref": "62:10c", "surah": 62, "ayah": 10},
    ]},

    # 68 ─ An-Nisa 36 — Bienfaisance envers tous
    {"title": "La bienfaisance totale", "verses": [
        {"ar": "وَاعْبُدُوا اللّٰهَ وَلَا تُشْرِكُوا بِهِ شَيْئًا", "en": "Worship Allah and associate nothing\nwith Him,", "ref": "4:36a", "surah": 4, "ayah": 36},
        {"ar": "وَبِالْوَالِدَيْنِ إِحْسَانًا", "en": "And to parents do good,", "ref": "4:36b", "surah": 4, "ayah": 36},
        {"ar": "وَبِذِي الْقُرْبَىٰ وَالْيَتَامَىٰ وَالْمَسَاكِينِ", "en": "And to relatives, orphans,\nthe needy,", "ref": "4:36c", "surah": 4, "ayah": 36},
        {"ar": "إِنَّ اللّٰهَ لَا يُحِبُّ مَن كَانَ مُخْتَالًا فَخُورًا", "en": "Indeed, Allah does not like those\nwho are self-deluding and boastful.", "ref": "4:36d", "surah": 4, "ayah": 36},
    ]},

    # 69 ─ Al-Imran 133-136 — Se hâter vers le pardon
    {"title": "Se hâter vers le pardon d'Allah", "verses": [
        {"ar": "وَسَارِعُوا إِلَىٰ مَغْفِرَةٍ مِّن رَّبِّكُمْ", "en": "And hasten to forgiveness\nfrom your Lord,", "ref": "3:133a", "surah": 3, "ayah": 133},
        {"ar": "وَجَنَّةٍ عَرْضُهَا السَّمَاوَاتُ وَالْأَرْضُ", "en": "And a garden whose width spans\nthe heavens and earth,", "ref": "3:133b", "surah": 3, "ayah": 133},
        {"ar": "أُعِدَّتْ لِلْمُتَّقِينَ", "en": "Prepared for the righteous.", "ref": "3:133c", "surah": 3, "ayah": 133},
        {"ar": "الَّذِينَ يُنفِقُونَ فِي السَّرَّاءِ وَالضَّرَّاءِ", "en": "Who spend in ease\nand in adversity,", "ref": "3:134a", "surah": 3, "ayah": 134},
        {"ar": "وَالْكَاظِمِينَ الْغَيْظَ وَالْعَافِينَ عَنِ النَّاسِ", "en": "And who restrain anger\nand who pardon people,", "ref": "3:134b", "surah": 3, "ayah": 134},
        {"ar": "وَاللّٰهُ يُحِبُّ الْمُحْسِنِينَ", "en": "And Allah loves\nthe doers of good.", "ref": "3:134c", "surah": 3, "ayah": 134},
    ]},

    # 70 ─ Al-Baqarah 177 — La vraie piété (Al-Birr)
    {"title": "La vraie piété — Al-Birr", "verses": [
        {"ar": "لَّيْسَ الْبِرَّ أَن تُوَلُّوا وُجُوهَكُمْ قِبَلَ الْمَشْرِقِ وَالْمَغْرِبِ", "en": "Righteousness is not turning\nyour faces toward the east or west.", "ref": "2:177a", "surah": 2, "ayah": 177},
        {"ar": "وَلَٰكِنَّ الْبِرَّ مَنْ آمَنَ بِاللّٰهِ وَالْيَوْمِ الْآخِرِ", "en": "But righteousness is one who believes in Allah,\nthe Last Day,", "ref": "2:177b", "surah": 2, "ayah": 177},
        {"ar": "وَآتَى الْمَالَ عَلَىٰ حُبِّهِ ذَوِي الْقُرْبَىٰ وَالْيَتَامَىٰ وَالْمَسَاكِينَ", "en": "And gives wealth, in spite of love for it,\nto relatives, orphans, the needy,", "ref": "2:177c", "surah": 2, "ayah": 177},
        {"ar": "وَأَقَامَ الصَّلَاةَ وَآتَى الزَّكَاةَ", "en": "And establishes prayer\nand gives Zakah.", "ref": "2:177d", "surah": 2, "ayah": 177},
        {"ar": "أُولَٰئِكَ الَّذِينَ صَدَقُوا وَأُولَٰئِكَ هُمُ الْمُتَّقُونَ", "en": "Those are the ones who have been true,\nand it is those who are\nthe righteous.", "ref": "2:177e", "surah": 2, "ayah": 177},
    ]},
]

# ═══════════════════════════════════════════════════════════════════════════
# RECITATEURS — 21 récitateurs de qualité
# ═══════════════════════════════════════════════════════════════════════════
RECITERS = [
    {"name": "Mishary Rashid Alafasy",       "qid": 1,   "ev": "Alafasy_128kbps",              "flag": "🇰🇼"},
    {"name": "Abdul Rahman Al-Sudais",       "qid": 2,   "ev": "AbdulSamad_128kbps",           "flag": "🇸🇦"},
    {"name": "Saad Al-Ghamdi",               "qid": 3,   "ev": "Saad_Al-Ghamdi_128kbps",       "flag": "🇸🇦"},
    {"name": "Maher Al-Muaiqly",             "qid": 10,  "ev": "MaherAlMuaiqly128kbps",        "flag": "🇸🇦"},
    {"name": "Hani Ar-Rifai",                "qid": 5,   "ev": "Hani_Rifai_128kbps",           "flag": "🇸🇦"},
    {"name": "Abu Bakr Al-Shatri",           "qid": 6,   "ev": "Abu_Bakr_Ash-Shaatree_128kbps","flag": "🇸🇦"},
    {"name": "Nasser Al-Qatami",             "qid": 43,  "ev": "Nasser_Alqatami_128kbps",      "flag": "🇸🇦"},
    {"name": "Yasser Al-Dosari",             "qid": 135, "ev": "Yasser_Ad-Dussary_128kbps",    "flag": "🇸🇦"},
    {"name": "Khalid Al-Jalil",              "qid": 53,  "ev": "Khalid_Jalil_128kbps",         "flag": "🇸🇦"},
    {"name": "Ahmad Al-Ajmi",                "qid": 7,   "ev": "Ahmed_ibn_Ali_al-Ajamy_128kbps_UNVERIFIED", "flag": "🇸🇦"},
    {"name": "Saud Al-Shuraim",              "qid": 4,   "ev": "Saud_Al-Shuraym_128kbps",      "flag": "🇸🇦"},
    {"name": "Idris Abkar",                  "qid": 15,  "ev": "Idrees_Abkar_128kbps",         "flag": "🇸🇦"},
    {"name": "Abdul Basit Abdul Samad",      "qid": 16,  "ev": "Abdul_Basit_Murattal_192kbps", "flag": "🇪🇬"},
    {"name": "Mahmoud Khalil Al-Husary",     "qid": 17,  "ev": "Husary_128kbps",               "flag": "🇪🇬"},
    {"name": "Ali Hajjaj Al-Suesy",          "qid": 18,  "ev": "Ali_Hajjaj_AlSuesy_128kbps",   "flag": "🇪🇬"},
    {"name": "Abdullah Al-Juhani",           "qid": 19,  "ev": "Abdullaah_3awwaad_Al-Juhaynee_128kbps", "flag": "🇸🇦"},
    {"name": "Abdullah Basfar",              "qid": 20,  "ev": "Abdullah_Basfar_192kbps",      "flag": "🇸🇦"},
    {"name": "Muhammad Ayyoub",              "qid": 21,  "ev": "Muhammad_Ayyoub_128kbps",      "flag": "🇸🇦"},
    {"name": "Salah Al-Budair",              "qid": 22,  "ev": "Salah_Al_Budair_128kbps",      "flag": "🇸🇦"},
    {"name": "Ali Al-Hudhaify",              "qid": 24,  "ev": "Hudhaify_128kbps",             "flag": "🇸🇦"},
    {"name": "Mohammed Siddiq Al-Minshawi",  "qid": 23,  "ev": "Minshawy_Murattal_128kbps",    "flag": "🇪🇬"},
    {"name": "Tawfiq As-Sayegh",              "qid": 48,  "ev": "Tawfeeq_As-Saweeg_128kbps",     "flag": "🇸🇦"},
    {"name": "Fares Abbad",                   "qid": 37,  "ev": "Fares_Abbad_64kbps",              "flag": "🇩🇿"},
    {"name": "Wadee Al-Yamani",               "qid": 26,  "ev": "Wadee_Alyhani_128kbps",           "flag": "🇸🇦"},
    {"name": "Bandar Baleela",                "qid": 80,  "ev": "Bandar_Baleela_128kbps",          "flag": "🇸🇦"},
    {"name": "Mostafa Al-Lahoni",             "qid": 73,  "ev": "Mostafa_Lahleh_128kbps",          "flag": "🇪🇬"},
    {"name": "Shuraym et Al-Ghamdi",          "qid": 101, "ev": "Saad_Al-Ghamdi_128kbps",         "flag": "🇸🇦"},
    {"name": "Ibrahim Al-Akhdar",             "qid": 76,  "ev": "Ibrahim_Akhdar_128kbps",          "flag": "🇸🇦"},
    {"name": "Akram Al-Alaqmi",               "qid": 107, "ev": "Alafasy_128kbps",                "flag": "🇸🇦"},
    {"name": "Yusuf Al-Shuyoukhi",            "qid": 117, "ev": "Alafasy_128kbps",                "flag": "🇸🇦"},
]

PHOTOS = [
    # ── Couchers & levers de soleil ────────────────────────────────────────
    ("https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?w=1080&h=1920&fit=crop&crop=center", "sunset_orange"),
    ("https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=1080&h=1920&fit=crop&crop=center", "sunset_valley"),
    ("https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1080&h=1920&fit=crop&crop=center", "golden_mountain"),
    ("https://images.unsplash.com/photo-1532274402911-5a369e4c4bb5?w=1080&h=1920&fit=crop&crop=center", "sunset_beach"),
    ("https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1080&h=1920&fit=crop&crop=center", "lake_sunset"),
    ("https://images.unsplash.com/photo-1491466424936-e304919aada7?w=1080&h=1920&fit=crop&crop=center", "alpine_sunset"),
    ("https://images.unsplash.com/photo-1502209524164-acea936639a2?w=1080&h=1920&fit=crop&crop=center", "sunrise_lake"),
    ("https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1080&h=1920&fit=crop&crop=center", "golden_lake"),
    # ── Montagnes & sommets ────────────────────────────────────────────────
    ("https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1080&h=1920&fit=crop&crop=center", "snowy_peaks"),
    ("https://images.unsplash.com/photo-1486870591958-9b9d0d1dda99?w=1080&h=1920&fit=crop&crop=center", "mountain_range"),
    ("https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1080&h=1920&fit=crop&crop=center", "milky_way_mountain"),
    ("https://images.unsplash.com/photo-1434394354979-a235cd36269d?w=1080&h=1920&fit=crop&crop=center", "mountain_lake"),
    ("https://images.unsplash.com/photo-1520962922320-2038eebab146?w=1080&h=1920&fit=crop&crop=center", "fjord"),
    ("https://images.unsplash.com/photo-1483728642387-6c3bdd6c93e5?w=1080&h=1920&fit=crop&crop=center", "alpine_meadow"),
    # ── Forêts & cascades ──────────────────────────────────────────────────
    ("https://images.unsplash.com/photo-1448375240586-882707db888b?w=1080&h=1920&fit=crop&crop=center", "forest_green"),
    ("https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1080&h=1920&fit=crop&crop=center", "green_meadow"),
    ("https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=1080&h=1920&fit=crop&crop=center", "waterfall"),
    ("https://images.unsplash.com/photo-1542273917363-3b1817f69a2d?w=1080&h=1920&fit=crop&crop=center", "forest_light"),
    ("https://images.unsplash.com/photo-1448630360428-65456885c650?w=1080&h=1920&fit=crop&crop=center", "autumn_trees"),
    # ── Déserts & dunes ────────────────────────────────────────────────────
    ("https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=1080&h=1920&fit=crop&crop=center", "sahara_dunes"),
    ("https://images.unsplash.com/photo-1518173946687-a4c8892bbd9f?w=1080&h=1920&fit=crop&crop=center", "golden_dunes"),
    ("https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=1080&h=1920&fit=crop&crop=center", "canyon_red"),
    ("https://images.unsplash.com/photo-1547234935-80c7145ec969?w=1080&h=1920&fit=crop&crop=center", "wadi_desert"),
    # ── Océans & côtes ─────────────────────────────────────────────────────
    ("https://images.unsplash.com/photo-1505118380757-91f5f5632de0?w=1080&h=1920&fit=crop&crop=center", "turquoise_sea"),
    ("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1080&h=1920&fit=crop&crop=center", "tropical_coast"),
    ("https://images.unsplash.com/photo-1504701954957-2010ec3bcec1?w=1080&h=1920&fit=crop&crop=center", "rocky_coast"),
    # ── Ciels & phénomènes naturels ────────────────────────────────────────
    ("https://images.unsplash.com/photo-1534088568595-a066f410bcda?w=1080&h=1920&fit=crop&crop=center", "dramatic_sky"),
    ("https://images.unsplash.com/photo-1504608524841-42584120d693?w=1080&h=1920&fit=crop&crop=center", "golden_clouds"),
    ("https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=1080&h=1920&fit=crop&crop=center", "aurora_borealis"),
    ("https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1080&h=1920&fit=crop&crop=center", "misty_lake"),
]

def _load_font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            pass
    return ImageFont.load_default()

_FONTS_CACHE = None

def fonts():
    global _FONTS_CACHE
    if _FONTS_CACHE is None:
        AR = [
            "/usr/share/fonts/truetype/fonts-hosny-amiri/Amiri-Regular.ttf",
            "/usr/share/fonts/opentype/fonts-hosny-amiri/Amiri-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        ]
        IT = [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf",
        ]
        RG = [
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        ]
        _FONTS_CACHE = {
            "ar":      _load_font(AR, 92),    # +6 : arabe plus lisible
            "ar_bold": _load_font(AR, 98),    # +8 : mot courant plus imposant
            "en":      _load_font(IT, 54),    # +2 : traduction légèrement plus grande
            "ref":     _load_font(RG, 42),    # +2
            "small":   _load_font(RG, 30),    # +2
            "title":   _load_font(IT, 42),    # +8 : titre beaucoup plus visible
        }
    return _FONTS_CACHE

WORD_GAP = 20

def _word_w(font, word):
    bb = font.getbbox(word)
    return bb[2] - bb[0]

def _line_h(font):
    bb = font.getbbox("ابجد")
    return bb[3] - bb[1]

def _wrap_words(words, font, max_w):
    lines, cur, cur_w = [], [], 0
    for i, w in enumerate(words):
        ww = _word_w(font, w)
        if cur and cur_w + WORD_GAP + ww > max_w:
            lines.append(cur)
            cur, cur_w = [(i, w, ww)], ww
        else:
            cur.append((i, w, ww))
            cur_w = (cur_w + WORD_GAP + ww) if len(cur) > 1 else ww
    if cur:
        lines.append(cur)
    return lines

VISUAL_LEAD_S = 0.25   # Anticipe le surlignage de 250ms pour compenser la latence perceptive

def _ease_inout(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

class SyncEngine:
    FADE_S = 0.080
    def __init__(self, timings, n_audio_frames, aud_dur, fps=FPS):
        self._timings        = timings or []
        self._n_audio_frames = max(1, n_audio_frames)
        self._aud_dur        = max(0.001, aud_dur)
        self._fps            = fps
        self._n_words        = len(self._timings)
    def frame_to_t(self, frame_index):
        dt = self._aud_dur / self._n_audio_frames
        return min(frame_index * dt, self._aud_dur)
    def word_at(self, frame_index):
        if not self._timings:
            return 0
        t = self.frame_to_t(frame_index) + VISUAL_LEAD_S
        segs = self._timings
        if t >= segs[-1]["end"]:
            return self._n_words - 1
        if t < segs[0]["start"]:
            return 0
        for i, seg in enumerate(segs):
            if seg["start"] <= t < seg["end"]:
                return i
        for i in range(len(segs) - 1):
            if segs[i]["end"] <= t < segs[i + 1]["start"]:
                return i
        return 0
    def hi_strength(self, frame_index):
        if not self._timings:
            return 1.0
        t    = self.frame_to_t(frame_index) + VISUAL_LEAD_S
        segs = self._timings
        # Avant le premier mot : pas de highlight
        if t < segs[0]["start"]:
            return 0.0
        # Après la fin du dernier mot : le dernier mot reste allumé
        # (pas de fade-out qui crée le double flash)
        if t >= segs[-1]["end"]:
            return 1.0
        wi    = self.word_at(frame_index)
        seg   = segs[wi]
        t_s   = seg["start"]
        t_e   = seg["end"]
        fade  = self.FADE_S
        # Pendant le mot courant
        if t_s <= t < t_e:
            if t < t_s + fade:
                return _ease_inout((t - t_s) / fade)
            return 1.0
        # Entre deux mots : décroissance rapide
        if wi < self._n_words - 1:
            next_start = segs[wi + 1]["start"]
            if t_e <= t < next_start:
                silence = next_start - t_e
                elapsed = t - t_e
                decay   = max(fade, silence * 0.25)
                if elapsed < decay:
                    return _ease_inout(1.0 - elapsed / decay)
                return 0.0
        return 1.0

_HI_GLOW_COLOR   = (255, 215, 80)          # Or pur pour le mot courant
_HI_GLOW_ALPHA1  = 90                      # Glow externe plus visible
_HI_GLOW_ALPHA2  = 140                     # Glow interne très lumineux
_HI_GLOW_RADIUS1 = 22                      # Halo large
_HI_GLOW_RADIUS2 = 10                      # Halo serré
_HI_WORD_COLOR   = (255, 245, 180)         # Mot courant : blanc-or
_HI_UNDER_H      = 3                       # Soulignement fin sous le mot
_HI_UNDER_OFFSET = 4                       # Décalage soulignement
_HI_UNDER_COLOR  = (255, 215, 80)          # Couleur or pour le soulignement
_PAST_COLOR      = (160, 160, 180)         # Mots passés : gris-bleu doux
_FUTURE_COLOR    = (220, 220, 235)         # Mots à venir : blanc nacré
_SHADOW_OFFSETS  = [(-2,-2),(2,-2),(-2,2),(2,2),(0,4),(1,3),(-1,3)]  # Ombre plus riche
_EN_COLOR        = (240, 240, 255)         # Traduction : blanc légèrement bleuté

def _glow_word(draw, x, y, w, font, hi_strength, alpha):
    if hi_strength <= 0.01:
        return
    for radius, base_a in [(_HI_GLOW_RADIUS1, _HI_GLOW_ALPHA1), (_HI_GLOW_RADIUS2, _HI_GLOW_ALPHA2)]:
        ga = int(base_a * hi_strength * (alpha / 255.0))
        if ga < 2:
            continue
        for ddx in range(-radius, radius + 1, max(1, radius // 3)):
            for ddy in range(-radius // 2, radius // 2 + 1, max(1, radius // 4)):
                draw.text((x + ddx, y + ddy), w, font=font, fill=(*_HI_GLOW_COLOR, max(0, min(255, ga))))

def draw_arabic_karaoke(draw, text, font, font_hi, cx, y_start, max_w, highlight_idx, alpha, hi_strength=1.0, line_gap=30):
    words = text.split()
    if not words:
        return 0
    lines   = _wrap_words(words, font, max_w)
    fh      = _line_h(font) + 6
    fh_hi   = _line_h(font_hi) + 6
    y       = y_start
    total_h = 0
    for line in lines:
        hi_in  = any(idx == highlight_idx for idx, _, _ in line)
        line_w = 0
        for k, (idx, w, _) in enumerate(line):
            f_use   = font_hi if idx == highlight_idx else font
            line_w += _word_w(f_use, w) + (WORD_GAP if k > 0 else 0)
        x      = cx + line_w // 2
        line_h = fh_hi if hi_in else fh
        for k, (idx, w, _) in enumerate(line):
            is_hi   = (idx == highlight_idx)
            is_past = (idx < highlight_idx)
            f_use   = font_hi if is_hi else font
            ww      = _word_w(f_use, w)
            x      -= ww
            dy_off = (fh_hi - fh) // 2 if (hi_in and not is_hi) else 0
            word_y = y + dy_off
            if is_hi:
                _glow_word(draw, x, word_y, w, f_use, hi_strength, alpha)
            shad_a = min(alpha, 150)
            for dx, dy in _SHADOW_OFFSETS:
                draw.text((x + dx, word_y + dy), w, font=f_use, fill=(0, 0, 0, shad_a))
            if is_hi:
                color = (*_HI_WORD_COLOR, alpha)       # Or-blanc pour le mot courant
            elif is_past:
                color = (*_PAST_COLOR, int(alpha * 0.65))   # Passés plus discrets
            else:
                color = (*_FUTURE_COLOR, int(alpha * 0.90))  # À venir légèrement atténués
            draw.text((x, word_y), w, font=f_use, fill=color)
            x -= WORD_GAP
        y       += line_h + line_gap
        total_h += line_h + line_gap
    return total_h

def dl_image(url, path):
    if path.exists():
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            path.write_bytes(r.read())
        return True
    except Exception as e:
        print(f"   Image DL: {e}")
        return False

def cinematic(img, p):
    img = ImageEnhance.Contrast(img).enhance(p["contrast"])
    img = ImageEnhance.Color(img).enhance(p["color_sat"])
    img = ImageEnhance.Brightness(img).enhance(p["brightness"])
    # Vignette légère uniquement sur les bords — jamais trop sombre au centre
    vign = Image.new("L", (W, H), 0)
    vd   = ImageDraw.Draw(vign)
    cx, cy = W // 2, H // 2
    mr  = int(math.sqrt(cx**2 + cy**2))
    vs  = int(p["vign"])
    for r in range(mr, 0, -5):
        a = int(vs * (1 - (r / mr) ** 1.6))  # exposant plus fort = vignette moins agressive
        vd.ellipse([cx-r, cy-r, cx+r, cy+r], fill=max(0, a))
    result = Image.composite(Image.new("RGB", (W, H), 0), img, vign)
    # S'assurer que le résultat est suffisamment lumineux
    result = ImageEnhance.Brightness(result).enhance(1.12)
    return result

def get_scene(idx, p):
    real = p["photo_indices"][idx % len(p["photo_indices"])]
    url, theme = PHOTOS[real]
    cache = OUT_DIR / "cache" / f"photo_{real:03d}.jpg"
    if dl_image(url, cache):
        try:
            img = Image.open(str(cache)).convert("RGB").resize((W, H), Image.LANCZOS)
            return cinematic(img, p), theme
        except:
            pass
    img = Image.new("RGB", (W, H))
    d   = ImageDraw.Draw(img)
    cols = [(15,10,30),(40,20,60),(80,30,80),(120,50,40),(180,100,30),(220,160,50)]
    seg  = H // (len(cols) - 1)
    for i, (c1, c2) in enumerate(zip(cols, cols[1:])):
        for y in range(seg):
            t = y / seg
            d.line([(0, i*seg+y), (W, i*seg+y)], fill=tuple(int(c1[j]*(1-t)+c2[j]*t) for j in range(3)))
    return cinematic(img, p), "gradient"

def ken_burns(img, t, zoom_end=1.06, pan_x=0., pan_y=0.):
    w, h   = img.size
    zoom   = 1. + (zoom_end - 1.) * t
    nw, nh = int(w / zoom), int(h / zoom)
    cx     = int(w // 2 + pan_x * w * (1 - t))
    cy     = int(h // 2 + pan_y * h * (1 - t))
    l  = max(0, cx - nw // 2)
    t2 = max(0, cy - nh // 2)
    return img.crop((l, t2, min(w, l+nw), min(h, t2+nh))).resize((w, h), Image.LANCZOS)

def make_params(n):
    directions = [(+1,0),(-1,0),(0,+1),(0,-1)]
    kb = []
    for _ in range(n):
        dx, dy = RNG.choice(directions)
        kb.append({"zoom_end": RNG.uniform(1.04, 1.09), "pan_x": dx * RNG.uniform(0.008, 0.022), "pan_y": dy * RNG.uniform(0.008, 0.022)})
    return {
        "photo_indices": RNG.sample(range(len(PHOTOS)), k=min(n, len(PHOTOS))),
        "contrast":      RNG.uniform(1.08, 1.18),   # Contraste modéré pour ne pas assombrir
        "color_sat":     RNG.uniform(1.15, 1.35),   # Couleurs bien saturées
        "brightness":    RNG.uniform(0.95, 1.10),   # Toujours lumineux
        "vign":          RNG.uniform(60, 100),       # Vignette très légère
        "xf":            RNG.randint(8, 16),
        "kb":            kb,
    }

def render_frame(base_img, verse, reciter, title, alpha_frac, hi_word, hi_strength, verse_num, total_verses):
    import re as _re, math as _math
    img = base_img.copy().convert("RGBA")
    ov  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d   = ImageDraw.Draw(ov, "RGBA")
    f   = fonts()
    a   = int(255 * max(0., min(1., alpha_frac)))

    # ── Layout ───────────────────────────────────────────────────────────────
    words_ar  = verse["ar"].split()
    lines_ar  = _wrap_words(words_ar, f["ar"], 920)
    fh        = _line_h(f["ar"]) + 6
    ar_est_h  = len(lines_ar) * (fh + 32) + 10
    en_lines  = verse["en"].split("\n")
    en_h      = len(en_lines) * 68
    block_h   = ar_est_h + 30 + 56 + 24 + en_h
    ar_top    = H // 2 - block_h // 2 + 20
    mid       = H // 2

    # ── 1. Fond dégradé central — vignette plus dramatique + teinte bleue-nuit
    panel_top    = mid - block_h // 2 - 130
    panel_bottom = mid + block_h // 2 + 130
    panel_h      = panel_bottom - panel_top
    for yi in range(panel_top, panel_bottom):
        dist = abs(yi - mid) / (panel_h / 2 + 1)
        # Dégradé quadratique : très opaque au centre, transparent aux bords
        sa = int(210 * max(0., 1 - dist ** 1.6))
        # Légère teinte bleu nuit au fond (0, 0, 15)
        d.line([(0, yi), (W, yi)], fill=(0, 0, 15, sa))

    # ── 2. Bande décorative supérieure — ligne dorée + étoile islamique ─────
    band_y = panel_top + 28
    line_w_half = int(W * 0.38)
    # Ligne gauche
    for xt in range(W//2 - line_w_half, W//2 - 44):
        frac = (xt - (W//2 - line_w_half)) / (line_w_half - 44)
        la   = int(a * 0.8 * frac)
        d.point((xt, band_y), fill=(212, 175, 55, la))
    # Ligne droite
    for xt in range(W//2 + 44, W//2 + line_w_half):
        frac = (W//2 + line_w_half - xt) / (line_w_half - 44)
        la   = int(a * 0.8 * frac)
        d.point((xt, band_y), fill=(212, 175, 55, la))
    # Étoile à 8 branches (losange croisé)
    cx_star, cy_star = W//2, band_y
    star_r1, star_r2 = 16, 7
    pts = []
    for i in range(16):
        angle = _math.pi * i / 8 - _math.pi / 2
        r     = star_r1 if i % 2 == 0 else star_r2
        pts.extend([cx_star + r * _math.cos(angle), cy_star + r * _math.sin(angle)])
    d.polygon(pts, fill=(212, 175, 55, int(a * 0.9)))

    # ── 3. Titre — plus grand, lettres espacées, avec halo ──────────────────
    title_y = band_y + 22
    tw = f["title"].getbbox(title)[2] - f["title"].getbbox(title)[0]
    tx = W // 2 - tw // 2
    # Halo titre
    for dx, dy in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,-2),(-2,2),(2,2)]:
        d.text((tx+dx, title_y+dy), title, font=f["title"], fill=(212, 175, 55, int(a*0.18)))
    # Ombre
    d.text((tx+2, title_y+3), title, font=f["title"], fill=(0, 0, 0, int(a*0.6)))
    # Texte principal
    d.text((tx, title_y), title, font=f["title"], fill=(255, 220, 100, int(a*0.95)))

    # ── 4. Texte arabe karaoké ───────────────────────────────────────────────
    ar_h = draw_arabic_karaoke(
        d, verse["ar"], f["ar"], f["ar_bold"],
        cx=W//2, y_start=ar_top, max_w=920,
        highlight_idx=hi_word, alpha=a, hi_strength=hi_strength, line_gap=32
    )

    # ── 5. Séparateur — ligne dorée ornementale avec fleurs ──────────────────
    sep_y    = ar_top + ar_h + 22
    sep_half = int(W * 0.36)
    # Dégradé gauche→droite
    for xt in range(W//2 - sep_half, W//2 - 30):
        frac = (xt - (W//2 - sep_half)) / max(1, sep_half - 30)
        la   = int(a * 0.9 * frac)
        d.point((xt, sep_y),     fill=(212, 175, 55, la))
        d.point((xt, sep_y + 1), fill=(212, 175, 55, la // 2))
    for xt in range(W//2 + 30, W//2 + sep_half):
        frac = (W//2 + sep_half - xt) / max(1, sep_half - 30)
        la   = int(a * 0.9 * frac)
        d.point((xt, sep_y),     fill=(212, 175, 55, la))
        d.point((xt, sep_y + 1), fill=(212, 175, 55, la // 2))
    # Losange central
    ds = 9
    d.polygon(
        [(W//2, sep_y - ds), (W//2 + ds, sep_y), (W//2, sep_y + ds), (W//2 - ds, sep_y)],
        fill=(255, 215, 80, int(a * 0.95))
    )
    # Petits points décoratifs de chaque côté
    for ox in [28, 42]:
        for sx in [-1, 1]:
            d.ellipse(
                [W//2 + sx*ox - 3, sep_y - 3, W//2 + sx*ox + 3, sep_y + 3],
                fill=(212, 175, 55, int(a * 0.7))
            )

    # ── 6. Référence verset ──────────────────────────────────────────────────
    ref_y     = sep_y + 18
    _clean_ref = _re.sub(r'[a-z]$', '', verse["ref"])
    rw         = f["ref"].getbbox(_clean_ref)[2] - f["ref"].getbbox(_clean_ref)[0]
    rx         = W//2 - rw//2
    # Halo doré
    d.text((rx+2, ref_y+3), _clean_ref, font=f["ref"], fill=(0, 0, 0, int(a*0.55)))
    d.text((rx, ref_y), _clean_ref, font=f["ref"], fill=(255, 215, 80, int(a*0.95)))

    # ── 7. Traduction anglaise ───────────────────────────────────────────────
    en_y = ref_y + 56
    for i, line in enumerate(en_lines):
        lw = f["en"].getbbox(line)[2] - f["en"].getbbox(line)[0]
        lx = W//2 - lw//2
        ly = en_y + i * 68
        # Ombre riche
        for dx, dy in _SHADOW_OFFSETS:
            d.text((lx+dx, ly+dy), line, font=f["en"], fill=(0, 0, 0, min(255, int(a*0.55))))
        d.text((lx, ly), line, font=f["en"], fill=(*_EN_COLOR, a))

    # ── 8. Bande basse ornementale ───────────────────────────────────────────
    low_band_y = panel_bottom - 28
    for xt in range(W//2 - line_w_half, W//2 + line_w_half):
        frac_l = (xt - (W//2 - line_w_half)) / (2 * line_w_half)
        frac   = 1 - abs(frac_l * 2 - 1)  # pic au centre
        la     = int(a * 0.5 * frac)
        d.point((xt, low_band_y), fill=(212, 175, 55, la))

    # ── 9. Dots navigation — avec indicateur glissant stylisé ────────────────
    dot_y   = int(H * 0.882)
    MAX_DOTS = 12
    if total_verses <= MAX_DOTS:
        dots_start, dots_end = 0, total_verses
    else:
        half       = MAX_DOTS // 2
        dots_start = max(0, min(verse_num - 1 - half, total_verses - MAX_DOTS))
        dots_end   = dots_start + MAX_DOTS
    n_dots  = dots_end - dots_start
    spacing = min(32, (W - 120) // max(1, n_dots))
    start_x = W//2 - (n_dots * spacing) // 2
    for i in range(dots_start, dots_end):
        xd = start_x + (i - dots_start) * spacing
        if i == verse_num - 1:
            # Dot actif : grand, or vif, avec halo
            d.ellipse([xd-11, dot_y-11, xd+11, dot_y+11], fill=(212, 175, 55, int(a*0.25)))
            d.ellipse([xd-8,  dot_y-8,  xd+8,  dot_y+8 ], fill=(255, 215, 80, int(a*0.98)))
        elif i < verse_num - 1:
            # Passés : gris moyen
            d.ellipse([xd-4, dot_y-4, xd+4, dot_y+4], fill=(180, 180, 200, int(a*0.55)))
        else:
            # À venir : discrets
            d.ellipse([xd-3, dot_y-3, xd+3, dot_y+3], fill=(120, 120, 140, int(a*0.35)))

    # ── 10. Récitateur + compte ───────────────────────────────────────────────
    rec  = reciter["flag"] + "  " + reciter["name"]
    rw2  = f["small"].getbbox(rec)[2] - f["small"].getbbox(rec)[0]
    ry2  = int(H * 0.915)
    d.text((W//2 - rw2//2 + 1, ry2 + 2), rec, font=f["small"], fill=(0, 0, 0, int(a*0.5)))
    d.text((W//2 - rw2//2, ry2), rec, font=f["small"], fill=(212, 175, 55, int(a*0.88)))
    hw   = f["small"].getbbox(ACCOUNT)[2] - f["small"].getbbox(ACCOUNT)[0]
    hay  = int(H * 0.950)
    d.text((W//2 - hw//2 + 1, hay + 2), ACCOUNT, font=f["small"], fill=(0, 0, 0, int(a*0.45)))
    d.text((W//2 - hw//2, hay), ACCOUNT, font=f["small"], fill=(255, 255, 255, int(a*0.78)))

    return Image.alpha_composite(img, ov).convert("RGB")

def dl_audio(verse, reciter):
    s, a  = verse["surah"], verse["ayah"]
    qid   = reciter["qid"]
    ev    = reciter["ev"]
    ss, aa = str(s).zfill(3), str(a).zfill(3)
    cache = OUT_DIR / "cache" / f"audio_{s}_{a}_{qid}.mp3"
    if cache.exists():
        return cache
    urls = [
        f"https://cdn.islamic.network/quran/audio/128/{qid}/{s}{aa}.mp3",
        f"https://everyayah.com/data/{ev}/{ss}{aa}.mp3",
        f"https://everyayah.com/data/Alafasy_128kbps/{ss}{aa}.mp3",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            if len(data) > 3000:
                cache.write_bytes(data)
                print(f"   Audio {cache.name} ({len(data)//1024} KB)")
                return cache
        except:
            continue
    print("   Audio indisponible")
    return None

def get_audio_dur(path):
    try:
        r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)], capture_output=True, text=True, timeout=10)
        v = float(r.stdout.strip())
        return v if v > 0 else 4.5
    except:
        return 4.5

def _normalize_ar(text):
    result = []
    for c in text:
        cp = ord(c)
        if (0x0610 <= cp <= 0x061A or 0x064B <= cp <= 0x065F or cp == 0x0670 or cp == 0x06D6 or cp == 0x06DC):
            continue
        if cp == 0x0640:
            continue
        result.append(c)
    normalized = "".join(result).strip()
    normalized = normalized.replace("\u0623", "\u0627").replace("\u0625", "\u0627").replace("\u0622", "\u0627")
    normalized = normalized.replace("\u0649", "\u064a").replace("\u0629", "\u0647")
    return normalized

def _char_similarity(a, b):
    if not a or not b:
        return 0.0
    pref = 0
    for ca, cb in zip(a, b):
        if ca == cb:
            pref += 1
        else:
            break
    set_a = set(a)
    set_b = set(b)
    jaccard = len(set_a & set_b) / max(1, len(set_a | set_b))
    pref_score = pref / max(len(a), len(b))
    return 0.6 * pref_score + 0.4 * jaccard

def get_timings(verse, reciter, audio_path, aud_dur):
    s, a, qid = verse["surah"], verse["ayah"], reciter["qid"]
    cache     = OUT_DIR / "cache" / f"timing_{s}_{a}_{qid}.json"
    n_words   = len(verse["ar"].split())
    verse_words = verse["ar"].split()
    def _validate_and_scale(tlist, dur):
        if not tlist or len(tlist) != n_words:
            return None
        # Rebaser à t=0 : si le premier mot commence avec un décalage (intro silence)
        # on soustrait cet offset pour que le surlignage commence dès le début de l'audio
        first_start = tlist[0]["start"]
        if first_start > 0.05:
            tlist = [{"start": max(0.0, t["start"] - first_start),
                      "end":   max(0.0, t["end"]   - first_start)} for t in tlist]
        last_end = tlist[-1]["end"]
        # Rescaler pour que last_end == dur
        if last_end > 0.01 and abs(last_end - dur) > 0.05:
            k     = dur / last_end
            tlist = [{"start": t["start"] * k, "end": t["end"] * k} for t in tlist]
        tlist = [{"start": max(0.0, min(t["start"], dur)), "end": max(0.0, min(t["end"], dur))} for t in tlist]
        for i in range(1, len(tlist)):
            if tlist[i]["start"] < tlist[i-1]["end"]:
                tlist[i]["start"] = tlist[i-1]["end"]
        tlist[-1]["end"] = dur
        return tlist
    if cache.exists():
        try:
            data = json.loads(cache.read_text())
            validated = _validate_and_scale(data, aud_dur)
            if validated:
                print(f"      Timings (cache) {n_words} mots")
                return validated
        except:
            pass
    try:
        _qid_p = str(reciter["qid"])
        _surah_p = str(verse["surah"])
        url_p = "https://api.qurancdn.com/api/qdc/audio/reciters/" + _qid_p + "/audio_files?chapter=" + _surah_p + "&segments=true"
        req_p = urllib.request.Request(url_p, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req_p, timeout=15) as r_p:
            data_p = json.loads(r_p.read())
        for af_p in data_p.get("audio_files", []):
            if str(af_p.get("ayah", "")) == str(verse["ayah"]):
                segs_p = af_p.get("segments", [])
                if segs_p:
                    tlist_p = [{"start": sg[1]/1000.0, "end": sg[2]/1000.0} for sg in segs_p if len(sg) >= 3]
                    if len(tlist_p) == n_words:
                        validated_p = _validate_and_scale(tlist_p, aud_dur)
                        if validated_p:
                            cache.write_text(json.dumps(validated_p))
                            print(f"      ✅ QuranCDN timings OK ({n_words} mots)")
                            return validated_p
                    elif tlist_p:
                        ratio = n_words / len(tlist_p)
                        interp = []
                        for i in range(n_words):
                            src_i = min(int(i / ratio), len(tlist_p)-1)
                            src_i2 = min(src_i+1, len(tlist_p)-1)
                            alpha_v = (i/ratio) - src_i
                            ts = tlist_p[src_i]["start"] * (1-alpha_v) + tlist_p[src_i2]["start"] * alpha_v
                            te = tlist_p[src_i]["end"] * (1-alpha_v) + tlist_p[src_i2]["end"] * alpha_v
                            interp.append({"start": ts, "end": te})
                        validated_p = _validate_and_scale(interp, aud_dur)
                        if validated_p:
                            cache.write_text(json.dumps(validated_p))
                            print(f"      ✅ QuranCDN timings interpolés ({len(tlist_p)}→{n_words} mots)")
                            return validated_p
    except Exception as e_p:
        print(f"      QuranCDN: {e_p}")
    if _load_whisper() and audio_path and Path(audio_path).exists():
        try:
            import whisper
            print(f"      Whisper aligne {Path(audio_path).name}...")
            result = _whisper_model.transcribe(str(audio_path), language="ar", word_timestamps=True, verbose=False, initial_prompt="بسم الله الرحمن الرحيم", temperature=0.0, condition_on_previous_text=False)
            whisper_words = []
            for seg in result.get("segments", []):
                for w in seg.get("words", []):
                    word_text = w["word"].strip()
                    if word_text:
                        whisper_words.append({"word": word_text, "start": float(w["start"]), "end": float(w["end"])})
            print(f"         Whisper: {len(whisper_words)} tokens / {n_words} mots")
            if whisper_words:
                tlist = _align_whisper_to_verse(verse_words, whisper_words, aud_dur)
                validated = _validate_and_scale(tlist, aud_dur)
                if validated:
                    cache.write_text(json.dumps(validated))
                    print(f"      Whisper aligne OK")
                    return validated
        except Exception as e:
            print(f"      Whisper erreur : {e}")
    print("      Fallback proportionnel " + verse["ref"])
    tlist = _fallback_timings(verse_words, aud_dur)
    return _validate_and_scale(tlist, aud_dur) or tlist

def _align_whisper_to_verse(verse_words, whisper_words, aud_dur):
    n   = len(verse_words)
    m   = len(whisper_words)
    tlist = [None] * n
    verse_norm   = [_normalize_ar(w) for w in verse_words]
    whisper_norm = [_normalize_ar(w["word"]) for w in whisper_words]
    wi = 0
    for vi in range(n):
        if wi >= m:
            break
        vw       = verse_norm[vi]
        best_j   = wi
        best_scr = -1.0
        lo = max(0, wi)
        hi = min(m, wi + 4)
        for j in range(lo, hi):
            scr = _char_similarity(vw, whisper_norm[j])
            if scr > best_scr:
                best_scr = scr
                best_j   = j
        if best_scr > 0.35:
            tlist[vi] = {"start": whisper_words[best_j]["start"], "end": whisper_word
