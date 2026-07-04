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

_ensure_installed()


print("\n🚀 Démarrage de la génération...\n")

import os, sys, math, subprocess, datetime, json, random, time, hashlib, unicodedata, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import urllib.request

W, H      = 1080, 1920
FPS       = 24
# v7 : PAS de limite de durée — on joue TOUS les versets du passage sans coupure
MAX_DUR   = None   # Pas de limite : la récitation n'est jamais coupée
BREATH    = 0.40   # Silence naturel entre versets (respecte le rythme de la récitation)
# 🔧 FIX karaoké parfait : le nombre de frames vidéo du breath (BREATH_FRAMES) et la
# durée AUDIO du silence inséré entre versets DOIVENT être calculés depuis la MÊME
# source. Avant : breath_frames = int(BREATH*FPS) = 9 frames (0.375s vidéo) alors que
# le silence audio généré dans mix_audio() durait 0.40s pile → écart de 0.025s à
# CHAQUE transition entre ayat, qui s'accumule sur tout le passage et désynchronise
# progressivement le karaoké des derniers versets. On dérive maintenant BREATH_DUR
# (durée du silence audio) à partir de BREATH_FRAMES (durée vidéo), pas l'inverse :
# les deux flux sont ainsi verrouillés image par image, sans dérive possible.
BREATH_FRAMES = int(round(BREATH * FPS))
BREATH_DUR    = BREATH_FRAMES / FPS
ACCOUNT   = os.getenv("IG_HANDLE", "@quranreminders14")
OUT_DIR   = Path("quran_out")
for d in [OUT_DIR, OUT_DIR / "frames", OUT_DIR / "cache"]:
    d.mkdir(exist_ok=True)

def make_seed():
    raw = f"{time.time_ns()}_{os.urandom(16).hex()}_{os.getpid()}"
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16) % (2 ** 31)

RUN_SEED = make_seed()
RNG      = random.Random(RUN_SEED)

class AudioMissingError(Exception):
    """Levée quand l'audio d'un verset est introuvable malgré tous les miroirs.
    Empêche de générer une vidéo avec des frames silencieuses (verset 'sauté')."""
    pass

# ═══════════════════════════════════════════════════════════════════════════
# PASSAGES — 35 thèmes avec plusieurs versets chacun
# ═══════════════════════════════════════════════════════════════════════════
PASSAGES = [
    # 0 ─ Al-Fatiha complète
    {"title": "Al-Fatiha — The Opening", "verses": [
        {"ar": "بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيمِ",   "en": "In the name of Allah,the Most Gracious, the Most Merciful.",  "ref": "1:1",  "surah": 1,  "ayah": 1},
        {"ar": "الْحَمْدُ لِلّٰهِ رَبِّ الْعَالَمِينَ",    "en": "All praise is due to Allah,Lord of all the worlds.",            "ref": "1:2",  "surah": 1,  "ayah": 2},
        {"ar": "الرَّحْمٰنِ الرَّحِيمِ",                   "en": "The Most Gracious,the Most Merciful.",                         "ref": "1:3",  "surah": 1,  "ayah": 3},
        {"ar": "مَالِكِ يَوْمِ الدِّينِ",                  "en": "Master of the Day of Judgment.",                                 "ref": "1:4",  "surah": 1,  "ayah": 4},
        {"ar": "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "en": "It is You we worshipand You we ask for help.",                "ref": "1:5",  "surah": 1,  "ayah": 5},
        {"ar": "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ",       "en": "Guide us to the straight path.",                                 "ref": "1:6",  "surah": 1,  "ayah": 6},
        {"ar": "صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ", "en": "The path of those You have blessed,not those who have earned angernor those who are astray.", "ref": "1:7", "surah": 1, "ayah": 7},
    ]},

    # 1 ─ La patience et l'espoir — Al-Inshirah
    {"title": "Patience and Hope", "verses": [
        {"ar": "أَلَمْ نَشْرَحْ لَكَ صَدْرَكَ",             "en": "Did We not expandfor you your chest?",                         "ref": "94:1", "surah": 94, "ayah": 1},
        {"ar": "وَوَضَعْنَا عَنكَ وِزْرَكَ",               "en": "And removed from youyour burden?",                              "ref": "94:2", "surah": 94, "ayah": 2},
        {"ar": "الَّذِي أَنقَضَ ظَهْرَكَ",                 "en": "Which had weighedheavily upon your back?",                      "ref": "94:3", "surah": 94, "ayah": 3},
        {"ar": "وَرَفَعْنَا لَكَ ذِكْرَكَ",                "en": "And raised highyour repute?",                                    "ref": "94:4", "surah": 94, "ayah": 4},
        {"ar": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا",           "en": "For indeed, with hardshipwill be ease.",                        "ref": "94:5", "surah": 94, "ayah": 5},
        {"ar": "إِنَّ مَعَ الْعُسْرِ يُسْرًا",             "en": "Indeed, with hardshipwill be ease.",                            "ref": "94:6", "surah": 94, "ayah": 6},
        {"ar": "فَإِذَا فَرَغْتَ فَانصَبْ",                "en": "So when you have finishedyour duties, then stand up.",           "ref": "94:7", "surah": 94, "ayah": 7},
        {"ar": "وَإِلَىٰ رَبِّكَ فَارْغَبْ",               "en": "And to your Lorddirect your longing.",                          "ref": "94:8", "surah": 94, "ayah": 8},
    ]},

    # 2 ─ La confiance en Allah — At-Talaq
    {"title": "Trust in Allah", "verses": [
        {"ar": "وَمَن يَتَّقِ اللّٰهَ يَجْعَل لَّهُ مَخْرَجًا", "en": "And whoever fears Allah,He will make for him a way out.", "ref": "65:2", "surah": 65, "ayah": 2},
        {"ar": "وَيَرْزُقْهُ مِنْ حَيْثُ لَا يَحْتَسِبُ",       "en": "And will provide for himfrom where he does not expect.",  "ref": "65:3", "surah": 65, "ayah": 3},
        {"ar": "وَمَن يَتَوَكَّلْ عَلَى اللّٰهِ فَهُوَ حَسْبُهُ", "en": "Whoever relies upon Allah —He is sufficient for him.", "ref": "65:3b","surah": 65, "ayah": 3},
        {"ar": "إِنَّ اللّٰهَ بَالِغُ أَمْرِهِ",              "en": "Indeed, Allah will accomplishHis purpose.",                  "ref": "65:3c","surah": 65, "ayah": 3},
        {"ar": "قَدْ جَعَلَ اللّٰهُ لِكُلِّ شَيْءٍ قَدْرًا",  "en": "Allah has already seta decreed extent for everything.", "ref": "65:3d","surah": 65, "ayah": 3},
    ]},

    # 3 ─ Al-Ikhlas complète
    {"title": "Al-Ikhlas — Sincerity", "verses": [
        {"ar": "قُلْ هُوَ اللّٰهُ أَحَدٌ",               "en": "Say: He is Allah, [who is] One.",               "ref": "112:1", "surah": 112, "ayah": 1},
        {"ar": "اللّٰهُ الصَّمَدُ",                      "en": "Allah, the Eternal Refuge.",                    "ref": "112:2", "surah": 112, "ayah": 2},
        {"ar": "لَمْ يَلِدْ وَلَمْ يُولَدْ",             "en": "He neither begetsnor is born.",                "ref": "112:3", "surah": 112, "ayah": 3},
        {"ar": "وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ",      "en": "Nor is there to Himany equivalent.",           "ref": "112:4", "surah": 112, "ayah": 4},
    ]},

    # 4 ─ Ayat Al-Kursi
    {"title": "Ayat Al-Kursi — The Throne Verse", "verses": [
        {"ar": "اللّٰهُ لَا إِلٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ", "en": "Allah — there is no deity except Him,the Ever-Living, the Sustainer.", "ref": "2:255a", "surah": 2, "ayah": 255},
        {"ar": "لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ",       "en": "Neither drowsiness overtakes Himnor sleep.",                     "ref": "2:255b", "surah": 2, "ayah": 255},
        {"ar": "لَّهُ مَا فِي السَّمٰوَاتِ وَمَا فِي الْأَرْضِ", "en": "To Him belongs whatever isin the heavens and earth.",       "ref": "2:255c", "surah": 2, "ayah": 255},
        {"ar": "مَن ذَا الَّذِي يَشْفَعُ عِندَهُ إِلَّا بِإِذْنِهِ", "en": "Who is it that can intercedewith Him except by His permission?", "ref": "2:255d", "surah": 2, "ayah": 255},
        {"ar": "يَعْلَمُ مَا بَيْنَ أَيْدِيهِمْ وَمَا خَلْفَهُمْ", "en": "He knows what is before themand what is behind them.",        "ref": "2:255e", "surah": 2, "ayah": 255},
        {"ar": "وَلَا يُحِيطُونَ بِشَيْءٍ مِّنْ عِلْمِهِ إِلَّا بِمَا شَاءَ", "en": "And they encompass nothingof His knowledge except what He wills.", "ref": "2:255f", "surah": 2, "ayah": 255},
        {"ar": "وَسِعَ كُرْسِيُّهُ السَّمٰوَاتِ وَالْأَرْضَ", "en": "His Throne extends overthe heavens and the earth.",          "ref": "2:255g", "surah": 2, "ayah": 255},
        {"ar": "وَلَا يَئُودُهُ حِفْظُهُمَا وَهُوَ الْعَلِيُّ الْعَظِيمُ", "en": "And their preservation does not tire Him.He is the Most High, the Most Great.", "ref": "2:255h", "surah": 2, "ayah": 255},
    ]},

    # 5 ─ Lumière et guidance
    {"title": "Light and Guidance", "verses": [
        {"ar": "اللّٰهُ نُورُ السَّمٰوَاتِ وَالْأَرْضِ",   "en": "Allah is the Lightof the heavens and the earth.",              "ref": "24:35a", "surah": 24, "ayah": 35},
        {"ar": "مَثَلُ نُورِهِ كَمِشْكَاةٍ فِيهَا مِصْبَاحٌ", "en": "The example of His light is likea niche within which is a lamp.",    "ref": "24:35b", "surah": 24, "ayah": 35},
        {"ar": "الْمِصْبَاحُ فِي زُجَاجَةٍ",               "en": "The lamp is within glass.",                                     "ref": "24:35c", "surah": 24, "ayah": 35},
        {"ar": "الزُّجَاجَةُ كَأَنَّهَا كَوْكَبٌ دُرِّيٌّ", "en": "The glass is like a brilliant star.",                           "ref": "24:35d", "surah": 24, "ayah": 35},
        {"ar": "يَهْدِي اللّٰهُ لِنُورِهِ مَن يَشَاءُ",    "en": "Allah guides to His lightwhom He wills.",                       "ref": "24:35e", "surah": 24, "ayah": 35},
    ]},

    # 6 ─ La création — Sourate Qaf
    {"title": "The Greatness of Creation", "verses": [
        {"ar": "أَفَلَمْ يَنظُرُوا إِلَى السَّمَاءِ فَوْقَهُمْ", "en": "Do they not look at the sky above them —", "ref": "50:6a", "surah": 50, "ayah": 6},
        {"ar": "كَيْفَ بَنَيْنَاهَا وَزَيَّنَّاهَا",           "en": "how We have built itand adorned it?",                          "ref": "50:6b", "surah": 50, "ayah": 6},
        {"ar": "وَمَا لَهَا مِن فُرُوجٍ",                     "en": "And there are no riftswithin it.",                             "ref": "50:6c", "surah": 50, "ayah": 6},
        {"ar": "وَالْأَرْضَ مَدَدْنَاهَا وَأَلْقَيْنَا فِيهَا رَوَاسِيَ", "en": "And the earth — We spread it outand cast therein firmly set mountains.", "ref": "50:7a", "surah": 50, "ayah": 7},
        {"ar": "وَأَنبَتْنَا فِيهَا مِن كُلِّ زَوْجٍ بَهِيجٍ", "en": "And We caused to grow thereinevery beautiful kind of plant.", "ref": "50:7b", "surah": 50, "ayah": 7},
    ]},

    # 7 ─ La miséricorde divine — Az-Zumar 53
    {"title": "Divine Mercy", "verses": [
        {"ar": "قُلْ يَا عِبَادِيَ الَّذِينَ أَسْرَفُوا عَلَىٰ أَنفُسِهِمْ", "en": "Say: O My servants who havetransgressed against themselves,", "ref": "39:53a", "surah": 39, "ayah": 53},
        {"ar": "لَا تَقْنَطُوا مِن رَّحْمَةِ اللّٰهِ",       "en": "do not despairof the mercy of Allah.",                         "ref": "39:53b", "surah": 39, "ayah": 53},
        {"ar": "إِنَّ اللّٰهَ يَغْفِرُ الذُّنُوبَ جَمِيعًا", "en": "Indeed, Allah forgivesall sins.",                              "ref": "39:53c", "surah": 39, "ayah": 53},
        {"ar": "إِنَّهُ هُوَ الْغَفُورُ الرَّحِيمُ",          "en": "Indeed, it is He who isthe Forgiving, the Merciful.",           "ref": "39:53d", "surah": 39, "ayah": 53},
    ]},

    # 8 ─ Al-Falaq — L'aube
    {"title": "Al-Falaq — The Daybreak", "verses": [
        {"ar": "قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ",             "en": "Say: I seek refugein the Lord of the daybreak,",               "ref": "113:1", "surah": 113, "ayah": 1},
        {"ar": "مِن شَرِّ مَا خَلَقَ",                       "en": "From the evilof what He created,",                           "ref": "113:2", "surah": 113, "ayah": 2},
        {"ar": "وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ",           "en": "And from the evilof darkness when it settles,",               "ref": "113:3", "surah": 113, "ayah": 3},
        {"ar": "وَمِن شَرِّ النَّفَّاثَاتِ فِي الْعُقَدِ",   "en": "And from the evilof those who blow on knots,",                "ref": "113:4", "surah": 113, "ayah": 4},
        {"ar": "وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ",           "en": "And from the evilof an envier when he envies.",               "ref": "113:5", "surah": 113, "ayah": 5},
    ]},

    # 9 ─ An-Nas — Les hommes
    {"title": "An-Nas — Mankind", "verses": [
        {"ar": "قُلْ أَعُوذُ بِرَبِّ النَّاسِ",              "en": "Say: I seek refugein the Lord of mankind,",                    "ref": "114:1", "surah": 114, "ayah": 1},
        {"ar": "مَلِكِ النَّاسِ",                             "en": "The Sovereign of mankind,",                                     "ref": "114:2", "surah": 114, "ayah": 2},
        {"ar": "إِلٰهِ النَّاسِ",                             "en": "The God of mankind,",                                           "ref": "114:3", "surah": 114, "ayah": 3},
        {"ar": "مِن شَرِّ الْوَسْوَاسِ الْخَنَّاسِ",         "en": "From the evilof the retreating whisperer,",                   "ref": "114:4", "surah": 114, "ayah": 4},
        {"ar": "الَّذِي يُوَسْوِسُ فِي صُدُورِ النَّاسِ",    "en": "Who whispers in the heartsof mankind,",                       "ref": "114:5", "surah": 114, "ayah": 5},
        {"ar": "مِنَ الْجِنَّةِ وَالنَّاسِ",                 "en": "From among the jinnand mankind.",                             "ref": "114:6", "surah": 114, "ayah": 6},
    ]},

    # 10 ─ La gratitude — Ibrahim 7
    {"title": "Gratitude", "verses": [
        {"ar": "وَإِذْ تَأَذَّنَ رَبُّكُمْ",                 "en": "And when your Lord proclaimed:",                                 "ref": "14:7a", "surah": 14, "ayah": 7},
        {"ar": "لَئِن شَكَرْتُمْ لَأَزِيدَنَّكُمْ",         "en": "If you are grateful,I will surely increase you in favor.",    "ref": "14:7b", "surah": 14, "ayah": 7},
        {"ar": "وَلَئِن كَفَرْتُمْ إِنَّ عَذَابِي لَشَدِيدٌ", "en": "But if you deny,indeed, My punishment is severe.", "ref": "14:7c", "surah": 14, "ayah": 7},
        {"ar": "فَإِنَّ اللّٰهَ لَغَنِيٌّ حَمِيدٌ",         "en": "Indeed, Allah is Free of needand Praiseworthy.",               "ref": "14:8b", "surah": 14, "ayah": 8},
    ]},

    # 11 ─ Al-Mulk — La Royauté
    {"title": "Al-Mulk — Sovereignty", "verses": [
        {"ar": "تَبَارَكَ الَّذِي بِيَدِهِ الْمُلْكُ وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "en": "Blessed is He in whose hand is dominion,and He is over all things competent.", "ref": "67:1", "surah": 67, "ayah": 1},
        {"ar": "الَّذِي خَلَقَ الْمَوْتَ وَالْحَيَاةَ",     "en": "He who created deathand life to test you —",                   "ref": "67:2a", "surah": 67, "ayah": 2},
        {"ar": "لِيَبْلُوَكُمْ أَيُّكُمْ أَحْسَنُ عَمَلًا", "en": "which of you is best in deed.",                                  "ref": "67:2b", "surah": 67, "ayah": 2},
        {"ar": "وَهُوَ الْعَزِيزُ الْغَفُورُ",               "en": "And He is the Exalted in Might,the Forgiving.",               "ref": "67:2c", "surah": 67, "ayah": 2},
        {"ar": "الَّذِي خَلَقَ سَبْعَ سَمٰوَاتٍ طِبَاقًا",  "en": "He who created seven heavensin layers.",                       "ref": "67:3a", "surah": 67, "ayah": 3},
        {"ar": "مَّا تَرَىٰ فِي خَلْقِ الرَّحْمٰنِ مِن تَفَاوُتٍ", "en": "You do not see in the creationof the Most Merciful any inconsistency.", "ref": "67:3b", "surah": 67, "ayah": 3},
    ]},

    # 12 ─ Al-Baqarah 286 — Le pardon
    {"title": "Forgiveness and Mercy", "verses": [
        {"ar": "لَا يُكَلِّفُ اللّٰهُ نَفْسًا إِلَّا وُسْعَهَا", "en": "Allah does not burden a soulbeyond that it can bear.", "ref": "2:286a", "surah": 2, "ayah": 286},
        {"ar": "رَبَّنَا لَا تُؤَاخِذْنَا إِن نَّسِينَا أَوْ أَخْطَأْنَا", "en": "Our Lord, do not impose blame on usif we have forgotten or erred.", "ref": "2:286b", "surah": 2, "ayah": 286},
        {"ar": "رَبَّنَا وَلَا تَحْمِلْ عَلَيْنَا إِصْرًا",    "en": "Our Lord, and lay not upon usa burden like that You laid upon those before us.", "ref": "2:286c", "surah": 2, "ayah": 286},
        {"ar": "رَبَّنَا وَلَا تُحَمِّلْنَا مَا لَا طَاقَةَ لَنَا بِهِ", "en": "Our Lord, and burden us notwith that which we have no ability to bear.", "ref": "2:286d", "surah": 2, "ayah": 286},
        {"ar": "وَاعْفُ عَنَّا وَاغْفِرْ لَنَا وَارْحَمْنَا", "en": "And pardon us,forgive us, and have mercy upon us.",           "ref": "2:286e", "surah": 2, "ayah": 286},
        {"ar": "أَنتَ مَوْلَانَا فَانصُرْنَا عَلَى الْقَوْمِ الْكَافِرِينَ", "en": "You are our protector,so give us victory over the disbelieving people.", "ref": "2:286f", "surah": 2, "ayah": 286},
    ]},

    # 13 ─ Rappel du Seigneur — Ar-Ra'd 28
    {"title": "Peace of the Heart", "verses": [
        {"ar": "الَّذِينَ آمَنُوا وَتَطْمَئِنُّ قُلُوبُهُم بِذِكْرِ اللّٰهِ", "en": "Those who believe and whose heartsare assured by the remembrance of Allah.", "ref": "13:28a", "surah": 13, "ayah": 28},
        {"ar": "أَلَا بِذِكْرِ اللّٰهِ تَطْمَئِنُّ الْقُلُوبُ", "en": "Unquestionably, by the remembranceof Allah, hearts are assured.", "ref": "13:28b", "surah": 13, "ayah": 28},
        {"ar": "الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ",   "en": "Those who believedand did righteous deeds —",                  "ref": "13:29a", "surah": 13, "ayah": 29},
        {"ar": "طُوبَىٰ لَهُمْ وَحُسْنُ مَآبٍ",               "en": "Happiness is for themand a beautiful place of return.",          "ref": "13:29b", "surah": 13, "ayah": 29},
    ]},

    # 14 ─ Yusuf 87 — Ne pas désespérer
    {"title": "Never Lose Hope", "verses": [
        {"ar": "يَا بَنِيَّ اذْهَبُوا فَتَحَسَّسُوا مِن يُوسُفَ وَأَخِيهِ", "en": "O my sons, go and searchfor Joseph and his brother,", "ref": "12:87a", "surah": 12, "ayah": 87},
        {"ar": "وَلَا تَيْأَسُوا مِن رَّوْحِ اللّٰهِ", "en": "and do not despairof relief from Allah.", "ref": "12:87b", "surah": 12, "ayah": 87},
        {"ar": "إِنَّهُ لَا يَيْأَسُ مِن رَّوْحِ اللّٰهِ إِلَّا الْقَوْمُ الْكَافِرُونَ", "en": "Indeed, no one despairsof relief from Allah exceptthe disbelieving people.", "ref": "12:87c", "surah": 12, "ayah": 87},
    ]},

    # 15 ─ Al-Baqarah 153 — Patience et prière
    {"title": "Patience and Prayer", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ", "en": "O you who have believed,seek help through patienceand prayer.", "ref": "2:153a", "surah": 2, "ayah": 153},
        {"ar": "إِنَّ اللّٰهَ مَعَ الصَّابِرِينَ", "en": "Indeed, Allah is withthe patient.", "ref": "2:153b", "surah": 2, "ayah": 153},
    ]},

    # 16 ─ Al-Hajj 46 — Le cœur qui voit
    {"title": "The Heart that Understands", "verses": [
        {"ar": "أَفَلَمْ يَسِيرُوا فِي الْأَرْضِ", "en": "Have they not traveledthrough the land?", "ref": "22:46a", "surah": 22, "ayah": 46},
        {"ar": "فَتَكُونَ لَهُمْ قُلُوبٌ يَعْقِلُونَ بِهَا", "en": "So that their heartsmay reason with it,", "ref": "22:46b", "surah": 22, "ayah": 46},
        {"ar": "فَإِنَّهَا لَا تَعْمَى الْأَبْصَارُ", "en": "For indeed, it is not the eyesthat are blinded,", "ref": "22:46c", "surah": 22, "ayah": 46},
        {"ar": "وَلَٰكِن تَعْمَى الْقُلُوبُ الَّتِي فِي الصُّدُورِ", "en": "But it is the hearts,which are in the chests,that are blinded.", "ref": "22:46d", "surah": 22, "ayah": 46},
    ]},

    # 17 ─ Al-Imran 173 — La confiance absolue
    {"title": "Hasbunallah — Allah is Enough", "verses": [
        {"ar": "الَّذِينَ قَالَ لَهُمُ النَّاسُ إِنَّ النَّاسَ قَدْ جَمَعُوا لَكُمْ", "en": "Those to whom people said:the people have gatheredagainst you,", "ref": "3:173a", "surah": 3, "ayah": 173},
        {"ar": "فَاخْشَوْهُمْ فَزَادَهُمْ إِيمَانًا", "en": "So fear them —but it only increased themin faith,", "ref": "3:173b", "surah": 3, "ayah": 173},
        {"ar": "وَقَالُوا حَسْبُنَا اللّٰهُ وَنِعْمَ الْوَكِيلُ", "en": "And they said:Allah is sufficient for us,and He is the best disposer.", "ref": "3:173c", "surah": 3, "ayah": 173},
    ]},

    # 18 ─ Az-Zumar 9 — La science et l'adoration
    {"title": "Knowledge and Prostration", "verses": [
        {"ar": "أَمَّنْ هُوَ قَانِتٌ آنَاءَ اللَّيْلِ سَاجِدًا وَقَائِمًا", "en": "Is one who is devout in hoursof the night, prostratingand standing in prayer,", "ref": "39:9a", "surah": 39, "ayah": 9},
        {"ar": "يَحْذَرُ الْآخِرَةَ وَيَرْجُو رَحْمَةَ رَبِّهِ", "en": "Fearing the Hereafterand hoping for the mercyof his Lord?", "ref": "39:9b", "surah": 39, "ayah": 9},
        {"ar": "قُلْ هَلْ يَسْتَوِي الَّذِينَ يَعْلَمُونَ وَالَّذِينَ لَا يَعْلَمُونَ", "en": "Say: Are those who knowequal to those who do not know?", "ref": "39:9c", "surah": 39, "ayah": 9},
    ]},

    # 19 ─ Al-Imran 8 — Ne pas faire dévier les cœurs
    {"title": "Steadfast Hearts", "verses": [
        {"ar": "رَبَّنَا لَا تُزِغْ قُلُوبَنَا بَعْدَ إِذْ هَدَيْتَنَا", "en": "Our Lord, do not letour hearts deviate afterYou have guided us,", "ref": "3:8a", "surah": 3, "ayah": 8},
        {"ar": "وَهَبْ لَنَا مِن لَّدُنكَ رَحْمَةً", "en": "And grant us from Yourselfmercy.", "ref": "3:8b", "surah": 3, "ayah": 8},
        {"ar": "إِنَّكَ أَنتَ الْوَهَّابُ", "en": "Indeed, You are the Bestower.", "ref": "3:8c", "surah": 3, "ayah": 8},
    ]},

    # 20 ─ Al-Muzzammil 8 — Invoquer et se confier
    {"title": "Turning to Allah", "verses": [
        {"ar": "وَاذْكُرِ اسْمَ رَبِّكَ وَتَبَتَّلْ إِلَيْهِ تَبْتِيلًا", "en": "And remember the nameof your Lord and devote yourselfto Him with complete devotion.", "ref": "73:8", "surah": 73, "ayah": 8},
        {"ar": "رَّبُّ الْمَشْرِقِ وَالْمَغْرِبِ لَا إِلَٰهَ إِلَّا هُوَ", "en": "Lord of the East and the West —there is no deity except Him,", "ref": "73:9a", "surah": 73, "ayah": 9},
        {"ar": "فَاتَّخِذْهُ وَكِيلًا", "en": "So take Him as Disposerof your affairs.", "ref": "73:9b", "surah": 73, "ayah": 9},
    ]},

    # 21 ─ Al-Baqarah 186 — Allah répond
    {"title": "Allah Hears Your Prayer", "verses": [
        {"ar": "وَإِذَا سَأَلَكَ عِبَادِي عَنِّي فَإِنِّي قَرِيبٌ", "en": "And when My servants ask youabout Me — indeed I am near.", "ref": "2:186a", "surah": 2, "ayah": 186},
        {"ar": "أُجِيبُ دَعْوَةَ الدَّاعِ إِذَا دَعَانِ", "en": "I respond to the invocationof the supplicant when he calls Me.", "ref": "2:186b", "surah": 2, "ayah": 186},
        {"ar": "فَلْيَسْتَجِيبُوا لِي وَلْيُؤْمِنُوا بِي", "en": "So let them respond to Meand believe in Me,", "ref": "2:186c", "surah": 2, "ayah": 186},
        {"ar": "لَعَلَّهُمْ يَرْشُدُونَ", "en": "That they may be guided.", "ref": "2:186d", "surah": 2, "ayah": 186},
    ]},

    # 22 ─ Fussilat 30 — Les anges descendent
    {"title": "The Angels and the Believers", "verses": [
        {"ar": "إِنَّ الَّذِينَ قَالُوا رَبُّنَا اللّٰهُ ثُمَّ اسْتَقَامُوا", "en": "Indeed, those who saidour Lord is Allah and thenstayed on course —", "ref": "41:30a", "surah": 41, "ayah": 30},
        {"ar": "تَتَنَزَّلُ عَلَيْهِمُ الْمَلَائِكَةُ", "en": "The angels will descendupon them,", "ref": "41:30b", "surah": 41, "ayah": 30},
        {"ar": "أَلَّا تَخَافُوا وَلَا تَحْزَنُوا", "en": "Saying: do not fearand do not grieve,", "ref": "41:30c", "surah": 41, "ayah": 30},
        {"ar": "وَأَبْشِرُوا بِالْجَنَّةِ الَّتِي كُنتُمْ تُوعَدُونَ", "en": "But receive good tidingsof Paradise which youwere promised.", "ref": "41:30d", "surah": 41, "ayah": 30},
    ]},

    # 23 ─ Al-Hashr 22-23 — Les noms d'Allah
    {"title": "The Beautiful Names of Allah", "verses": [
        {"ar": "هُوَ اللّٰهُ الَّذِي لَا إِلَٰهَ إِلَّا هُوَ", "en": "He is Allah — there is no deityexcept Him,", "ref": "59:22a", "surah": 59, "ayah": 22},
        {"ar": "عَالِمُ الْغَيْبِ وَالشَّهَادَةِ", "en": "Knower of the unseenand the witnessed.", "ref": "59:22b", "surah": 59, "ayah": 22},
        {"ar": "هُوَ الرَّحْمَٰنُ الرَّحِيمُ", "en": "He is the Most Gracious,the Most Merciful.", "ref": "59:22c", "surah": 59, "ayah": 22},
        {"ar": "هُوَ اللّٰهُ الَّذِي لَا إِلَٰهَ إِلَّا هُوَ الْمَلِكُ الْقُدُّوسُ السَّلَامُ", "en": "He is Allah — no deity except Him,the Sovereign, the Pure,the Perfection.", "ref": "59:23a", "surah": 59, "ayah": 23},
        {"ar": "الْمُؤْمِنُ الْمُهَيْمِنُ الْعَزِيزُ الْجَبَّارُ الْمُتَكَبِّرُ", "en": "The Grantor of security,the Overseer, the Exalted,the Compeller, the Superior.", "ref": "59:23b", "surah": 59, "ayah": 23},
    ]},

    # 24 ─ Al-Duha — Le matin
    {"title": "Al-Duha — The Morning", "verses": [
        {"ar": "وَالضُّحَىٰ", "en": "By the morning brightness,", "ref": "93:1", "surah": 93, "ayah": 1},
        {"ar": "وَاللَّيْلِ إِذَا سَجَىٰ", "en": "And by the night when it covers with darkness,", "ref": "93:2", "surah": 93, "ayah": 2},
        {"ar": "مَا وَدَّعَكَ رَبُّكَ وَمَا قَلَىٰ", "en": "Your Lord has not taken leave of you,nor has He detested you.", "ref": "93:3", "surah": 93, "ayah": 3},
        {"ar": "وَلَلْآخِرَةُ خَيْرٌ لَّكَ مِنَ الْأُولَىٰ", "en": "And the Hereafter is better for youthan the first life.", "ref": "93:4", "surah": 93, "ayah": 4},
        {"ar": "وَلَسَوْفَ يُعْطِيكَ رَبُّكَ فَتَرْضَىٰ", "en": "And your Lord is going to give you,and you will be satisfied.", "ref": "93:5", "surah": 93, "ayah": 5},
        {"ar": "أَلَمْ يَجِدْكَ يَتِيمًا فَآوَىٰ", "en": "Did He not find you an orphanand give refuge?", "ref": "93:6", "surah": 93, "ayah": 6},
        {"ar": "وَوَجَدَكَ ضَالًّا فَهَدَىٰ", "en": "And He found you lostand guided you,", "ref": "93:7", "surah": 93, "ayah": 7},
        {"ar": "وَوَجَدَكَ عَائِلًا فَأَغْنَىٰ", "en": "And He found you poorand made you self-sufficient.", "ref": "93:8", "surah": 93, "ayah": 8},
    ]},

    # 25 ─ Al-Kahf 10 — La caverne
    {"title": "Refuge and Guidance", "verses": [
        {"ar": "إِذْ أَوَى الْفِتْيَةُ إِلَى الْكَهْفِ فَقَالُوا", "en": "When the youths retreatedto the cave and said:", "ref": "18:10a", "surah": 18, "ayah": 10},
        {"ar": "رَبَّنَا آتِنَا مِن لَّدُنكَ رَحْمَةً", "en": "Our Lord, grant usfrom Yourself mercy,", "ref": "18:10b", "surah": 18, "ayah": 10},
        {"ar": "وَهَيِّئْ لَنَا مِنْ أَمْرِنَا رَشَدًا", "en": "And prepare for usfrom our affair right guidance.", "ref": "18:10c", "surah": 18, "ayah": 10},
    ]},

    # 26 ─ Al-Zilzalah — Le Séisme
    {"title": "Al-Zilzalah — The Earthquake", "verses": [
        {"ar": "إِذَا زُلْزِلَتِ الْأَرْضُ زِلْزَالَهَا", "en": "When the earth is shakenwith its final earthquake,", "ref": "99:1", "surah": 99, "ayah": 1},
        {"ar": "وَأَخْرَجَتِ الْأَرْضُ أَثْقَالَهَا", "en": "And the earth brings outits burdens,", "ref": "99:2", "surah": 99, "ayah": 2},
        {"ar": "وَقَالَ الْإِنسَانُ مَا لَهَا", "en": "And man says:what is wrong with it?", "ref": "99:3", "surah": 99, "ayah": 3},
        {"ar": "يَوْمَئِذٍ تُحَدِّثُ أَخْبَارَهَا", "en": "That day, it will reportits news,", "ref": "99:4", "surah": 99, "ayah": 4},
        {"ar": "بِأَنَّ رَبَّكَ أَوْحَىٰ لَهَا", "en": "Because your Lordhas inspired it.", "ref": "99:5", "surah": 99, "ayah": 5},
        {"ar": "يَوْمَئِذٍ يَصْدُرُ النَّاسُ أَشْتَاتًا لِّيُرَوْا أَعْمَالَهُمْ", "en": "That day, the people will departseparated to be shownthe result of their deeds.", "ref": "99:6", "surah": 99, "ayah": 6},
        {"ar": "فَمَن يَعْمَلْ مِثْقَالَ ذَرَّةٍ خَيْرًا يَرَهُ", "en": "Whoever does an atom's weightof good will see it,", "ref": "99:7", "surah": 99, "ayah": 7},
        {"ar": "وَمَن يَعْمَلْ مِثْقَالَ ذَرَّةٍ شَرًّا يَرَهُ", "en": "And whoever does an atom's weightof evil will see it.", "ref": "99:8", "surah": 99, "ayah": 8},
    ]},

    # 27 ─ Al-Asr — Le Temps
    {"title": "Al-Asr — Time", "verses": [
        {"ar": "وَالْعَصْرِ", "en": "By time,", "ref": "103:1", "surah": 103, "ayah": 1},
        {"ar": "إِنَّ الْإِنسَانَ لَفِي خُسْرٍ", "en": "Indeed, mankind is in loss,", "ref": "103:2", "surah": 103, "ayah": 2},
        {"ar": "إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ", "en": "Except for those who have believedand done righteous deeds,", "ref": "103:3", "surah": 103, "ayah": 3},
        {"ar": "وَتَوَاصَوْا بِالْحَقِّ وَتَوَاصَوْا بِالصَّبْرِ", "en": "And advised each other to truthand advised each other to patience.", "ref": "103:3b", "surah": 103, "ayah": 3},
    ]},

    # 28 ─ Al-Qadr — La Nuit du Destin
    {"title": "Laylat Al-Qadr — Night of Decree", "verses": [
        {"ar": "إِنَّا أَنزَلْنَاهُ فِي لَيْلَةِ الْقَدْرِ", "en": "Indeed, We sent it downduring the Night of Decree.", "ref": "97:1", "surah": 97, "ayah": 1},
        {"ar": "وَمَا أَدْرَاكَ مَا لَيْلَةُ الْقَدْرِ", "en": "And what can make you knowwhat is the Night of Decree?", "ref": "97:2", "surah": 97, "ayah": 2},
        {"ar": "لَيْلَةُ الْقَدْرِ خَيْرٌ مِّنْ أَلْفِ شَهْرٍ", "en": "The Night of Decree is betterthan a thousand months.", "ref": "97:3", "surah": 97, "ayah": 3},
        {"ar": "تَنَزَّلُ الْمَلَائِكَةُ وَالرُّوحُ فِيهَا بِإِذْنِ رَبِّهِم", "en": "The angels and the Spirit descendtherein by permission of their Lord.", "ref": "97:4", "surah": 97, "ayah": 4},
        {"ar": "سَلَامٌ هِيَ حَتَّىٰ مَطْلَعِ الْفَجْرِ", "en": "Peace it is untilthe emergence of dawn.", "ref": "97:5", "surah": 97, "ayah": 5},
    ]},

    # 29 ─ Ar-Rahman — Le Bienfaiteur (55:1-13, consécutifs)
    {"title": "Ar-Rahman — The Most Merciful", "verses": [
        {"ar": "الرَّحْمَٰنُ", "en": "The Most Merciful", "ref": "55:1", "surah": 55, "ayah": 1},
        {"ar": "عَلَّمَ الْقُرْآنَ", "en": "Taught the Qur'an,", "ref": "55:2", "surah": 55, "ayah": 2},
        {"ar": "خَلَقَ الْإِنسَانَ", "en": "Created man,", "ref": "55:3", "surah": 55, "ayah": 3},
        {"ar": "عَلَّمَهُ الْبَيَانَ", "en": "Taught him eloquence.", "ref": "55:4", "surah": 55, "ayah": 4},
        {"ar": "الشَّمْسُ وَالْقَمَرُ بِحُسْبَانٍ", "en": "The sun and the moonrun on precise courses.", "ref": "55:5", "surah": 55, "ayah": 5},
        {"ar": "وَالنَّجْمُ وَالشَّجَرُ يَسْجُدَانِ", "en": "And the stars and treesprostrate themselves.", "ref": "55:6", "surah": 55, "ayah": 6},
        {"ar": "وَالسَّمَاءَ رَفَعَهَا وَوَضَعَ الْمِيزَانَ", "en": "And the sky He raisedand He set the balance.", "ref": "55:7", "surah": 55, "ayah": 7},
        {"ar": "أَلَّا تَطْغَوْا فِي الْمِيزَانِ", "en": "That you do not transgressthe balance.", "ref": "55:8", "surah": 55, "ayah": 8},
        {"ar": "وَأَقِيمُوا الْوَزْنَ بِالْقِسْطِ وَلَا تُخْسِرُوا الْمِيزَانَ", "en": "And establish weight in justiceand do not make deficient the balance.", "ref": "55:9", "surah": 55, "ayah": 9},
        {"ar": "وَالْأَرْضَ وَضَعَهَا لِلْأَنَامِ", "en": "And the earth He laidfor the creatures.", "ref": "55:10", "surah": 55, "ayah": 10},
        {"ar": "فِيهَا فَاكِهَةٌ وَالنَّخْلُ ذَاتُ الْأَكْمَامِ", "en": "Therein is fruitand palm trees with sheaths,", "ref": "55:11", "surah": 55, "ayah": 11},
        {"ar": "وَالْحَبُّ ذُو الْعَصْفِ وَالرَّيْحَانُ", "en": "And grain with husksand fragrant plants.", "ref": "55:12", "surah": 55, "ayah": 12},
        {"ar": "فَبِأَيِّ آلَاءِ رَبِّكُمَا تُكَذِّبَانِ", "en": "So which of the favorsof your Lord would you deny?", "ref": "55:13", "surah": 55, "ayah": 13},
    ]},

    # 30 ─ Al-Insan — La générosité des croyants
    {"title": "Sincere Generosity", "verses": [
        {"ar": "وَيُطْعِمُونَ الطَّعَامَ عَلَىٰ حُبِّهِ مِسْكِينًا وَيَتِيمًا وَأَسِيرًا", "en": "And they give food, in spite of love for it,to the needy, the orphan, and the captive,", "ref": "76:8", "surah": 76, "ayah": 8},
        {"ar": "إِنَّمَا نُطْعِمُكُمْ لِوَجْهِ اللّٰهِ", "en": "Saying: we feed youonly for the countenance of Allah.", "ref": "76:9a", "surah": 76, "ayah": 9},
        {"ar": "لَا نُرِيدُ مِنكُمْ جَزَاءً وَلَا شُكُورًا", "en": "We wish not from youreward or gratitude.", "ref": "76:9b", "surah": 76, "ayah": 9},
        {"ar": "إِنَّا نَخَافُ مِن رَّبِّنَا يَوْمًا عَبُوسًا قَمْطَرِيرًا", "en": "Indeed, we fear from our Lorda Day austere and distressful.", "ref": "76:10", "surah": 76, "ayah": 10},
    ]},

    # 31 ─ Al-Baqarah 45-46 — La patience et la salat
    {"title": "Salah — The Bond with Allah", "verses": [
        {"ar": "وَاسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ", "en": "And seek help throughpatience and prayer.", "ref": "2:45a", "surah": 2, "ayah": 45},
        {"ar": "وَإِنَّهَا لَكَبِيرَةٌ إِلَّا عَلَى الْخَاشِعِينَ", "en": "And indeed it is difficultexcept for the humbly submissive.", "ref": "2:45b", "surah": 2, "ayah": 45},
        {"ar": "الَّذِينَ يَظُنُّونَ أَنَّهُم مُّلَاقُو رَبِّهِمْ", "en": "Who are certain that theywill meet their Lord,", "ref": "2:46a", "surah": 2, "ayah": 46},
        {"ar": "وَأَنَّهُمْ إِلَيْهِ رَاجِعُونَ", "en": "And that they willreturn to Him.", "ref": "2:46b", "surah": 2, "ayah": 46},
    ]},

    # 32 ─ Ibrahim 24-25 — La bonne parole
    {"title": "The Good Word", "verses": [
        {"ar": "أَلَمْ تَرَ كَيْفَ ضَرَبَ اللّٰهُ مَثَلًا كَلِمَةً طَيِّبَةً", "en": "Have you not considered howAllah presents an example —a good word,", "ref": "14:24a", "surah": 14, "ayah": 24},
        {"ar": "كَشَجَرَةٍ طَيِّبَةٍ أَصْلُهَا ثَابِتٌ وَفَرْعُهَا فِي السَّمَاءِ", "en": "Like a good tree,whose root is firmly fixedand its branches are toward the sky,", "ref": "14:24b", "surah": 14, "ayah": 24},
        {"ar": "تُؤْتِي أُكُلَهَا كُلَّ حِينٍ بِإِذْنِ رَبِّهَا", "en": "Producing its fruitevery seasonby permission of its Lord.", "ref": "14:25a", "surah": 14, "ayah": 25},
        {"ar": "وَيَضْرِبُ اللّٰهُ الْأَمْثَالَ لِلنَّاسِ لَعَلَّهُمْ يَتَذَكَّرُونَ", "en": "And Allah presents examplesfor the people that perhapsthey will be reminded.", "ref": "14:25b", "surah": 14, "ayah": 25},
    ]},

    # 33 ─ Al-Qiyamah — La Résurrection
    {"title": "The Resurrection", "verses": [
        {"ar": "لَا أُقْسِمُ بِيَوْمِ الْقِيَامَةِ", "en": "I swear by the Dayof Resurrection,", "ref": "75:1", "surah": 75, "ayah": 1},
        {"ar": "وَلَا أُقْسِمُ بِالنَّفْسِ اللَّوَّامَةِ", "en": "And I swear by theself-reproaching soul.", "ref": "75:2", "surah": 75, "ayah": 2},
        {"ar": "أَيَحْسَبُ الْإِنسَانُ أَلَّن نَّجْمَعَ عِظَامَهُ", "en": "Does man think that We will notassemble his bones?", "ref": "75:3", "surah": 75, "ayah": 3},
        {"ar": "بَلَىٰ قَادِرِينَ عَلَىٰ أَن نُّسَوِّيَ بَنَانَهُ", "en": "Yes, We are able to puttogether even his fingertips.", "ref": "75:4", "surah": 75, "ayah": 4},
    ]},

    # 34 ─ Al-Fajr — L'Aurore
    {"title": "Al-Fajr — The Dawn", "verses": [
        {"ar": "يَا أَيَّتُهَا النَّفْسُ الْمُطْمَئِنَّةُ", "en": "O reassured soul,", "ref": "89:27", "surah": 89, "ayah": 27},
        {"ar": "ارْجِعِي إِلَىٰ رَبِّكِ رَاضِيَةً مَّرْضِيَّةً", "en": "Return to your Lordwell-pleased and pleasing to Him,", "ref": "89:28", "surah": 89, "ayah": 28},
        {"ar": "فَادْخُلِي فِي عِبَادِي", "en": "And enter amongMy servants,", "ref": "89:29", "surah": 89, "ayah": 29},
        {"ar": "وَادْخُلِي جَنَّتِي", "en": "And enter My Paradise.", "ref": "89:30", "surah": 89, "ayah": 30},
    ]},

    # 35 ─ Al-Kawthar — L'Abondance
    {"title": "Al-Kawthar — Abundance", "verses": [
        {"ar": "إِنَّا أَعْطَيْنَاكَ الْكَوْثَرَ", "en": "Indeed, We have granted youAl-Kawthar.", "ref": "108:1", "surah": 108, "ayah": 1},
        {"ar": "فَصَلِّ لِرَبِّكَ وَانْحَرْ", "en": "So pray to your Lordand sacrifice.", "ref": "108:2", "surah": 108, "ayah": 2},
        {"ar": "إِنَّ شَانِئَكَ هُوَ الْأَبْتَرُ", "en": "Indeed, your enemy isthe one cut off.", "ref": "108:3", "surah": 108, "ayah": 3},
    ]},

    # 36 ─ An-Nasr — Le Secours
    {"title": "An-Nasr — The Victory", "verses": [
        {"ar": "إِذَا جَاءَ نَصْرُ اللّٰهِ وَالْفَتْحُ", "en": "When the victory of Allahhas come and the conquest,", "ref": "110:1", "surah": 110, "ayah": 1},
        {"ar": "وَرَأَيْتَ النَّاسَ يَدْخُلُونَ فِي دِينِ اللّٰهِ أَفْوَاجًا", "en": "And you see the people enteringinto the religion of Allah in multitudes,", "ref": "110:2", "surah": 110, "ayah": 2},
        {"ar": "فَسَبِّحْ بِحَمْدِ رَبِّكَ وَاسْتَغْفِرْهُ إِنَّهُ كَانَ تَوَّابًا", "en": "Then exalt Him with praise of your Lordand ask forgiveness of Him. Indeed, He is ever Accepting of repentance.", "ref": "110:3", "surah": 110, "ayah": 3},
    ]},

    # 37 ─ At-Tin — Le Figuier
    {"title": "At-Tin — The Fig", "verses": [
        {"ar": "لَقَدْ خَلَقْنَا الْإِنسَانَ فِي أَحْسَنِ تَقْوِيمٍ", "en": "We have certainly created manin the best of stature.", "ref": "95:4", "surah": 95, "ayah": 4},
        {"ar": "ثُمَّ رَدَدْنَاهُ أَسْفَلَ سَافِلِينَ", "en": "Then We return himto the lowest of the low,", "ref": "95:5", "surah": 95, "ayah": 5},
        {"ar": "إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ فَلَهُمْ أَجْرٌ غَيْرُ مَمْنُونٍ", "en": "Except for those who believeand do righteous deeds — for theywill have a reward uninterrupted.", "ref": "95:6", "surah": 95, "ayah": 6},
    ]},

    # 38 ─ Al-Layl 5-7 — Les chemins de la facilité
    {"title": "The Path of Ease", "verses": [
        {"ar": "فَأَمَّا مَنْ أَعْطَىٰ وَاتَّقَىٰ", "en": "As for he who givesand fears Allah", "ref": "92:5", "surah": 92, "ayah": 5},
        {"ar": "وَصَدَّقَ بِالْحُسْنَىٰ", "en": "And believes inthe best [reward],", "ref": "92:6", "surah": 92, "ayah": 6},
        {"ar": "فَسَنُيَسِّرُهُ لِلْيُسْرَىٰ", "en": "We will ease himtoward ease.", "ref": "92:7", "surah": 92, "ayah": 7},
    ]},

    # 39 ─ Al-Baqarah 152 — Le souvenir mutuel
    {"title": "Mutual Remembrance", "verses": [
        {"ar": "فَاذْكُرُونِي أَذْكُرْكُمْ", "en": "So remember Me;I will remember you.", "ref": "2:152a", "surah": 2, "ayah": 152},
        {"ar": "وَاشْكُرُوا لِي وَلَا تَكْفُرُونِ", "en": "And be grateful to Meand do not deny Me.", "ref": "2:152b", "surah": 2, "ayah": 152},
    ]},

    # 40 ─ At-Tawbah 51 — Ce qu'Allah a écrit
    {"title": "What Allah Has Decreed", "verses": [
        {"ar": "قُل لَّن يُصِيبَنَا إِلَّا مَا كَتَبَ اللّٰهُ لَنَا", "en": "Say: Nothing will befall usexcept what Allah has decreed for us;", "ref": "9:51a", "surah": 9, "ayah": 51},
        {"ar": "هُوَ مَوْلَانَا وَعَلَى اللّٰهِ فَلْيَتَوَكَّلِ الْمُؤْمِنُونَ", "en": "He is our protector. And upon Allahlet the believers rely.", "ref": "9:51b", "surah": 9, "ayah": 51},
    ]},

    # 41 ─ Ar-Ra'd 11 — Allah ne change pas l'état d'un peuple
    {"title": "Change Comes from Within", "verses": [
        {"ar": "إِنَّ اللّٰهَ لَا يُغَيِّرُ مَا بِقَوْمٍ حَتَّىٰ يُغَيِّرُوا مَا بِأَنفُسِهِمْ", "en": "Indeed, Allah will not change the conditionof a people until they changewhat is in themselves.", "ref": "13:11", "surah": 13, "ayah": 11},
    ]},

    # 42 ─ Al-Baqarah 255 (suite) — complète avec Ayat Al-Kursi déjà faite séparée
    # 42 ─ Al-Anfal 2-4 — Les vrais croyants
    {"title": "The True Believers", "verses": [
        {"ar": "إِنَّمَا الْمُؤْمِنُونَ الَّذِينَ إِذَا ذُكِرَ اللّٰهُ وَجِلَتْ قُلُوبُهُمْ", "en": "The believers are only those who,when Allah is mentioned,their hearts become fearful,", "ref": "8:2a", "surah": 8, "ayah": 2},
        {"ar": "وَإِذَا تُلِيَتْ عَلَيْهِمْ آيَاتُهُ زَادَتْهُمْ إِيمَانًا", "en": "And when His verses are recited to them,it increases them in faith,", "ref": "8:2b", "surah": 8, "ayah": 2},
        {"ar": "وَعَلَىٰ رَبِّهِمْ يَتَوَكَّلُونَ", "en": "And upon their Lordthey rely.", "ref": "8:2c", "surah": 8, "ayah": 2},
        {"ar": "الَّذِينَ يُقِيمُونَ الصَّلَاةَ وَمِمَّا رَزَقْنَاهُمْ يُنفِقُونَ", "en": "Those who establish prayerand spend from what Wehave provided them.", "ref": "8:3", "surah": 8, "ayah": 3},
        {"ar": "أُولَٰئِكَ هُمُ الْمُؤْمِنُونَ حَقًّا", "en": "Those are the believers, truly.", "ref": "8:4a", "surah": 8, "ayah": 4},
        {"ar": "لَّهُمْ دَرَجَاتٌ عِندَ رَبِّهِمْ وَمَغْفِرَةٌ وَرِزْقٌ كَرِيمٌ", "en": "For them are degrees of honorwith their Lord, and forgivenessand noble provision.", "ref": "8:4b", "surah": 8, "ayah": 4},
    ]},

    # 43 ─ Al-Hujurat 10-13 — La fraternité et l'honneur
    {"title": "Brotherhood in Islam", "verses": [
        {"ar": "إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ", "en": "The believers are but brothers,", "ref": "49:10a", "surah": 49, "ayah": 10},
        {"ar": "فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ", "en": "So make peace betweenyour brothers,", "ref": "49:10b", "surah": 49, "ayah": 10},
        {"ar": "وَاتَّقُوا اللّٰهَ لَعَلَّكُمْ تُرْحَمُونَ", "en": "And fear Allah that you mayreceive mercy.", "ref": "49:10c", "surah": 49, "ayah": 10},
        {"ar": "يَا أَيُّهَا النَّاسُ إِنَّا خَلَقْنَاكُم مِّن ذَكَرٍ وَأُنثَىٰ", "en": "O mankind, indeed We have created youfrom male and female,", "ref": "49:13a", "surah": 49, "ayah": 13},
        {"ar": "وَجَعَلْنَاكُمْ شُعُوبًا وَقَبَائِلَ لِتَعَارَفُوا", "en": "And made you peoples and tribesthat you may know one another.", "ref": "49:13b", "surah": 49, "ayah": 13},
        {"ar": "إِنَّ أَكْرَمَكُمْ عِندَ اللّٰهِ أَتْقَاكُمْ", "en": "Indeed, the most noble of youbefore Allah is the most righteous.", "ref": "49:13c", "surah": 49, "ayah": 13},
    ]},

    # 44 ─ Yunus 62-64 — Les alliés d'Allah
    {"title": "The Allies of Allah", "verses": [
        {"ar": "أَلَا إِنَّ أَوْلِيَاءَ اللّٰهِ لَا خَوْفٌ عَلَيْهِمْ وَلَا هُمْ يَحْزَنُونَ", "en": "Unquestionably, the allies of Allah —there will be no fear concerning them,nor will they grieve.", "ref": "10:62", "surah": 10, "ayah": 62},
        {"ar": "الَّذِينَ آمَنُوا وَكَانُوا يَتَّقُونَ", "en": "Those who believedand were fearing Allah.", "ref": "10:63", "surah": 10, "ayah": 63},
        {"ar": "لَهُمُ الْبُشْرَىٰ فِي الْحَيَاةِ الدُّنْيَا وَفِي الْآخِرَةِ", "en": "For them are good tidingsin worldly life and in the Hereafter.", "ref": "10:64a", "surah": 10, "ayah": 64},
        {"ar": "لَا تَبْدِيلَ لِكَلِمَاتِ اللّٰهِ", "en": "There is no change in the wordsof Allah.", "ref": "10:64b", "surah": 10, "ayah": 64},
    ]},

    # 45 ─ Az-Zumar 23 — Le meilleur des discours
    {"title": "The Quran — The Best Speech", "verses": [
        {"ar": "اللّٰهُ نَزَّلَ أَحْسَنَ الْحَدِيثِ كِتَابًا مُّتَشَابِهًا مَّثَانِيَ", "en": "Allah has sent down the best statement:a consistent Book whereinis reiteration.", "ref": "39:23a", "surah": 39, "ayah": 23},
        {"ar": "تَقْشَعِرُّ مِنْهُ جُلُودُ الَّذِينَ يَخْشَوْنَ رَبَّهُمْ", "en": "The skins shudder therefromof those who fear their Lord,", "ref": "39:23b", "surah": 39, "ayah": 23},
        {"ar": "ثُمَّ تَلِينُ جُلُودُهُمْ وَقُلُوبُهُمْ إِلَىٰ ذِكْرِ اللّٰهِ", "en": "Then their skins and hearts softento the remembrance of Allah.", "ref": "39:23c", "surah": 39, "ayah": 23},
        {"ar": "ذَٰلِكَ هُدَى اللّٰهِ يَهْدِي بِهِ مَن يَشَاءُ", "en": "That is the guidance of Allahby which He guides whom He wills.", "ref": "39:23d", "surah": 39, "ayah": 23},
    ]},

    # 46 ─ Al-Isra 23-24 — Les parents
    {"title": "Honoring Parents", "verses": [
        {"ar": "وَقَضَىٰ رَبُّكَ أَلَّا تَعْبُدُوا إِلَّا إِيَّاهُ", "en": "And your Lord has decreed that younot worship except Him,", "ref": "17:23a", "surah": 17, "ayah": 23},
        {"ar": "وَبِالْوَالِدَيْنِ إِحْسَانًا", "en": "And to parents, good treatment.", "ref": "17:23b", "surah": 17, "ayah": 23},
        {"ar": "إِمَّا يَبْلُغَنَّ عِندَكَ الْكِبَرَ أَحَدُهُمَا أَوْ كِلَاهُمَا", "en": "Whether one or both of them reach oldage with you,", "ref": "17:23c", "surah": 17, "ayah": 23},
        {"ar": "فَلَا تَقُل لَّهُمَا أُفٍّ وَلَا تَنْهَرْهُمَا", "en": "Do not say to them a word of disrespectnor repel them,", "ref": "17:23d", "surah": 17, "ayah": 23},
        {"ar": "وَقُل لَّهُمَا قَوْلًا كَرِيمًا", "en": "But say to them words ofnoble kindness.", "ref": "17:23e", "surah": 17, "ayah": 23},
        {"ar": "وَاخْفِضْ لَهُمَا جَنَاحَ الذُّلِّ مِنَ الرَّحْمَةِ", "en": "And lower to them the wingof humility out of mercy,", "ref": "17:24a", "surah": 17, "ayah": 24},
        {"ar": "وَقُل رَّبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا", "en": "And say: My Lord, have mercy upon themas they brought me up when I was small.", "ref": "17:24b", "surah": 17, "ayah": 24},
    ]},

    # 47 ─ Al-Muzzammil 20 — La prière de nuit
    {"title": "The Night Prayer — Tahajjud", "verses": [
        {"ar": "إِنَّ رَبَّكَ يَعْلَمُ أَنَّكَ تَقُومُ أَدْنَىٰ مِن ثُلُثَيِ اللَّيْلِ", "en": "Indeed, your Lord knows that you standpraying almost two thirds of the night,", "ref": "73:20a", "surah": 73, "ayah": 20},
        {"ar": "وَنِصْفَهُ وَثُلُثَهُ وَطَائِفَةٌ مِّنَ الَّذِينَ مَعَكَ", "en": "And half of it and a third of it,and a group of those with you.", "ref": "73:20b", "surah": 73, "ayah": 20},
        {"ar": "وَأَقِيمُوا الصَّلَاةَ وَآتُوا الزَّكَاةَ", "en": "And establish prayerand give Zakah,", "ref": "73:20c", "surah": 73, "ayah": 20},
        {"ar": "وَمَا تُقَدِّمُوا لِأَنفُسِكُم مِّنْ خَيْرٍ تَجِدُوهُ عِندَ اللّٰهِ", "en": "And whatever good you put forwardfor yourselves — you will find itwith Allah.", "ref": "73:20d", "surah": 73, "ayah": 20},
        {"ar": "إِنَّ اللّٰهَ غَفُورٌ رَّحِيمٌ", "en": "Indeed, Allah is Forgivingand Merciful.", "ref": "73:20e", "surah": 73, "ayah": 20},
    ]},

    # 48 ─ Al-Baqarah 2-5 — Le Livre sans doute
    {"title": "The Guide for the Righteous", "verses": [
        {"ar": "ذَٰلِكَ الْكِتَابُ لَا رَيْبَ فِيهِ", "en": "This is the Book about whichthere is no doubt,", "ref": "2:2a", "surah": 2, "ayah": 2},
        {"ar": "هُدًى لِّلْمُتَّقِينَ", "en": "A guidance for thoseconscious of Allah.", "ref": "2:2b", "surah": 2, "ayah": 2},
        {"ar": "الَّذِينَ يُؤْمِنُونَ بِالْغَيْبِ وَيُقِيمُونَ الصَّلَاةَ", "en": "Who believe in the unseen,establish prayer,", "ref": "2:3a", "surah": 2, "ayah": 3},
        {"ar": "وَمِمَّا رَزَقْنَاهُمْ يُنفِقُونَ", "en": "And spend from what Wehave provided them.", "ref": "2:3b", "surah": 2, "ayah": 3},
        {"ar": "أُولَٰئِكَ عَلَىٰ هُدًى مِّن رَّبِّهِمْ", "en": "Those are upon guidancefrom their Lord,", "ref": "2:5a", "surah": 2, "ayah": 5},
        {"ar": "وَأُولَٰئِكَ هُمُ الْمُفْلِحُونَ", "en": "And it is those whoare the successful.", "ref": "2:5b", "surah": 2, "ayah": 5},
    ]},

    # 49 ─ Fussilat 33 — La meilleure parole
    {"title": "Calling to Allah", "verses": [
        {"ar": "وَمَنْ أَحْسَنُ قَوْلًا مِّمَّن دَعَا إِلَى اللّٰهِ", "en": "And who is better in speechthan one who calls to Allah,", "ref": "41:33a", "surah": 41, "ayah": 33},
        {"ar": "وَعَمِلَ صَالِحًا", "en": "And does righteousness,", "ref": "41:33b", "surah": 41, "ayah": 33},
        {"ar": "وَقَالَ إِنَّنِي مِنَ الْمُسْلِمِينَ", "en": "And says: Indeed, I amof the Muslims?", "ref": "41:33c", "surah":41, "ayah": 33},
    ]},

    # 50 ─ Al-Imran 185 — Chaque âme goûtera la mort
    {"title": "The Test of This World", "verses": [
        {"ar": "كُلُّ نَفْسٍ ذَائِقَةُ الْمَوْتِ", "en": "Every soul will taste death.", "ref": "3:185a", "surah": 3, "ayah": 185},
        {"ar": "وَإِنَّمَا تُوَفَّوْنَ أُجُورَكُمْ يَوْمَ الْقِيَامَةِ", "en": "And you will only be givenyour full compensationon the Day of Resurrection.", "ref": "3:185b", "surah": 3, "ayah": 185},
        {"ar": "فَمَن زُحْزِحَ عَنِ النَّارِ وَأُدْخِلَ الْجَنَّةَ فَقَدْ فَازَ", "en": "So whoever is kept away from the Fireand admitted to Paradisehas attained his desire.", "ref": "3:185c", "surah": 3, "ayah": 185},
        {"ar": "وَمَا الْحَيَاةُ الدُّنْيَا إِلَّا مَتَاعُ الْغُرُورِ", "en": "And what is the life of this worldexcept the enjoyment of delusion.", "ref": "3:185d", "surah": 3, "ayah": 185},
    ]},

    # 51 ─ Al-Kahf 46 — Les richesses passagères
    {"title": "True Wealth", "verses": [
        {"ar": "الْمَالُ وَالْبَنُونَ زِينَةُ الْحَيَاةِ الدُّنْيَا", "en": "Wealth and children arethe adornment of worldly life.", "ref": "18:46a", "surah": 18, "ayah": 46},
        {"ar": "وَالْبَاقِيَاتُ الصَّالِحَاتُ خَيْرٌ عِندَ رَبِّكَ ثَوَابًا", "en": "But the enduring good deeds are betterto your Lord for reward,", "ref": "18:46b", "surah": 18, "ayah": 46},
        {"ar": "وَخَيْرٌ أَمَلًا", "en": "And better for one's hope.", "ref": "18:46c", "surah": 18, "ayah": 46},
    ]},

    # 52 ─ Al-Imran 26-27 — La souveraineté d'Allah
    {"title": "Allah Gives and Takes", "verses": [
        {"ar": "قُلِ اللّٰهُمَّ مَالِكَ الْمُلْكِ", "en": "Say: O Allah, Owner of Sovereignty,", "ref": "3:26a", "surah": 3, "ayah": 26},
        {"ar": "تُؤْتِي الْمُلْكَ مَن تَشَاءُ وَتَنزِعُ الْمُلْكَ مِمَّن تَشَاءُ", "en": "You give sovereignty to whom You willand You take sovereignty from whom You will.", "ref": "3:26b", "surah": 3, "ayah": 26},
        {"ar": "وَتُعِزُّ مَن تَشَاءُ وَتُذِلُّ مَن تَشَاءُ", "en": "You honor whom You willand You humble whom You will.", "ref": "3:26c", "surah": 3, "ayah": 26},
        {"ar": "بِيَدِكَ الْخَيْرُ إِنَّكَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "en": "In Your hand is all good.Indeed, You are over all things competent.", "ref": "3:26d", "surah": 3, "ayah": 26},
    ]},

    # 53 ─ Al-Mu'minun 1-11 — Les croyants qui réussissent
    {"title": "The Successful Believers", "verses": [
        {"ar": "قَدْ أَفْلَحَ الْمُؤْمِنُونَ", "en": "Certainly will the believershave succeeded:", "ref": "23:1", "surah": 23, "ayah": 1},
        {"ar": "الَّذِينَ هُمْ فِي صَلَاتِهِمْ خَاشِعُونَ", "en": "They who are during their prayerhumbly submissive,", "ref": "23:2", "surah": 23, "ayah": 2},
        {"ar": "وَالَّذِينَ هُمْ عَنِ اللَّغْوِ مُعْرِضُونَ", "en": "And they who turn awayfrom ill speech,", "ref": "23:3", "surah": 23, "ayah": 3},
        {"ar": "وَالَّذِينَ هُمْ لِلزَّكَاةِ فَاعِلُونَ", "en": "And they who are observantof Zakah,", "ref": "23:4", "surah": 23, "ayah": 4},
        {"ar": "أُولَٰئِكَ هُمُ الْوَارِثُونَ", "en": "Those are the inheritors,", "ref": "23:10", "surah": 23, "ayah": 10},
        {"ar": "الَّذِينَ يَرِثُونَ الْفِرْدَوْسَ هُمْ فِيهَا خَالِدُونَ", "en": "Who will inherit al-Firdaus.They will abide therein eternally.", "ref": "23:11", "surah": 23, "ayah": 11},
    ]},

    # 54 ─ Al-Baqarah 163 — L'Unique
    {"title": "Allah — The One", "verses": [
        {"ar": "وَإِلَٰهُكُمْ إِلَٰهٌ وَاحِدٌ", "en": "And your God is one God.", "ref": "2:163a", "surah": 2, "ayah": 163},
        {"ar": "لَّا إِلَٰهَ إِلَّا هُوَ الرَّحْمَٰنُ الرَّحِيمُ", "en": "There is no deity worthy of worshipexcept Him, the Most Gracious,the Most Merciful.", "ref": "2:163b", "surah": 2, "ayah": 163},
    ]},

    # 55 ─ An-Nahl 97 — La bonne vie
    {"title": "The Good Life", "verses": [
        {"ar": "مَنْ عَمِلَ صَالِحًا مِّن ذَكَرٍ أَوْ أُنثَىٰ وَهُوَ مُؤْمِنٌ", "en": "Whoever does righteousness,whether male or female,while being a believer —", "ref": "16:97a", "surah": 16, "ayah": 97},
        {"ar": "فَلَنُحْيِيَنَّهُ حَيَاةً طَيِّبَةً", "en": "We will surely cause himto live a good life.", "ref": "16:97b", "surah": 16, "ayah": 97},
        {"ar": "وَلَنَجْزِيَنَّهُمْ أَجْرَهُم بِأَحْسَنِ مَا كَانُوا يَعْمَلُونَ", "en": "And We will surely give themtheir reward according to the bestof what they used to do.", "ref": "16:97c", "surah": 16, "ayah": 97},
    ]},

    # 56 ─ Al-Ahzab 41-43 — Abondance de dhikr
    {"title": "Abundance of Remembrance", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا اذْكُرُوا اللّٰهَ ذِكْرًا كَثِيرًا", "en": "O you who have believed,remember Allah with much remembrance,", "ref": "33:41", "surah": 33, "ayah": 41},
        {"ar": "وَسَبِّحُوهُ بُكْرَةً وَأَصِيلًا", "en": "And exalt Him morningand afternoon.", "ref": "33:42", "surah": 33, "ayah": 42},
        {"ar": "هُوَ الَّذِي يُصَلِّي عَلَيْكُمْ وَمَلَائِكَتُهُ", "en": "It is He who confers blessing upon you,and His angels,", "ref": "33:43a", "surah": 33, "ayah": 43},
        {"ar": "لِيُخْرِجَكُم مِّنَ الظُّلُمَاتِ إِلَى النُّورِ", "en": "That He may bring you outfrom darkness into the light.", "ref": "33:43b", "surah": 33, "ayah": 43},
        {"ar": "وَكَانَ بِالْمُؤْمِنِينَ رَحِيمًا", "en": "And ever is He, to the believers,Merciful.", "ref": "33:43c", "surah": 33, "ayah": 43},
    ]},

    # 57 ─ Ibrahim 40-41 — Dua d'Ibrahim
    {"title": "The Prayer of Ibrahim", "verses": [
        {"ar": "رَبِّ اجْعَلْنِي مُقِيمَ الصَّلَاةِ وَمِن ذُرِّيَّتِي", "en": "My Lord, make me an establisher of prayer,and my descendants.", "ref": "14:40a", "surah": 14, "ayah": 40},
        {"ar": "رَبَّنَا وَتَقَبَّلْ دُعَاءِ", "en": "Our Lord, and accept my supplication.", "ref": "14:40b", "surah": 14, "ayah": 40},
        {"ar": "رَبَّنَا اغْفِرْ لِي وَلِوَالِدَيَّ وَلِلْمُؤْمِنِينَ", "en": "Our Lord, forgive meand my parents and the believers.", "ref": "14:41a", "surah": 14, "ayah": 41},
        {"ar": "يَوْمَ يَقُومُ الْحِسَابُ", "en": "On the Day when the accountis established.", "ref": "14:41b", "surah": 14, "ayah": 41},
    ]},

    # 58 ─ Al-Ghashiyah — La Déferlante
    {"title": "Al-Ghashiyah — The Overwhelming", "verses": [
        {"ar": "وُجُوهٌ يَوْمَئِذٍ خَاشِعَةٌ", "en": "Faces, that Day, will be humbled,", "ref": "88:2", "surah": 88, "ayah": 2},
        {"ar": "وُجُوهٌ يَوْمَئِذٍ نَّاعِمَةٌ", "en": "And faces, that Day, will be in delight,", "ref": "88:8", "surah": 88, "ayah": 8},
        {"ar": "لِّسَعْيِهَا رَاضِيَةٌ", "en": "Satisfied with their effort,", "ref": "88:9", "surah": 88, "ayah": 9},
        {"ar": "فِي جَنَّةٍ عَالِيَةٍ", "en": "In an elevated garden,", "ref": "88:10", "surah": 88, "ayah": 10},
        {"ar": "أَفَلَا يَنظُرُونَ إِلَى الْإِبِلِ كَيْفَ خُلِقَتْ", "en": "Then do they not look at the camels —how they are created?", "ref": "88:17", "surah": 88, "ayah": 17},
        {"ar": "وَإِلَى السَّمَاءِ كَيْفَ رُفِعَتْ", "en": "And at the sky —how it is raised?", "ref": "88:18", "surah": 88, "ayah": 18},
        {"ar": "وَإِلَى الْجِبَالِ كَيْفَ نُصِبَتْ", "en": "And at the mountains —how they are erected?", "ref": "88:19", "surah": 88, "ayah": 19},
        {"ar": "وَإِلَى الْأَرْضِ كَيْفَ سُطِحَتْ", "en": "And at the earth —how it is spread out?", "ref": "88:20", "surah": 88, "ayah": 20},
    ]},

    # 59 ─ Al-Qasas 24 — Dua de Musa
    {"title": "The Dua of Musa", "verses": [
        {"ar": "رَبِّ إِنِّي لِمَا أَنزَلْتَ إِلَيَّ مِنْ خَيْرٍ فَقِيرٌ", "en": "My Lord, indeed I amfor whatever good You would send downto me, in need.", "ref": "28:24", "surah": 28, "ayah": 24},
    ]},

    # 60 ─ Sad 35 — Dua de Sulayman
    {"title": "The Dua of Sulayman", "verses": [
        {"ar": "رَبِّ اغْفِرْ لِي وَهَبْ لِي مُلْكًا لَّا يَنبَغِي لِأَحَدٍ مِّن بَعْدِي", "en": "My Lord, forgive me and grant mea kingdom such as will not belongto anyone after me.", "ref": "38:35a", "surah": 38, "ayah": 35},
        {"ar": "إِنَّكَ أَنتَ الْوَهَّابُ", "en": "Indeed, You are the Bestower.", "ref": "38:35b", "surah": 38, "ayah": 35},
    ]},

    # 61 ─ Al-Anbiya 83-84 — Dua d'Ayyoub
    {"title": "The Dua of Ayyoub — Patience in Trial", "verses": [
        {"ar": "وَأَيُّوبَ إِذْ نَادَىٰ رَبَّهُ أَنِّي مَسَّنِيَ الضُّرُّ", "en": "And remember Job, when he calledto his Lord: Indeed, adversity has touched me,", "ref": "21:83a", "surah": 21, "ayah": 83},
        {"ar": "وَأَنتَ أَرْحَمُ الرَّاحِمِينَ", "en": "And you are the most Mercifulof the merciful.", "ref": "21:83b", "surah": 21, "ayah": 83},
        {"ar": "فَاسْتَجَبْنَا لَهُ فَكَشَفْنَا مَا بِهِ مِن ضُرٍّ", "en": "So We responded to himand removed what afflicted him of adversity.", "ref": "21:84a", "surah": 21, "ayah": 84},
        {"ar": "وَآتَيْنَاهُ أَهْلَهُ وَمِثْلَهُم مَّعَهُمْ رَحْمَةً مِّنْ عِندِنَا", "en": "And We gave back his familyand the like thereof with themas mercy from Us.", "ref": "21:84b", "surah": 21, "ayah": 84},
    ]},

    # 62 ─ Al-Anbiya 87 — Dua de Yunus (Dhul-Nun)
    {"title": "The Dua of Yunus — From the Darkness", "verses": [
        {"ar": "وَذَا النُّونِ إِذ ذَّهَبَ مُغَاضِبًا", "en": "And remember the man of the fish,when he went away in anger,", "ref": "21:87a", "surah": 21, "ayah": 87},
        {"ar": "فَنَادَىٰ فِي الظُّلُمَاتِ أَن لَّا إِلَٰهَ إِلَّا أَنتَ سُبْحَانَكَ", "en": "And called out in the darkness:There is no deity except You;exalted are You.", "ref": "21:87b", "surah": 21, "ayah": 87},
        {"ar": "إِنِّي كُنتُ مِنَ الظَّالِمِينَ", "en": "Indeed, I have beenof the wrongdoers.", "ref": "21:87c", "surah": 21, "ayah": 87},
        {"ar": "فَاسْتَجَبْنَا لَهُ وَنَجَّيْنَاهُ مِنَ الْغَمِّ", "en": "So We responded to himand saved him from the distress.", "ref": "21:88a", "surah": 21, "ayah": 88},
        {"ar": "وَكَذَٰلِكَ نُنجِي الْمُؤْمِنِينَ", "en": "And thus do We savethe believers.", "ref": "21:88b", "surah": 21, "ayah": 88},
    ]},

    # 63 ─ Al-Baqarah 201 — La meilleure dua
    {"title": "The Best Supplication", "verses": [
        {"ar": "رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً", "en": "Our Lord, give us in this worldthat which is good,", "ref": "2:201a", "surah": 2, "ayah": 201},
        {"ar": "وَفِي الْآخِرَةِ حَسَنَةً", "en": "And in the Hereafterthat which is good,", "ref": "2:201b", "surah": 2, "ayah": 201},
        {"ar": "وَقِنَا عَذَابَ النَّارِ", "en": "And protect us fromthe punishment of the Fire.", "ref": "2:201c", "surah": 2, "ayah": 201},
    ]},

    # 64 ─ Al-Furqan 63-76 — Les serviteurs du Tout-Miséricordieux
    {"title": "The Servants of the Most Merciful", "verses": [
        {"ar": "وَعِبَادُ الرَّحْمَٰنِ الَّذِينَ يَمْشُونَ عَلَى الْأَرْضِ هَوْنًا", "en": "And the servants of the Most Mercifulare those who walk upon the earth easily,", "ref": "25:63a", "surah": 25, "ayah": 63},
        {"ar": "وَإِذَا خَاطَبَهُمُ الْجَاهِلُونَ قَالُوا سَلَامًا", "en": "And when the ignorant address themharshly, they say words of peace.", "ref": "25:63b", "surah": 25, "ayah": 63},
        {"ar": "وَالَّذِينَ يَبِيتُونَ لِرَبِّهِمْ سُجَّدًا وَقِيَامًا", "en": "And those who spend the nightfor their Lord prostratingand standing in prayer.", "ref": "25:64", "surah": 25, "ayah": 64},
        {"ar": "وَالَّذِينَ يَقُولُونَ رَبَّنَا اصْرِفْ عَنَّا عَذَابَ جَهَنَّمَ", "en": "And those who say:Our Lord, avert from usthe punishment of Hell.", "ref": "25:65a", "surah": 25, "ayah": 65},
        {"ar": "إِنَّ عَذَابَهَا كَانَ غَرَامًا", "en": "Indeed, its punishment isa calamity.", "ref": "25:65b", "surah": 25, "ayah": 65},
    ]},

    # 65 ─ Al-Anfal 45-46 — Steadfastness
    {"title": "Steadfastness in Struggle", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا إِذَا لَقِيتُمْ فِئَةً فَاثْبُتُوا", "en": "O you who have believed,when you encounter a company,stand firm.", "ref": "8:45a", "surah": 8, "ayah": 45},
        {"ar": "وَاذْكُرُوا اللّٰهَ كَثِيرًا لَّعَلَّكُمْ تُفْلِحُونَ", "en": "And remember Allah muchthat you may be successful.", "ref": "8:45b", "surah": 8, "ayah": 45},
        {"ar": "وَأَطِيعُوا اللّٰهَ وَرَسُولَهُ وَلَا تَنَازَعُوا فَتَفْشَلُوا", "en": "And obey Allah and His messengerand do not dispute,lest you fail.", "ref": "8:46a", "surah": 8, "ayah": 46},
        {"ar": "وَاصْبِرُوا إِنَّ اللّٰهَ مَعَ الصَّابِرِينَ", "en": "And be patient. Indeed,Allah is with the patient.", "ref": "8:46b", "surah": 8, "ayah": 46},
    ]},

    # 66 ─ Al-Maidah 35 — Se rapprocher d'Allah
    {"title": "Drawing Closer to Allah", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا اتَّقُوا اللّٰهَ", "en": "O you who have believed,fear Allah,", "ref": "5:35a", "surah": 5, "ayah": 35},
        {"ar": "وَابْتَغُوا إِلَيْهِ الْوَسِيلَةَ", "en": "And seek the meansof nearness to Him,", "ref": "5:35b", "surah": 5, "ayah": 35},
        {"ar": "وَجَاهِدُوا فِي سَبِيلِهِ لَعَلَّكُمْ تُفْلِحُونَ", "en": "And strive in His causethat you may succeed.", "ref": "5:35c", "surah": 5, "ayah": 35},
    ]},

    # 67 ─ Al-Jumu'ah 9-10 — La prière du vendredi
    {"title": "The Friday Prayer", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا إِذَا نُودِيَ لِلصَّلَاةِ مِن يَوْمِ الْجُمُعَةِ", "en": "O you who have believed,when the call to prayer is madeon Friday,", "ref": "62:9a", "surah": 62, "ayah": 9},
        {"ar": "فَاسْعَوْا إِلَىٰ ذِكْرِ اللّٰهِ وَذَرُوا الْبَيْعَ", "en": "Then proceed to the remembrance of Allahand leave trade.", "ref": "62:9b", "surah": 62, "ayah": 9},
        {"ar": "ذَٰلِكُمْ خَيْرٌ لَّكُمْ إِن كُنتُمْ تَعْلَمُونَ", "en": "That is better for you,if you only knew.", "ref": "62:9c", "surah": 62, "ayah": 9},
        {"ar": "فَإِذَا قُضِيَتِ الصَّلَاةُ فَانتَشِرُوا فِي الْأَرْضِ", "en": "And when the prayer has been concluded,disperse through the land,", "ref": "62:10a", "surah": 62, "ayah": 10},
        {"ar": "وَابْتَغُوا مِن فَضْلِ اللّٰهِ وَاذْكُرُوا اللّٰهَ كَثِيرًا", "en": "And seek from the bounty of Allah,and remember Allah often,", "ref": "62:10b", "surah": 62, "ayah": 10},
        {"ar": "لَّعَلَّكُمْ تُفْلِحُونَ", "en": "That you may succeed.", "ref": "62:10c", "surah": 62, "ayah": 10},
    ]},

    # 68 ─ An-Nisa 36 — Bienfaisance envers tous
    {"title": "Total Goodness", "verses": [
        {"ar": "وَاعْبُدُوا اللّٰهَ وَلَا تُشْرِكُوا بِهِ شَيْئًا", "en": "Worship Allah and associate nothingwith Him,", "ref": "4:36a", "surah": 4, "ayah": 36},
        {"ar": "وَبِالْوَالِدَيْنِ إِحْسَانًا", "en": "And to parents do good,", "ref": "4:36b", "surah": 4, "ayah": 36},
        {"ar": "وَبِذِي الْقُرْبَىٰ وَالْيَتَامَىٰ وَالْمَسَاكِينِ", "en": "And to relatives, orphans,the needy,", "ref": "4:36c", "surah": 4, "ayah": 36},
        {"ar": "إِنَّ اللّٰهَ لَا يُحِبُّ مَن كَانَ مُخْتَالًا فَخُورًا", "en": "Indeed, Allah does not like thosewho are self-deluding and boastful.", "ref": "4:36d", "surah": 4, "ayah": 36},
    ]},

    # 69 ─ Al-Imran 133-136 — Se hâter vers le pardon
    {"title": "Hastening to Allah's Forgiveness", "verses": [
        {"ar": "وَسَارِعُوا إِلَىٰ مَغْفِرَةٍ مِّن رَّبِّكُمْ", "en": "And hasten to forgivenessfrom your Lord,", "ref": "3:133a", "surah": 3, "ayah": 133},
        {"ar": "وَجَنَّةٍ عَرْضُهَا السَّمَاوَاتُ وَالْأَرْضُ", "en": "And a garden whose width spansthe heavens and earth,", "ref": "3:133b", "surah": 3, "ayah": 133},
        {"ar": "أُعِدَّتْ لِلْمُتَّقِينَ", "en": "Prepared for the righteous.", "ref": "3:133c", "surah": 3, "ayah": 133},
        {"ar": "الَّذِينَ يُنفِقُونَ فِي السَّرَّاءِ وَالضَّرَّاءِ", "en": "Who spend in easeand in adversity,", "ref": "3:134a", "surah": 3, "ayah": 134},
        {"ar": "وَالْكَاظِمِينَ الْغَيْظَ وَالْعَافِينَ عَنِ النَّاسِ", "en": "And who restrain angerand who pardon people,", "ref": "3:134b", "surah": 3, "ayah": 134},
        {"ar": "وَاللّٰهُ يُحِبُّ الْمُحْسِنِينَ", "en": "And Allah lovesthe doers of good.", "ref": "3:134c", "surah": 3, "ayah": 134},
    ]},

    # 70 ─ Al-Baqarah 177 — La vraie piété (Al-Birr)
    {"title": "True Righteousness — Al-Birr", "verses": [
        {"ar": "لَّيْسَ الْبِرَّ أَن تُوَلُّوا وُجُوهَكُمْ قِبَلَ الْمَشْرِقِ وَالْمَغْرِبِ", "en": "Righteousness is not turningyour faces toward the east or west.", "ref": "2:177a", "surah": 2, "ayah": 177},
        {"ar": "وَلَٰكِنَّ الْبِرَّ مَنْ آمَنَ بِاللّٰهِ وَالْيَوْمِ الْآخِرِ", "en": "But righteousness is one who believes in Allah,the Last Day,", "ref": "2:177b", "surah": 2, "ayah": 177},
        {"ar": "وَآتَى الْمَالَ عَلَىٰ حُبِّهِ ذَوِي الْقُرْبَىٰ وَالْيَتَامَىٰ وَالْمَسَاكِينَ", "en": "And gives wealth, in spite of love for it,to relatives, orphans, the needy,", "ref": "2:177c", "surah": 2, "ayah": 177},
        {"ar": "وَأَقَامَ الصَّلَاةَ وَآتَى الزَّكَاةَ", "en": "And establishes prayerand gives Zakah.", "ref": "2:177d", "surah": 2, "ayah": 177},
        {"ar": "أُولَٰئِكَ الَّذِينَ صَدَقُوا وَأُولَٰئِكَ هُمُ الْمُتَّقُونَ", "en": "Those are the ones who have been true,and it is those who arethe righteous.", "ref": "2:177e", "surah": 2, "ayah": 177},
    ]},

    # 71 — Paradise
    {"title": "Paradise — Jannah", "verses": [
        {"ar": "وَبَشِّرِ الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ أَنَّ لَهُمْ جَنَّاتٍ تَجْرِي مِن تَحْتِهَا الْأَنْهَارُ", "en": "Give good tidings to those who believe\nand do righteous deeds that they will have\ngardens beneath which rivers flow.", "ref": "2:25a", "surah": 2, "ayah": 25},
        {"ar": "كُلَّمَا رُزِقُوا مِنْهَا مِن ثَمَرَةٍ رِّزْقًا قَالُوا هَٰذَا الَّذِي رُزِقْنَا مِن قَبْلُ", "en": "Whenever they are provided with fruit\ntherefrom as provision, they will say:\nthis is what we were provided before.", "ref": "2:25b", "surah": 2, "ayah": 25},
        {"ar": "وَلَهُمْ فِيهَا أَزْوَاجٌ مُّطَهَّرَةٌ وَهُمْ فِيهَا خَالِدُونَ", "en": "And they will have therein\npurified spouses,\nand they will abide therein eternally.", "ref": "2:25c", "surah": 2, "ayah": 25},
    ]},

    # 72 — The Day of Judgment
    {"title": "The Day of Judgment", "verses": [
        {"ar": "يَوْمَ تَجِدُ كُلُّ نَفْسٍ مَّا عَمِلَتْ مِنْ خَيْرٍ مُّحْضَرًا", "en": "The Day every soul will find\nwhat it has done of good\npresented before it,", "ref": "3:30a", "surah": 3, "ayah": 30},
        {"ar": "وَمَا عَمِلَتْ مِن سُوءٍ تَوَدُّ لَوْ أَنَّ بَيْنَهَا وَبَيْنَهُ أَمَدًا بَعِيدًا", "en": "And what it has done of evil,\nit will wish that between itself and that\nwere a great distance.", "ref": "3:30b", "surah": 3, "ayah": 30},
        {"ar": "وَيُحَذِّرُكُمُ اللّٰهُ نَفْسَهُ", "en": "And Allah warns you\nof Himself.", "ref": "3:30c", "surah": 3, "ayah": 30},
    ]},

    # 73 — The Signs of Allah
    {"title": "The Signs of Allah", "verses": [
        {"ar": "إِنَّ فِي خَلْقِ السَّمَاوَاتِ وَالْأَرْضِ وَاخْتِلَافِ اللَّيْلِ وَالنَّهَارِ لَآيَاتٍ لِّأُولِي الْأَلْبَابِ", "en": "Indeed, in the creation of the heavens\nand the earth and the alternation\nof night and day are signs for people of understanding.", "ref": "3:190", "surah": 3, "ayah": 190},
        {"ar": "الَّذِينَ يَذْكُرُونَ اللّٰهَ قِيَامًا وَقُعُودًا وَعَلَىٰ جُنُوبِهِمْ", "en": "Those who remember Allah\nwhile standing, sitting,\nand lying on their sides,", "ref": "3:191a", "surah": 3, "ayah": 191},
        {"ar": "وَيَتَفَكَّرُونَ فِي خَلْقِ السَّمَاوَاتِ وَالْأَرْضِ", "en": "And who reflect upon\nthe creation of the heavens\nand the earth,", "ref": "3:191b", "surah": 3, "ayah": 191},
        {"ar": "رَبَّنَا مَا خَلَقْتَ هَٰذَا بَاطِلًا سُبْحَانَكَ", "en": "Our Lord, You did not create this\nin vain; exalted are You.", "ref": "3:191c", "surah": 3, "ayah": 191},
    ]},

    # 74 — Repentance
    {"title": "Repentance — Tawbah", "verses": [
        {"ar": "وَتُوبُوا إِلَى اللّٰهِ جَمِيعًا أَيُّهَ الْمُؤْمِنُونَ لَعَلَّكُمْ تُفْلِحُونَ", "en": "And turn to Allah in repentance,\nall of you, O believers,\nthat you might succeed.", "ref": "24:31b", "surah": 24, "ayah": 31},
    ]},

    # 75 — The Quran as Healing
    {"title": "The Quran as Healing", "verses": [
        {"ar": "وَنُنَزِّلُ مِنَ الْقُرْآنِ مَا هُوَ شِفَاءٌ وَرَحْمَةٌ لِّلْمُؤْمِنِينَ", "en": "And We send down of the Quran\nthat which is healing and mercy\nfor the believers.", "ref": "17:82a", "surah": 17, "ayah": 82},
        {"ar": "وَلَا يَزِيدُ الظَّالِمِينَ إِلَّا خَسَارًا", "en": "And it does not increase the wrongdoers\nexcept in loss.", "ref": "17:82b", "surah": 17, "ayah": 82},
    ]},

    # 76 — Allah's Knowledge
    {"title": "Allah's All-Encompassing Knowledge", "verses": [
        {"ar": "وَعِندَهُ مَفَاتِحُ الْغَيْبِ لَا يَعْلَمُهَا إِلَّا هُوَ", "en": "And with Him are the keys\nof the unseen; none knows them\nexcept Him.", "ref": "6:59a", "surah": 6, "ayah": 59},
        {"ar": "وَيَعْلَمُ مَا فِي الْبَرِّ وَالْبَحْرِ", "en": "And He knows what is\non the land and in the sea.", "ref": "6:59b", "surah": 6, "ayah": 59},
        {"ar": "وَمَا تَسْقُطُ مِن وَرَقَةٍ إِلَّا يَعْلَمُهَا", "en": "Not a leaf falls\nbut that He knows it.", "ref": "6:59c", "surah": 6, "ayah": 59},
    ]},

    # 77 — Seeking Refuge in Allah
    {"title": "Seeking Refuge in Allah", "verses": [
        {"ar": "وَإِمَّا يَنزَغَنَّكَ مِنَ الشَّيْطَانِ نَزْغٌ فَاسْتَعِذْ بِاللّٰهِ", "en": "And if an evil suggestion\ncomes to you from Satan,\nthen seek refuge in Allah.", "ref": "7:200a", "surah": 7, "ayah": 200},
        {"ar": "إِنَّهُ سَمِيعٌ عَلِيمٌ", "en": "Indeed, He is\nHearing and Knowing.", "ref": "7:200b", "surah": 7, "ayah": 200},
    ]},

    # 78 — Dhikr Morning and Evening
    {"title": "Morning and Evening Remembrance", "verses": [
        {"ar": "وَاذْكُر رَّبَّكَ فِي نَفْسِكَ تَضَرُّعًا وَخِيفَةً", "en": "And remember your Lord within yourself\nin humility and in fear,", "ref": "7:205a", "surah": 7, "ayah": 205},
        {"ar": "وَدُونَ الْجَهْرِ مِنَ الْقَوْلِ بِالْغُدُوِّ وَالْآصَالِ", "en": "Without loudness in words,\nin the mornings and evenings.", "ref": "7:205b", "surah": 7, "ayah": 205},
        {"ar": "وَلَا تَكُن مِّنَ الْغَافِلِينَ", "en": "And do not be\namong the heedless.", "ref": "7:205c", "surah": 7, "ayah": 205},
    ]},

    # 79 — The Best of Deeds
    {"title": "The Best of Deeds", "verses": [
        {"ar": "قُلْ إِن كُنتُمْ تُحِبُّونَ اللّٰهَ فَاتَّبِعُونِي يُحْبِبْكُمُ اللّٰهُ", "en": "Say: If you love Allah,\nthen follow me — Allah will love you.", "ref": "3:31a", "surah": 3, "ayah": 31},
        {"ar": "وَيَغْفِرْ لَكُمْ ذُنُوبَكُمْ وَاللّٰهُ غَفُورٌ رَّحِيمٌ", "en": "And He will forgive your sins.\nAnd Allah is Forgiving\nand Merciful.", "ref": "3:31b", "surah": 3, "ayah": 31},
    ]},

    # 80 — The Hellfire Warning
    {"title": "Warning Against the Hellfire", "verses": [
        {"ar": "وَاتَّقُوا النَّارَ الَّتِي أُعِدَّتْ لِلْكَافِرِينَ", "en": "And fear the Fire\nprepared for the disbelievers.", "ref": "3:131", "surah": 3, "ayah": 131},
        {"ar": "وَأَطِيعُوا اللّٰهَ وَالرَّسُولَ لَعَلَّكُمْ تُرْحَمُونَ", "en": "And obey Allah and the Messenger\nthat you may obtain mercy.", "ref": "3:132", "surah": 3, "ayah": 132},
    ]},

    # 81 — Sincerity in Worship
    {"title": "Sincerity in Worship", "verses": [
        {"ar": "وَمَا أُمِرُوا إِلَّا لِيَعْبُدُوا اللّٰهَ مُخْلِصِينَ لَهُ الدِّينَ", "en": "And they were not commanded\nexcept to worship Allah,\nbeing sincere to Him in religion,", "ref": "98:5a", "surah": 98, "ayah": 5},
        {"ar": "حُنَفَاءَ وَيُقِيمُوا الصَّلَاةَ وَيُؤْتُوا الزَّكَاةَ", "en": "Inclining to truth,\nand to establish prayer\nand to give Zakah.", "ref": "98:5b", "surah": 98, "ayah": 5},
        {"ar": "وَذَٰلِكَ دِينُ الْقَيِّمَةِ", "en": "And that is\nthe correct religion.", "ref": "98:5c", "surah": 98, "ayah": 5},
    ]},

    # 82 — Al-Baqarah: Fasting
    {"title": "Fasting — Ramadan", "verses": [
        {"ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا كُتِبَ عَلَيْكُمُ الصِّيَامُ", "en": "O you who have believed,\ndecreed upon you is fasting,", "ref": "2:183a", "surah": 2, "ayah": 183},
        {"ar": "كَمَا كُتِبَ عَلَى الَّذِينَ مِن قَبْلِكُمْ لَعَلَّكُمْ تَتَّقُونَ", "en": "As it was decreed upon\nthose before you,\nthat you may become righteous.", "ref": "2:183b", "surah": 2, "ayah": 183},
        {"ar": "شَهْرُ رَمَضَانَ الَّذِي أُنزِلَ فِيهِ الْقُرْآنُ", "en": "The month of Ramadan\nin which was revealed the Quran,", "ref": "2:185a", "surah": 2, "ayah": 185},
        {"ar": "هُدًى لِّلنَّاسِ وَبَيِّنَاتٍ مِّنَ الْهُدَىٰ وَالْفُرْقَانِ", "en": "A guidance for the people\nand clear proofs of guidance\nand criterion.", "ref": "2:185b", "surah": 2, "ayah": 185},
    ]},

    # 83 — Charity
    {"title": "Charity and Giving", "verses": [
        {"ar": "مَّثَلُ الَّذِينَ يُنفِقُونَ أَمْوَالَهُمْ فِي سَبِيلِ اللّٰهِ كَمَثَلِ حَبَّةٍ أَنبَتَتْ سَبْعَ سَنَابِلَ", "en": "The example of those who spend\ntheir wealth in the way of Allah\nis like a grain that sprouts seven ears,", "ref": "2:261a", "surah": 2, "ayah": 261},
        {"ar": "فِي كُلِّ سُنبُلَةٍ مِّائَةُ حَبَّةٍ", "en": "In each ear\none hundred grains.", "ref": "2:261b", "surah": 2, "ayah": 261},
        {"ar": "وَاللّٰهُ يُضَاعِفُ لِمَن يَشَاءُ وَاللّٰهُ وَاسِعٌ عَلِيمٌ", "en": "And Allah multiplies\nfor whom He wills.\nAllah is All-Encompassing and Knowing.", "ref": "2:261c", "surah": 2, "ayah": 261},
    ]},

    # 84 — The Hereafter
    {"title": "The Hereafter — Al-Akhirah", "verses": [
        {"ar": "وَمَا الْحَيَاةُ الدُّنْيَا إِلَّا لَعِبٌ وَلَهْوٌ", "en": "And the worldly life\nis not but amusement and diversion.", "ref": "47:36a", "surah": 47, "ayah": 36},
        {"ar": "وَإِن تُؤْمِنُوا وَتَتَّقُوا يُؤْتِكُمْ أُجُورَكُمْ", "en": "But if you believe and fear Allah,\nHe will give you your rewards.", "ref": "47:36b", "surah": 47, "ayah": 36},
    ]},

    # 85 — Surah Yasin opening
    {"title": "Ya-Sin — Heart of the Quran", "verses": [
        {"ar": "يس", "en": "Ya-Sin.", "ref": "36:1", "surah": 36, "ayah": 1},
        {"ar": "وَالْقُرْآنِ الْحَكِيمِ", "en": "By the wise Quran.", "ref": "36:2", "surah": 36, "ayah": 2},
        {"ar": "إِنَّكَ لَمِنَ الْمُرْسَلِينَ", "en": "Indeed you are\nof the messengers,", "ref": "36:3", "surah": 36, "ayah": 3},
        {"ar": "عَلَىٰ صِرَاطٍ مُّسْتَقِيمٍ", "en": "On a straight path.", "ref": "36:4", "surah": 36, "ayah": 4},
    ]},

    # 86 — The Believers' Supplication
    {"title": "The Believers' Supplication", "verses": [
        {"ar": "رَبَّنَا إِنَّنَا سَمِعْنَا مُنَادِيًا يُنَادِي لِلْإِيمَانِ", "en": "Our Lord, indeed we have heard\na caller calling to faith:", "ref": "3:193a", "surah": 3, "ayah": 193},
        {"ar": "أَنْ آمِنُوا بِرَبِّكُمْ فَآمَنَّا", "en": "Believe in your Lord,\nand we have believed.", "ref": "3:193b", "surah": 3, "ayah": 193},
        {"ar": "رَبَّنَا فَاغْفِرْ لَنَا ذُنُوبَنَا وَكَفِّرْ عَنَّا سَيِّئَاتِنَا", "en": "Our Lord, forgive us our sins\nand remove from us\nour misdeeds.", "ref": "3:193c", "surah": 3, "ayah": 193},
        {"ar": "وَتَوَفَّنَا مَعَ الْأَبْرَارِ", "en": "And cause us to die\nwith the righteous.", "ref": "3:193d", "surah": 3, "ayah": 193},
    ]},

    # 87 — The Throne of Allah
    {"title": "The Throne of Allah", "verses": [
        {"ar": "إِنَّ رَبَّكُمُ اللّٰهُ الَّذِي خَلَقَ السَّمَاوَاتِ وَالْأَرْضَ فِي سِتَّةِ أَيَّامٍ", "en": "Indeed, your Lord is Allah\nwho created the heavens\nand earth in six days,", "ref": "7:54a", "surah": 7, "ayah": 54},
        {"ar": "ثُمَّ اسْتَوَىٰ عَلَى الْعَرْشِ", "en": "Then He established Himself\nabove the Throne.", "ref": "7:54b", "surah": 7, "ayah": 54},
        {"ar": "يُغْشِي اللَّيْلَ النَّهَارَ يَطْلُبُهُ حَثِيثًا", "en": "He covers the night\nwith the day pursuing it rapidly.", "ref": "7:54c", "surah": 7, "ayah": 54},
        {"ar": "أَلَا لَهُ الْخَلْقُ وَالْأَمْرُ تَبَارَكَ اللّٰهُ رَبُّ الْعَالَمِينَ", "en": "Unquestionably, His is the creation\nand the command.\nBlessed is Allah, Lord of the worlds.", "ref": "7:54d", "surah": 7, "ayah": 54},
    ]},

    # 88 — Dua for Guidance
    {"title": "Dua for Guidance", "verses": [
        {"ar": "رَبَّنَا لَا تُزِغْ قُلُوبَنَا بَعْدَ إِذْ هَدَيْتَنَا", "en": "Our Lord, do not let\nour hearts deviate after\nYou have guided us,", "ref": "3:8a", "surah": 3, "ayah": 8},
        {"ar": "وَهَبْ لَنَا مِن لَّدُنكَ رَحْمَةً", "en": "And grant us from Yourself\nmercy.", "ref": "3:8b", "surah": 3, "ayah": 8},
        {"ar": "إِنَّكَ أَنتَ الْوَهَّابُ", "en": "Indeed, You are\nthe Bestower.", "ref": "3:8c", "surah": 3, "ayah": 8},
    ]},

    # 89 — Surah Al-Waqiah — The Inevitable
    {"title": "Al-Waqiah — The Inevitable Event", "verses": [
        {"ar": "إِذَا وَقَعَتِ الْوَاقِعَةُ", "en": "When the Inevitable Event occurs,", "ref": "56:1", "surah": 56, "ayah": 1},
        {"ar": "لَيْسَ لِوَقْعَتِهَا كَاذِبَةٌ", "en": "There is, at its occurrence,\nno denial.", "ref": "56:2", "surah": 56, "ayah": 2},
        {"ar": "خَافِضَةٌ رَّافِعَةٌ", "en": "It will bring down\nand raise up.", "ref": "56:3", "surah": 56, "ayah": 3},
    ]},

    # 90 — The People of the Right Hand
    {"title": "The People of the Right Hand", "verses": [
        {"ar": "وَأَصْحَابُ الْيَمِينِ مَا أَصْحَابُ الْيَمِينِ", "en": "And the companions of the right —\nwhat are the companions of the right?", "ref": "56:27", "surah": 56, "ayah": 27},
        {"ar": "فِي سِدْرٍ مَّخْضُودٍ", "en": "They will be among\nthornless lote trees,", "ref": "56:28", "surah": 56, "ayah": 28},
        {"ar": "وَطَلْحٍ مَّنضُودٍ", "en": "And clustered plantains,", "ref": "56:29", "surah": 56, "ayah": 29},
        {"ar": "وَظِلٍّ مَّمْدُودٍ", "en": "And shade extended,", "ref": "56:30", "surah": 56, "ayah": 30},
        {"ar": "وَمَاءٍ مَّسْكُوبٍ", "en": "And water poured out,", "ref": "56:31", "surah": 56, "ayah": 31},
    ]},

    # 91 — Glorifying Allah
    {"title": "Glorifying Allah — Tasbih", "verses": [
        {"ar": "سَبَّحَ لِلّٰهِ مَا فِي السَّمَاوَاتِ وَالْأَرْضِ", "en": "Whatever is in the heavens\nand earth glorifies Allah,", "ref": "57:1a", "surah": 57, "ayah": 1},
        {"ar": "وَهُوَ الْعَزِيزُ الْحَكِيمُ", "en": "And He is the Exalted in Might,\nthe Wise.", "ref": "57:1b", "surah": 57, "ayah": 1},
        {"ar": "لَهُ مُلْكُ السَّمَاوَاتِ وَالْأَرْضِ يُحْيِي وَيُمِيتُ", "en": "His is the dominion of the heavens\nand earth. He gives life\nand causes death.", "ref": "57:2", "surah": 57, "ayah": 2},
        {"ar": "وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ", "en": "And He is over all things\ncompetent.", "ref": "57:3b", "surah": 57, "ayah": 3},
    ]},

    # 92 — Allah is Al-Awwal and Al-Akhir
    {"title": "The First and The Last", "verses": [
        {"ar": "هُوَ الْأَوَّلُ وَالْآخِرُ وَالظَّاهِرُ وَالْبَاطِنُ", "en": "He is the First and the Last,\nthe Ascendant and the Intimate,", "ref": "57:3a", "surah": 57, "ayah": 3},
        {"ar": "وَهُوَ بِكُلِّ شَيْءٍ عَلِيمٌ", "en": "And He is,\nof all things, Knowing.", "ref": "57:3b", "surah": 57, "ayah": 3},
    ]},

    # 93 — Surah Al-Hadid — The Iron
    {"title": "This World is Fleeting", "verses": [
        {"ar": "اعْلَمُوا أَنَّمَا الْحَيَاةُ الدُّنْيَا لَعِبٌ وَلَهْوٌ وَزِينَةٌ", "en": "Know that the life of this world\nis but amusement and diversion\nand adornment,", "ref": "57:20a", "surah": 57, "ayah": 20},
        {"ar": "وَتَفَاخُرٌ بَيْنَكُمْ وَتَكَاثُرٌ فِي الْأَمْوَالِ وَالْأَوْلَادِ", "en": "And boasting among yourselves\nand competition in increase\nof wealth and children.", "ref": "57:20b", "surah": 57, "ayah": 20},
        {"ar": "وَمَا الْحَيَاةُ الدُّنْيَا إِلَّا مَتَاعُ الْغُرُورِ", "en": "And the worldly life is not but\nthe enjoyment of self-delusion.", "ref": "57:20c", "surah": 57, "ayah": 20},
    ]},

    # 94 — Competing for the Hereafter
    {"title": "Race Toward the Hereafter", "verses": [
        {"ar": "سَابِقُوا إِلَىٰ مَغْفِرَةٍ مِّن رَّبِّكُمْ وَجَنَّةٍ عَرْضُهَا كَعَرْضِ السَّمَاءِ وَالْأَرْضِ", "en": "Race toward forgiveness\nfrom your Lord and a garden\nwhose width is like the width of the heavens and earth,", "ref": "57:21a", "surah": 57, "ayah": 21},
        {"ar": "أُعِدَّتْ لِلَّذِينَ آمَنُوا بِاللّٰهِ وَرُسُلِهِ", "en": "Prepared for those who believed\nin Allah and His messengers.", "ref": "57:21b", "surah": 57, "ayah": 21},
        {"ar": "ذَٰلِكَ فَضْلُ اللّٰهِ يُؤْتِيهِ مَن يَشَاءُ", "en": "That is the bounty of Allah\nwhich He gives to whom He wills.", "ref": "57:21c", "surah": 57, "ayah": 21},
    ]},

    # 95 — Allah Sees Everything
    {"title": "Allah Sees Everything", "verses": [
        {"ar": "أَلَمْ تَرَ أَنَّ اللّٰهَ يَعْلَمُ مَا فِي السَّمَاوَاتِ وَمَا فِي الْأَرْضِ", "en": "Do you not see that Allah knows\nwhat is in the heavens\nand what is on the earth?", "ref": "58:7a", "surah": 58, "ayah": 7},
        {"ar": "مَا يَكُونُ مِن نَّجْوَىٰ ثَلَاثَةٍ إِلَّا هُوَ رَابِعُهُمْ", "en": "There is no private conversation\nbetween three but that He is\nthe fourth of them,", "ref": "58:7b", "surah": 58, "ayah": 7},
        {"ar": "وَلَا خَمْسَةٍ إِلَّا هُوَ سَادِسُهُمْ", "en": "Nor between five\nbut that He is the sixth of them,", "ref": "58:7c", "surah": 58, "ayah": 7},
        {"ar": "وَهُوَ مَعَهُمْ أَيْنَ مَا كَانُوا", "en": "And He is with them\nwherever they are.", "ref": "58:7d", "surah": 58, "ayah": 7},
    ]},

    # 96 — Surah Al-Mulk — Protection
    {"title": "Protection Through Al-Mulk", "verses": [
        {"ar": "أَمَّن هَٰذَا الَّذِي هُوَ جُندٌ لَّكُمْ يَنصُرُكُم مِّن دُونِ الرَّحْمَٰنِ", "en": "Who is it that could be\nan army for you to aid you\nother than the Most Merciful?", "ref": "67:20", "surah": 67, "ayah": 20},
        {"ar": "قُلْ هُوَ الرَّحْمَٰنُ آمَنَّا بِهِ وَعَلَيْهِ تَوَكَّلْنَا", "en": "Say: He is the Most Merciful;\nwe have believed in Him\nand upon Him we rely.", "ref": "67:29a", "surah": 67, "ayah": 29},
    ]},

    # 97 — Al-Haqqah — The Reality
    {"title": "Al-Haqqah — The Reality", "verses": [
        {"ar": "الْحَاقَّةُ", "en": "The Reality.", "ref": "69:1", "surah": 69, "ayah": 1},
        {"ar": "مَا الْحَاقَّةُ", "en": "What is the Reality?", "ref": "69:2", "surah": 69, "ayah": 2},
        {"ar": "وَمَا أَدْرَاكَ مَا الْحَاقَّةُ", "en": "And what can make you know\nwhat the Reality is?", "ref": "69:3", "surah": 69, "ayah": 3},
    ]},

    # 98 — Al-Ma'arij — Ways of Ascent
    {"title": "Patience is Beautiful", "verses": [
        {"ar": "إِنَّ الْإِنسَانَ خُلِقَ هَلُوعًا", "en": "Indeed, mankind was created\nanxious:", "ref": "70:19", "surah": 70, "ayah": 19},
        {"ar": "إِذَا مَسَّهُ الشَّرُّ جَزُوعًا", "en": "When evil touches him,\nimpatient,", "ref": "70:20", "surah": 70, "ayah": 20},
        {"ar": "وَإِذَا مَسَّهُ الْخَيْرُ مَنُوعًا", "en": "And when good touches him,\nwithholding of it.", "ref": "70:21", "surah": 70, "ayah": 21},
        {"ar": "إِلَّا الْمُصَلِّينَ", "en": "Except the observers\nof prayer,", "ref": "70:22", "surah": 70, "ayah": 22},
        {"ar": "الَّذِينَ هُمْ عَلَىٰ صَلَاتِهِمْ دَائِمُونَ", "en": "Those who are\nconsistent in their prayer.", "ref": "70:23", "surah": 70, "ayah": 23},
    ]},

    # 99 — Surah Nuh — Prophet Nuh's Dua
    {"title": "The Dua of Prophet Nuh", "verses": [
        {"ar": "رَّبِّ اغْفِرْ لِي وَلِوَالِدَيَّ وَلِمَن دَخَلَ بَيْتِيَ مُؤْمِنًا", "en": "My Lord, forgive me\nand my parents and whoever\nenters my house a believer.", "ref": "71:28a", "surah": 71, "ayah": 28},
        {"ar": "وَلِلْمُؤْمِنِينَ وَالْمُؤْمِنَاتِ", "en": "And the believing men\nand believing women.", "ref": "71:28b", "surah": 71, "ayah": 28},
    ]},

    # 100 — Surah Al-Jinn
    {"title": "The Jinn Bear Witness", "verses": [
        {"ar": "قُلْ أُوحِيَ إِلَيَّ أَنَّهُ اسْتَمَعَ نَفَرٌ مِّنَ الْجِنِّ", "en": "Say: It has been revealed to me\nthat a group of the jinn\nlistened,", "ref": "72:1a", "surah": 72, "ayah": 1},
        {"ar": "فَقَالُوا إِنَّا سَمِعْنَا قُرْآنًا عَجَبًا", "en": "And said: Indeed, we have heard\na wondrous Quran.", "ref": "72:1b", "surah": 72, "ayah": 1},
        {"ar": "يَهْدِي إِلَى الرُّشْدِ فَآمَنَّا بِهِ", "en": "It guides to the right course,\nand we have believed in it.", "ref": "72:2a", "surah": 72, "ayah": 2},
    ]},

    # 101 — Al-Muddaththir
    {"title": "Rise and Warn", "verses": [
        {"ar": "يَا أَيُّهَا الْمُدَّثِّرُ", "en": "O you who covers himself!", "ref": "74:1", "surah": 74, "ayah": 1},
        {"ar": "قُمْ فَأَنذِرْ", "en": "Arise and warn.", "ref": "74:2", "surah": 74, "ayah": 2},
        {"ar": "وَرَبَّكَ فَكَبِّرْ", "en": "And your Lord glorify.", "ref": "74:3", "surah": 74, "ayah": 3},
        {"ar": "وَثِيَابَكَ فَطَهِّرْ", "en": "And your garments purify.", "ref": "74:4", "surah": 74, "ayah": 4},
        {"ar": "وَالرُّجْزَ فَاهْجُرْ", "en": "And uncleanliness avoid.", "ref": "74:5", "surah": 74, "ayah": 5},
    ]},

    # 102 — Al-Insan — Gratitude to Allah
    {"title": "Gratitude for Allah's Blessings", "verses": [
        {"ar": "هَلْ أَتَىٰ عَلَى الْإِنسَانِ حِينٌ مِّنَ الدَّهْرِ لَمْ يَكُن شَيْئًا مَّذْكُورًا", "en": "Has there not come upon man\na period of time when he was not\na thing even mentioned?", "ref": "76:1", "surah": 76, "ayah": 1},
        {"ar": "إِنَّا خَلَقْنَا الْإِنسَانَ مِن نُّطْفَةٍ أَمْشَاجٍ نَّبْتَلِيهِ", "en": "Indeed, We created man\nfrom a sperm-drop mixture\nthat We may test him.", "ref": "76:2a", "surah": 76, "ayah": 2},
        {"ar": "فَجَعَلْنَاهُ سَمِيعًا بَصِيرًا", "en": "And We made him\nhearing and seeing.", "ref": "76:2b", "surah": 76, "ayah": 2},
    ]},

    # 103 — Al-Mursalat
    {"title": "Woe to the Deniers", "verses": [
        {"ar": "وَيْلٌ يَوْمَئِذٍ لِّلْمُكَذِّبِينَ", "en": "Woe that Day\nto the deniers.", "ref": "77:15", "surah": 77, "ayah": 15},
        {"ar": "أَلَمْ نَخْلُقكُّم مِّن مَّاءٍ مَّهِينٍ", "en": "Did We not create you\nfrom a liquid disdained?", "ref": "77:20", "surah": 77, "ayah": 20},
        {"ar": "فَقَدَرْنَا فَنِعْمَ الْقَادِرُونَ", "en": "And We determined it\nand how excellent are We\nto determine.", "ref": "77:23", "surah": 77, "ayah": 23},
    ]},

    # 104 — An-Naba — The Great News
    {"title": "An-Naba — The Great News", "verses": [
        {"ar": "عَمَّ يَتَسَاءَلُونَ", "en": "About what are they asking one another?", "ref": "78:1", "surah": 78, "ayah": 1},
        {"ar": "عَنِ النَّبَإِ الْعَظِيمِ", "en": "About the great news,", "ref": "78:2", "surah": 78, "ayah": 2},
        {"ar": "الَّذِي هُمْ فِيهِ مُخْتَلِفُونَ", "en": "That over which\nthey are in disagreement.", "ref": "78:3", "surah": 78, "ayah": 3},
        {"ar": "أَلَمْ نَجْعَلِ الْأَرْضَ مِهَادًا", "en": "Have We not made\nthe earth a resting place?", "ref": "78:6", "surah": 78, "ayah": 6},
        {"ar": "وَالْجِبَالَ أَوْتَادًا", "en": "And the mountains\nas stakes?", "ref": "78:7", "surah": 78, "ayah": 7},
    ]},

    # 105 — An-Nazi'at
    {"title": "The Hereafter is Near", "verses": [
        {"ar": "يَوْمَ تَرْجُفُ الرَّاجِفَةُ", "en": "On the Day\nthe blast will convulse,", "ref": "79:6", "surah": 79, "ayah": 6},
        {"ar": "تَتْبَعُهَا الرَّادِفَةُ", "en": "There will follow it\nthe subsequent one.", "ref": "79:7", "surah": 79, "ayah": 7},
        {"ar": "أَأَنتُمْ أَشَدُّ خَلْقًا أَمِ السَّمَاءُ بَنَاهَا", "en": "Are you a more difficult creation\nor is the heaven?\nHe constructed it.", "ref": "79:27", "surah": 79, "ayah": 27},
    ]},

    # 106 — Abasa — He Frowned
    {"title": "Equal Worth of Every Soul", "verses": [
        {"ar": "فَمَن شَاءَ ذَكَرَهُ", "en": "So whoever wills\nmay remember it.", "ref": "80:12", "surah": 80, "ayah": 12},
        {"ar": "فِي صُحُفٍ مُّكَرَّمَةٍ", "en": "In honored sheets of scripture,", "ref": "80:13", "surah": 80, "ayah": 13},
        {"ar": "مَّرْفُوعَةٍ مُّطَهَّرَةٍ", "en": "Exalted and purified,", "ref": "80:14", "surah": 80, "ayah": 14},
        {"ar": "بِأَيْدِي سَفَرَةٍ", "en": "By the hands\nof messenger-angels,", "ref": "80:15", "surah": 80, "ayah": 15},
        {"ar": "كِرَامٍ بَرَرَةٍ", "en": "Noble and dutiful.", "ref": "80:16", "surah": 80, "ayah": 16},
    ]},

    # 107 — At-Takwir — The Folding Up
    {"title": "At-Takwir — The Folding Up", "verses": [
        {"ar": "إِذَا الشَّمْسُ كُوِّرَتْ", "en": "When the sun is wrapped up,", "ref": "81:1", "surah": 81, "ayah": 1},
        {"ar": "وَإِذَا النُّجُومُ انكَدَرَتْ", "en": "And when the stars fall,", "ref": "81:2", "surah": 81, "ayah": 2},
        {"ar": "وَإِذَا الْجِبَالُ سُيِّرَتْ", "en": "And when the mountains are removed,", "ref": "81:3", "surah": 81, "ayah": 3},
        {"ar": "عَلِمَتْ نَفْسٌ مَّا أَحْضَرَتْ", "en": "Every soul will know\nwhat it has brought.", "ref": "81:14", "surah": 81, "ayah": 14},
    ]},

    # 108 — Al-Infitar — The Cleaving
    {"title": "Al-Infitar — The Cleaving", "verses": [
        {"ar": "إِذَا السَّمَاءُ انفَطَرَتْ", "en": "When the sky breaks apart,", "ref": "82:1", "surah": 82, "ayah": 1},
        {"ar": "يَا أَيُّهَا الْإِنسَانُ مَا غَرَّكَ بِرَبِّكَ الْكَرِيمِ", "en": "O mankind, what has deceived you\nconcerning your Lord,\nthe Generous,", "ref": "82:6", "surah": 82, "ayah": 6},
        {"ar": "الَّذِي خَلَقَكَ فَسَوَّاكَ فَعَدَلَكَ", "en": "Who created you, proportioned you,\nand assembled you?", "ref": "82:7", "surah": 82, "ayah": 7},
    ]},

    # 109 — Al-Mutaffifin — The Defrauders
    {"title": "Justice in All Things", "verses": [
        {"ar": "وَيْلٌ لِّلْمُطَفِّفِينَ", "en": "Woe to those who give less\nthan due,", "ref": "83:1", "surah": 83, "ayah": 1},
        {"ar": "الَّذِينَ إِذَا اكْتَالُوا عَلَى النَّاسِ يَسْتَوْفُونَ", "en": "Who, when they take a measure\nfrom people, take in full,", "ref": "83:2", "surah": 83, "ayah": 2},
        {"ar": "وَإِذَا كَالُوهُمْ أَو وَّزَنُوهُمْ يُخْسِرُونَ", "en": "But if they give by measure\nor by weight to them,\nthey cause loss.", "ref": "83:3", "surah": 83, "ayah": 3},
    ]},

    # 110 — Al-Buruj — The Constellations
    {"title": "Allah is the Forgiving, the Loving", "verses": [
        {"ar": "وَهُوَ الْغَفُورُ الْوَدُودُ", "en": "And He is\nthe Forgiving, the Affectionate,", "ref": "85:14", "surah": 85, "ayah": 14},
        {"ar": "ذُو الْعَرْشِ الْمَجِيدُ", "en": "Owner of the Glorious Throne,", "ref": "85:15", "surah": 85, "ayah": 15},
        {"ar": "فَعَّالٌ لِّمَا يُرِيدُ", "en": "Effecter of what He intends.", "ref": "85:16", "surah": 85, "ayah": 16},
    ]},

    # 111 — At-Tariq — The Night Star
    {"title": "At-Tariq — The Night Star", "verses": [
        {"ar": "وَالسَّمَاءِ وَالطَّارِقِ", "en": "By the sky\nand the night comer,", "ref": "86:1", "surah": 86, "ayah": 1},
        {"ar": "وَمَا أَدْرَاكَ مَا الطَّارِقُ", "en": "And what can make you know\nwhat is the night comer?", "ref": "86:2", "surah": 86, "ayah": 2},
        {"ar": "النَّجْمُ الثَّاقِبُ", "en": "It is the piercing star.", "ref": "86:3", "surah": 86, "ayah": 3},
        {"ar": "إِن كُلُّ نَفْسٍ لَّمَّا عَلَيْهَا حَافِظٌ", "en": "There is no soul\nbut that it has over it a protector.", "ref": "86:4", "surah": 86, "ayah": 4},
    ]},

    # 112 — Al-A'la — The Most High
    {"title": "Al-A'la — The Most High", "verses": [
        {"ar": "سَبِّحِ اسْمَ رَبِّكَ الْأَعْلَى", "en": "Exalt the name of your Lord,\nthe Most High,", "ref": "87:1", "surah": 87, "ayah": 1},
        {"ar": "الَّذِي خَلَقَ فَسَوَّىٰ", "en": "Who created and proportioned,", "ref": "87:2", "surah": 87, "ayah": 2},
        {"ar": "وَالَّذِي قَدَّرَ فَهَدَىٰ", "en": "And who destined\nand then guided,", "ref": "87:3", "surah": 87, "ayah": 3},
        {"ar": "قَدْ أَفْلَحَ مَن تَزَكَّىٰ", "en": "He has certainly succeeded\nwho purifies himself,", "ref": "87:14", "surah": 87, "ayah": 14},
        {"ar": "وَذَكَرَ اسْمَ رَبِّهِ فَصَلَّىٰ", "en": "And mentions the name\nof his Lord and prays.", "ref": "87:15", "surah": 87, "ayah": 15},
    ]},

    # 113 — Al-Balad — The City
    {"title": "The Uphill Road", "verses": [
        {"ar": "وَهَدَيْنَاهُ النَّجْدَيْنِ", "en": "And We have shown him\nthe two ways.", "ref": "90:10", "surah": 90, "ayah": 10},
        {"ar": "فَلَا اقْتَحَمَ الْعَقَبَةَ", "en": "But he has not\nattempted the difficult path.", "ref": "90:11", "surah": 90, "ayah": 11},
        {"ar": "وَمَا أَدْرَاكَ مَا الْعَقَبَةُ", "en": "And what can make you know\nwhat is the difficult path?", "ref": "90:12", "surah": 90, "ayah": 12},
        {"ar": "فَكُّ رَقَبَةٍ", "en": "It is the freeing\nof a slave,", "ref": "90:13", "surah": 90, "ayah": 13},
        {"ar": "أَوْ إِطْعَامٌ فِي يَوْمٍ ذِي مَسْغَبَةٍ", "en": "Or feeding on a day of hunger,", "ref": "90:14", "surah": 90, "ayah": 14},
    ]},

    # 114 — Al-Shams — The Sun
    {"title": "Al-Shams — The Sun", "verses": [
        {"ar": "وَالشَّمْسِ وَضُحَاهَا", "en": "By the sun and its brightness,", "ref": "91:1", "surah": 91, "ayah": 1},
        {"ar": "وَالْقَمَرِ إِذَا تَلَاهَا", "en": "And the moon when\nit follows it,", "ref": "91:2", "surah": 91, "ayah": 2},
        {"ar": "وَالنَّهَارِ إِذَا جَلَّاهَا", "en": "And the day\nwhen it displays it,", "ref": "91:3", "surah": 91, "ayah": 3},
        {"ar": "قَدْ أَفْلَحَ مَن زَكَّاهَا", "en": "He has succeeded\nwho purifies it,", "ref": "91:9", "surah": 91, "ayah": 9},
        {"ar": "وَقَدْ خَابَ مَن دَسَّاهَا", "en": "And he has failed\nwho instills it with corruption.", "ref": "91:10", "surah": 91, "ayah": 10},
    ]},

    # 115 — Al-Layl — The Night
    {"title": "Al-Layl — The Night", "verses": [
        {"ar": "وَاللَّيْلِ إِذَا يَغْشَىٰ", "en": "By the night\nwhen it covers,", "ref": "92:1", "surah": 92, "ayah": 1},
        {"ar": "وَالنَّهَارِ إِذَا تَجَلَّىٰ", "en": "And the day\nwhen it appears,", "ref": "92:2", "surah": 92, "ayah": 2},
        {"ar": "إِنَّ سَعْيَكُمْ لَشَتَّىٰ", "en": "Indeed, your efforts\nare diverse.", "ref": "92:4", "surah": 92, "ayah": 4},
    ]},

    # 116 — Al-Alaq — The Clot
    {"title": "Al-Alaq — Read!", "verses": [
        {"ar": "اقْرَأْ بِاسْمِ رَبِّكَ الَّذِي خَلَقَ", "en": "Read in the name of your Lord\nwho created,", "ref": "96:1", "surah": 96, "ayah": 1},
        {"ar": "خَلَقَ الْإِنسَانَ مِنْ عَلَقٍ", "en": "Created man\nfrom a clinging substance.", "ref": "96:2", "surah": 96, "ayah": 2},
        {"ar": "اقْرَأْ وَرَبُّكَ الْأَكْرَمُ", "en": "Read, and your Lord\nis the Most Generous,", "ref": "96:3", "surah": 96, "ayah": 3},
        {"ar": "الَّذِي عَلَّمَ بِالْقَلَمِ", "en": "Who taught\nby the pen,", "ref": "96:4", "surah": 96, "ayah": 4},
        {"ar": "عَلَّمَ الْإِنسَانَ مَا لَمْ يَعْلَمْ", "en": "Taught man\nthat which he knew not.", "ref": "96:5", "surah": 96, "ayah": 5},
    ]},

    # 117 — Al-Bayyinah
    {"title": "The Clear Evidence", "verses": [
        {"ar": "إِنَّ الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ أُولَٰئِكَ هُمْ خَيْرُ الْبَرِيَّةِ", "en": "Indeed, those who have believed\nand done righteous deeds —\nthose are the best of creatures.", "ref": "98:7", "surah": 98, "ayah": 7},
        {"ar": "جَزَاؤُهُمْ عِندَ رَبِّهِمْ جَنَّاتُ عَدْنٍ تَجْرِي مِن تَحْتِهَا الْأَنْهَارُ", "en": "Their reward with Allah will be\ngardens of perpetual residence\nbeneath which rivers flow,", "ref": "98:8a", "surah": 98, "ayah": 8},
        {"ar": "خَالِدِينَ فِيهَا أَبَدًا رَّضِيَ اللّٰهُ عَنْهُمْ وَرَضُوا عَنْهُ", "en": "Wherein they abide forever,\nAllah being pleased with them\nand they pleased with Him.", "ref": "98:8b", "surah": 98, "ayah": 8},
    ]},

    # 118 — Al-Takathur — Rivalry
    {"title": "Al-Takathur — The Rivalry", "verses": [
        {"ar": "أَلْهَاكُمُ التَّكَاثُرُ", "en": "Rivalry in worldly increase\nhas distracted you,", "ref": "102:1", "surah": 102, "ayah": 1},
        {"ar": "حَتَّىٰ زُرْتُمُ الْمَقَابِرَ", "en": "Until you visit\nthe graveyards.", "ref": "102:2", "surah": 102, "ayah": 2},
        {"ar": "كَلَّا سَوْفَ تَعْلَمُونَ", "en": "No! You are going\nto know.", "ref": "102:3", "surah": 102, "ayah": 3},
        {"ar": "ثُمَّ كَلَّا سَوْفَ تَعْلَمُونَ", "en": "Then, no! You are going\nto know.", "ref": "102:4", "surah": 102, "ayah": 4},
    ]},

    # 119 — Al-Humazah
    {"title": "Beware of Backbiting", "verses": [
        {"ar": "وَيْلٌ لِّكُلِّ هُمَزَةٍ لُّمَزَةٍ", "en": "Woe to every scorner\nand mocker,", "ref": "104:1", "surah": 104, "ayah": 1},
        {"ar": "الَّذِي جَمَعَ مَالًا وَعَدَّدَهُ", "en": "Who collects wealth\nand repeatedly counts it.", "ref": "104:2", "surah": 104, "ayah": 2},
        {"ar": "يَحْسَبُ أَنَّ مَالَهُ أَخْلَدَهُ", "en": "He thinks that his wealth\nwill make him immortal.", "ref": "104:3", "surah": 104, "ayah": 3},
    ]},

    # 120 — Al-Fil — The Elephant
    {"title": "Al-Fil — Allah Protects", "verses": [
        {"ar": "أَلَمْ تَرَ كَيْفَ فَعَلَ رَبُّكَ بِأَصْحَابِ الْفِيلِ", "en": "Have you not considered\nhow your Lord dealt\nwith the companions of the elephant?", "ref": "105:1", "surah": 105, "ayah": 1},
        {"ar": "أَلَمْ يَجْعَلْ كَيْدَهُمْ فِي تَضْلِيلٍ", "en": "Did He not make\ntheir plan into misguidance?", "ref": "105:2", "surah": 105, "ayah": 2},
        {"ar": "وَأَرْسَلَ عَلَيْهِمْ طَيْرًا أَبَابِيلَ", "en": "And He sent against them\nbirds in flocks,", "ref": "105:3", "surah": 105, "ayah": 3},
    ]},

    # 121 — Quraysh
    {"title": "Quraysh — Allah's Blessings", "verses": [
        {"ar": "لِإِيلَافِ قُرَيْشٍ", "en": "For the accustomed security\nof the Quraysh,", "ref": "106:1", "surah": 106, "ayah": 1},
        {"ar": "إِيلَافِهِمْ رِحْلَةَ الشِّتَاءِ وَالصَّيْفِ", "en": "Their accustomed security\nin the journey of winter and summer,", "ref": "106:2", "surah": 106, "ayah": 2},
        {"ar": "فَلْيَعْبُدُوا رَبَّ هَٰذَا الْبَيْتِ", "en": "Let them worship\nthe Lord of this House,", "ref": "106:3", "surah": 106, "ayah": 3},
        {"ar": "الَّذِي أَطْعَمَهُم مِّن جُوعٍ وَآمَنَهُم مِّنْ خَوْفٍ", "en": "Who has fed them, saving them from hunger,\nand made them safe,\nsaving them from fear.", "ref": "106:4", "surah": 106, "ayah": 4},
    ]},

    # 122 — Al-Ma'un — Small Kindnesses
    {"title": "Al-Ma'un — Small Kindnesses", "verses": [
        {"ar": "أَرَأَيْتَ الَّذِي يُكَذِّبُ بِالدِّينِ", "en": "Have you seen the one\nwho denies the Recompense?", "ref": "107:1", "surah": 107, "ayah": 1},
        {"ar": "فَذَٰلِكَ الَّذِي يَدُعُّ الْيَتِيمَ", "en": "For that is the one\nwho drives away the orphan,", "ref": "107:2", "surah": 107, "ayah": 2},
        {"ar": "وَلَا يَحُضُّ عَلَىٰ طَعَامِ الْمِسْكِينِ", "en": "And does not encourage\nthe feeding of the poor.", "ref": "107:3", "surah": 107, "ayah": 3},
    ]},

    # 123 — Al-Masad — Consequences of Evil
    {"title": "No Wealth Can Save You", "verses": [
        {"ar": "مَا أَغْنَىٰ عَنْهُ مَالُهُ وَمَا كَسَبَ", "en": "His wealth will not avail him\nor that which he gained.", "ref": "111:2", "surah": 111, "ayah": 2},
    ]},

    # 124 — Dua for children
    {"title": "Dua for Righteous Children", "verses": [
        {"ar": "رَبِّ هَبْ لِي مِن لَّدُنكَ ذُرِّيَّةً طَيِّبَةً", "en": "My Lord, grant me\nfrom Yourself a good offspring.", "ref": "3:38b", "surah": 3, "ayah": 38},
        {"ar": "إِنَّكَ سَمِيعُ الدُّعَاءِ", "en": "Indeed, You are\nthe Hearer of supplication.", "ref": "3:38c", "surah": 3, "ayah": 38},
    ]},

    # 125 — Dua of Zakariyya
    {"title": "The Dua of Zakariyya", "verses": [
        {"ar": "رَبِّ لَا تَذَرْنِي فَرْدًا وَأَنتَ خَيْرُ الْوَارِثِينَ", "en": "My Lord, do not leave me alone\nand You are the best of inheritors.", "ref": "21:89", "surah": 21, "ayah": 89},
        {"ar": "فَاسْتَجَبْنَا لَهُ وَوَهَبْنَا لَهُ يَحْيَىٰ", "en": "So We responded to him\nand gave him Yahya.", "ref": "21:90a", "surah": 21, "ayah": 90},
        {"ar": "وَأَصْلَحْنَا لَهُ زَوْجَهُ", "en": "And We corrected\nhis wife for him.", "ref": "21:90b", "surah": 21, "ayah": 90},
    ]},

    # 126 — The Promise of Allah
    {"title": "The Promise of Allah", "verses": [
        {"ar": "وَعْدَ اللّٰهِ لَا يُخْلِفُ اللّٰهُ وَعْدَهُ", "en": "The promise of Allah —\nAllah does not fail\nin His promise.", "ref": "30:6b", "surah": 30, "ayah": 6},
        {"ar": "وَلَٰكِنَّ أَكْثَرَ النَّاسِ لَا يَعْلَمُونَ", "en": "But most of the people\ndo not know.", "ref": "30:6c", "surah": 30, "ayah": 6},
    ]},

    # 127 — Allah is Near
    {"title": "Allah is Closer Than You Think", "verses": [
        {"ar": "وَلَقَدْ خَلَقْنَا الْإِنسَانَ وَنَعْلَمُ مَا تُوَسْوِسُ بِهِ نَفْسُهُ", "en": "We have already created man\nand know what his soul\nwhispers to him.", "ref": "50:16a", "surah": 50, "ayah": 16},
        {"ar": "وَنَحْنُ أَقْرَبُ إِلَيْهِ مِنْ حَبْلِ الْوَرِيدِ", "en": "And We are closer to him\nthan his jugular vein.", "ref": "50:16b", "surah": 50, "ayah": 16},
    ]},

    # 128 — The Soul at Rest
    {"title": "The Reassured Soul", "verses": [
        {"ar": "يَا أَيَّتُهَا النَّفْسُ الْمُطْمَئِنَّةُ", "en": "O reassured soul,", "ref": "89:27", "surah": 89, "ayah": 27},
        {"ar": "ارْجِعِي إِلَىٰ رَبِّكِ رَاضِيَةً مَّرْضِيَّةً", "en": "Return to your Lord\nwell-pleased and pleasing to Him,", "ref": "89:28", "surah": 89, "ayah": 28},
        {"ar": "فَادْخُلِي فِي عِبَادِي", "en": "And enter among\nMy righteous servants,", "ref": "89:29", "surah": 89, "ayah": 29},
        {"ar": "وَادْخُلِي جَنَّتِي", "en": "And enter My Paradise.", "ref": "89:30", "surah": 89, "ayah": 30},
    ]},

    # 129 — The Greatness of the Quran
    {"title": "The Greatness of the Quran", "verses": [
        {"ar": "لَوْ أَنزَلْنَا هَٰذَا الْقُرْآنَ عَلَىٰ جَبَلٍ", "en": "If We had sent down\nthis Quran upon a mountain,", "ref": "59:21a", "surah": 59, "ayah": 21},
        {"ar": "لَّرَأَيْتَهُ خَاشِعًا مُّتَصَدِّعًا مِّنْ خَشْيَةِ اللّٰهِ", "en": "You would have seen it\nhumbled and split apart\nfrom fear of Allah.", "ref": "59:21b", "surah": 59, "ayah": 21},
        {"ar": "وَتِلْكَ الْأَمْثَالُ نَضْرِبُهَا لِلنَّاسِ لَعَلَّهُمْ يَتَفَكَّرُونَ", "en": "And these examples We present\nto the people that perhaps\nthey will give thought.", "ref": "59:21c", "surah": 59, "ayah": 21},
    ]},

    # 130 — The Correct Path
    {"title": "The Straight Path", "verses": [
        {"ar": "وَأَنَّ هَٰذَا صِرَاطِي مُسْتَقِيمًا فَاتَّبِعُوهُ", "en": "And this is My path,\nwhich is straight,\nso follow it,", "ref": "6:153a", "surah": 6, "ayah": 153},
        {"ar": "وَلَا تَتَّبِعُوا السُّبُلَ فَتَفَرَّقَ بِكُمْ عَن سَبِيلِهِ", "en": "And do not follow other ways,\nfor you will be separated\nfrom His way.", "ref": "6:153b", "surah": 6, "ayah": 153},
    ]},
]

# ═══════════════════════════════════════════════════════════════════════════
# 🔧 EXTENSION JUSQU'À 200 PASSAGES — générés depuis l'API officielle Quran.com
# ═══════════════════════════════════════════════════════════════════════════
# IMPORTANT : on ne tape JAMAIS de texte coranique supplémentaire "de mémoire".
# Le risque d'erreur sur un texte sacré est trop grand. À la place, on va
# chercher le texte arabe officiel (script Uthmani) + une traduction anglaise
# sourcée (Dr. Mustafa Khattab, The Clear Quran) directement sur l'API
# publique de Quran.com, pour les sourates qui ne sont pas encore couvertes
# par CURATED_PASSAGES ci-dessus. Résultat mis en cache (le texte du Coran ne
# change pas) pour ne faire ce travail réseau qu'une seule fois.
CURATED_PASSAGES   = PASSAGES
TARGET_PASSAGE_CNT = 200
PASSAGES_CACHE_FILE = OUT_DIR / "cache" / "passages_api.json"
PASSAGES_CACHE_MAX_AGE_S = 90 * 24 * 3600  # 90 jours — le texte du Coran est immuable
QURAN_API_BASE = "https://api.quran.com/api/v4"
CLEAR_QURAN_TRANSLATION_ID = 131  # Dr. Mustafa Khattab, The Clear Quran (EN)

def _strip_html(text):
    import re as _re
    return _re.sub(r"<[^>]+>", "", text or "").strip()

def _fully_covered_surahs(curated):
    """Sourates déjà entièrement couvertes par un passage curaté (on évite
    de générer un doublon pour ces sourates-là)."""
    by_surah = {}
    for p in curated:
        for v in p["verses"]:
            by_surah.setdefault(v["surah"], set()).add(v["ayah"])
    covered = set()
    for s, ayat in by_surah.items():
        # Heuristique : si on a au moins 1 et la dernière ayah connue de cette
        # sourate dans les passages curatés, on la considère "potentiellement"
        # déjà traitée — la vraie déduplication se fait en comparant au
        # verses_count réel renvoyé par l'API au moment de la génération.
        covered.add(s)
    return covered

def _fetch_chapters_meta():
    url = f"{QURAN_API_BASE}/chapters?language=en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    return data.get("chapters", [])

def _fetch_chapter_verses(chapter_id):
    """Récupère TOUTES les ayat d'une sourate (texte Uthmani + traduction),
    en paginant jusqu'à épuisement (l'API limite le nombre de résultats par page)."""
    out, page = [], 1
    while True:
        url = (f"{QURAN_API_BASE}/verses/by_chapter/{chapter_id}"
               f"?language=en&fields=text_uthmani&translations={CLEAR_QURAN_TRANSLATION_ID}"
               f"&per_page=50&page={page}")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        verses = data.get("verses", [])
        out.extend(verses)
        pagination = data.get("pagination", {})
        if not pagination.get("next_page"):
            break
        page = pagination["next_page"]
    return out

def _build_passages_from_api(curated, target_total):
    need = target_total - len(curated)
    if need <= 0:
        return []
    if PASSAGES_CACHE_FILE.exists():
        try:
            cached = json.loads(PASSAGES_CACHE_FILE.read_text())
            age = time.time() - cached.get("ts", 0)
            if age < PASSAGES_CACHE_MAX_AGE_S and cached.get("passages"):
                print(f"   📖 Passages additionnels (cache) : {len(cached['passages'])}")
                return cached["passages"][:need]
        except Exception:
            pass

    print(f"   📖 Génération de jusqu'à {need} passages additionnels depuis l'API Quran.com...")
    covered_surahs = _fully_covered_surahs(curated)
    extra = []
    try:
        chapters = _fetch_chapters_meta()
    except Exception as e:
        print(f"   ⚠ Impossible de joindre l'API Quran.com ({e}) — extension annulée, on garde les {len(curated)} passages curatés.")
        return []

    CHUNK_SIZE = 7  # ~7 ayat par écran-passage, cohérent avec le style des passages curatés
    for ch in chapters:
        if len(extra) >= need:
            break
        cid = ch.get("id")
        vcount = ch.get("verses_count", 0)
        name_en = ch.get("translated_name", {}).get("name") or ch.get("name_simple", f"Surah {cid}")
        name_simple = ch.get("name_simple", f"Surah {cid}")
        if cid in covered_surahs and vcount <= CHUNK_SIZE:
            # Petite sourate déjà entièrement couverte par les passages curatés : on saute.
            continue
        try:
            verses_raw = _fetch_chapter_verses(cid)
        except Exception as e:
            print(f"   ⚠ Sourate {cid} ({name_simple}) ignorée — erreur réseau : {e}")
            continue
        if not verses_raw:
            continue
        # Découpage en blocs de CHUNK_SIZE ayat (la dernière sourate déjà entière
        # si elle tient en un seul bloc, sinon plusieurs écrans successifs).
        for start in range(0, len(verses_raw), CHUNK_SIZE):
            if len(extra) >= need:
                break
            block = verses_raw[start:start + CHUNK_SIZE]
            verses_out = []
            for v in block:
                ayah_num = v.get("verse_number")
                ar_text  = v.get("text_uthmani", "").strip()
                trs      = v.get("translations", [])
                en_text  = _strip_html(trs[0]["text"]) if trs else ""
                if not ar_text or not en_text:
                    continue
                verses_out.append({
                    "ar": ar_text, "en": en_text,
                    "ref": f"{cid}:{ayah_num}", "surah": cid, "ayah": ayah_num,
                })
            if not verses_out:
                continue
            if len(block) < CHUNK_SIZE:
                title = f"{name_en} — {name_simple} (complète)" if start == 0 else f"{name_en} — {name_simple} (suite)"
            else:
                rng = f"{block[0].get('verse_number')}-{block[-1].get('verse_number')}"
                title = f"{name_en} — {name_simple} {rng}"
            extra.append({"title": title, "verses": verses_out})
        print(f"      Sourate {cid} ({name_simple}) traitée — total additionnel: {len(extra)}/{need}")

    try:
        PASSAGES_CACHE_FILE.write_text(json.dumps({"ts": time.time(), "passages": extra}, ensure_ascii=False))
    except Exception:
        pass
    print(f"   ✅ {len(extra)} passages additionnels générés depuis l'API officielle")
    return extra

try:
    PASSAGES = CURATED_PASSAGES + _build_passages_from_api(CURATED_PASSAGES, TARGET_PASSAGE_CNT)
except Exception as e:
    print(f"   ⚠ Extension des passages échouée ({e}) — on continue avec les {len(CURATED_PASSAGES)} passages curatés.")
    PASSAGES = CURATED_PASSAGES
print(f"   📚 {len(PASSAGES)} passages disponibles au total ({len(CURATED_PASSAGES)} curatés + {len(PASSAGES) - len(CURATED_PASSAGES)} générés)")

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

# ═══════════════════════════════════════════════════════════════════════════
# Tous les récitateurs de la liste sont utilisables : on affiche le verset
# entier (pas de surlignage mot-à-mot), donc on n'a plus besoin de segments
# CDN précis par mot. La disponibilité de l'audio lui-même est déjà vérifiée
# au moment voulu par dl_audio()/AudioMissingError dans select_verses().
# ═══════════════════════════════════════════════════════════════════════════

PHOTOS = [
    # Sunsets and sunrises
    ("https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?w=1080&h=1920&fit=crop&crop=center", "sunset_orange"),
    ("https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=1080&h=1920&fit=crop&crop=center", "sunset_valley"),
    ("https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1080&h=1920&fit=crop&crop=center", "golden_mountain"),
    ("https://images.unsplash.com/photo-1532274402911-5a369e4c4bb5?w=1080&h=1920&fit=crop&crop=center", "sunset_beach"),
    ("https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=1080&h=1920&fit=crop&crop=center", "lake_sunset"),
    ("https://images.unsplash.com/photo-1502209524164-acea936639a2?w=1080&h=1920&fit=crop&crop=center", "sunrise_lake"),
    ("https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1080&h=1920&fit=crop&crop=center", "golden_lake"),
    ("https://images.unsplash.com/photo-1518021964703-4b2030f03085?w=1080&h=1920&fit=crop&crop=center", "sunset_clouds"),
    # Mountains
    ("https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1080&h=1920&fit=crop&crop=center", "snowy_peaks"),
    ("https://images.unsplash.com/photo-1486870591958-9b9d0d1dda99?w=1080&h=1920&fit=crop&crop=center", "mountain_range"),
    ("https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1080&h=1920&fit=crop&crop=center", "milky_way_mountain"),
    ("https://images.unsplash.com/photo-1434394354979-a235cd36269d?w=1080&h=1920&fit=crop&crop=center", "mountain_lake"),
    ("https://images.unsplash.com/photo-1520962922320-2038eebab146?w=1080&h=1920&fit=crop&crop=center", "fjord"),
    ("https://images.unsplash.com/photo-1483728642387-6c3bdd6c93e5?w=1080&h=1920&fit=crop&crop=center", "alpine_meadow"),
    ("https://images.unsplash.com/photo-1493246507139-91e8fad9978e?w=1080&h=1920&fit=crop&crop=center", "mountain_reflection"),
    ("https://images.unsplash.com/photo-1455156218388-5e61b526818b?w=1080&h=1920&fit=crop&crop=center", "snow_mountain"),
    # Forests and waterfalls
    ("https://images.unsplash.com/photo-1448375240586-882707db888b?w=1080&h=1920&fit=crop&crop=center", "forest_green"),
    ("https://images.unsplash.com/photo-1501854140801-50d01698950b?w=1080&h=1920&fit=crop&crop=center", "green_meadow"),
    ("https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=1080&h=1920&fit=crop&crop=center", "waterfall"),
    ("https://images.unsplash.com/photo-1542273917363-3b1817f69a2d?w=1080&h=1920&fit=crop&crop=center", "forest_light"),
    ("https://images.unsplash.com/photo-1448630360428-65456885c650?w=1080&h=1920&fit=crop&crop=center", "autumn_trees"),
    ("https://images.unsplash.com/photo-1511497584788-876760111969?w=1080&h=1920&fit=crop&crop=center", "forest_path"),
    ("https://images.unsplash.com/photo-1425913397330-cf8af2ff40a1?w=1080&h=1920&fit=crop&crop=center", "misty_forest"),
    # Deserts
    ("https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=1080&h=1920&fit=crop&crop=center", "sahara_dunes"),
    ("https://images.unsplash.com/photo-1518173946687-a4c8892bbd9f?w=1080&h=1920&fit=crop&crop=center", "golden_dunes"),
    ("https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=1080&h=1920&fit=crop&crop=center", "canyon_red"),
    ("https://images.unsplash.com/photo-1547234935-80c7145ec969?w=1080&h=1920&fit=crop&crop=center", "wadi_desert"),
    ("https://images.unsplash.com/photo-1509233725247-49e657c54213?w=1080&h=1920&fit=crop&crop=center", "desert_stars"),
    # Oceans and coasts
    ("https://images.unsplash.com/photo-1505118380757-91f5f5632de0?w=1080&h=1920&fit=crop&crop=center", "turquoise_sea"),
    ("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1080&h=1920&fit=crop&crop=center", "tropical_coast"),
    ("https://images.unsplash.com/photo-1504701954957-2010ec3bcec1?w=1080&h=1920&fit=crop&crop=center", "rocky_coast"),
    ("https://images.unsplash.com/photo-1505459668311-8dfac7952bf0?w=1080&h=1920&fit=crop&crop=center", "ocean_waves"),
    ("https://images.unsplash.com/photo-1439405326854-014607f694d7?w=1080&h=1920&fit=crop&crop=center", "calm_ocean"),
    # Sky and phenomena
    ("https://images.unsplash.com/photo-1534088568595-a066f410bcda?w=1080&h=1920&fit=crop&crop=center", "dramatic_sky"),
    ("https://images.unsplash.com/photo-1504608524841-42584120d693?w=1080&h=1920&fit=crop&crop=center", "golden_clouds"),
    ("https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=1080&h=1920&fit=crop&crop=center", "aurora_borealis"),
    ("https://images.unsplash.com/photo-1470770841072-f978cf4d019e?w=1080&h=1920&fit=crop&crop=center", "misty_lake"),
    ("https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=1080&h=1920&fit=crop&crop=center", "starry_sky"),
    ("https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=1080&h=1920&fit=crop&crop=center", "rainbow_landscape"),
    ("https://images.unsplash.com/photo-1504192010706-dd7f569ee2be?w=1080&h=1920&fit=crop&crop=center", "storm_clouds"),
    # Rivers and lakes
    ("https://images.unsplash.com/photo-1501952476817-5a986dc68ea4?w=1080&h=1920&fit=crop&crop=center", "clear_river"),
    ("https://images.unsplash.com/photo-1455218873509-8fa753426d7a?w=1080&h=1920&fit=crop&crop=center", "alpine_lake"),
    ("https://images.unsplash.com/photo-1503756234508-e32369269ddb?w=1080&h=1920&fit=crop&crop=center", "turquoise_lake"),
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
            "ar":      _load_font(AR, 96),    # légèrement agrandi : plus de place sans le halo mot-à-mot
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

def _ease_inout(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

_HI_GLOW_COLOR   = (255, 215, 80)          # (conservé pour cohérence de palette ailleurs)
_HI_WORD_COLOR   = (255, 245, 180)
_PAST_COLOR      = (160, 160, 180)
_FUTURE_COLOR    = (220, 220, 235)
_SHADOW_OFFSETS  = [(-2,-2),(2,-2),(-2,2),(2,2),(0,4),(1,3),(-1,3)]  # Ombre plus riche
_EN_COLOR        = (240, 240, 255)         # Traduction : blanc légèrement bleuté
_AR_COLOR        = (255, 250, 235)         # Arabe : blanc chaud, légèrement doré

def draw_arabic_text(draw, text, font, cx, y_start, max_w, alpha, line_gap=32):
    """
    Affiche le verset arabe complet, statique (pas de surlignage mot-à-mot) :
    le verset entier est visible pendant toute sa récitation, puis cède la
    place au suivant. Plus simple et 100% fiable — aucune dépendance à un
    alignement mot-à-mot (CDN segments / Whisper) qui pouvait être imprécis.
    """
    words = text.split()
    if not words:
        return 0
    lines   = _wrap_words(words, font, max_w)
    fh      = _line_h(font) + 6
    y       = y_start
    total_h = 0
    for line in lines:
        line_w = sum(_word_w(font, w) for _, w, _ in line) + WORD_GAP * (len(line) - 1)
        x      = cx + line_w // 2
        for k, (_, w, _) in enumerate(line):
            ww = _word_w(font, w)
            x -= ww
            for dx, dy in _SHADOW_OFFSETS:
                draw.text((x + dx, y + dy), w, font=font, fill=(0, 0, 0, min(alpha, 150)))
            draw.text((x, y), w, font=font, fill=(*_AR_COLOR, alpha))
            x -= WORD_GAP
        y       += fh + line_gap
        total_h += fh + line_gap
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
        # 🔧 FIX vignette inversée : la formule précédente, (1 - (r/mr)**1.6),
        # donnait une alpha MAXIMALE au centre (r petit) et quasi nulle aux bords
        # (r proche de mr) — l'inverse du commentaire ci-dessus. On assombrit
        # maintenant bien les bords (r grand → alpha haute) en laissant le centre clair.
        a = int(vs * (r / mr) ** 1.6)
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

def render_frame(base_img, verse, reciter, title, alpha_frac, verse_num, total_verses):
    import re as _re, math as _math
    img = base_img.copy().convert("RGBA")
    ov  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d   = ImageDraw.Draw(ov, "RGBA")
    f   = fonts()
    af  = max(0., min(1., alpha_frac))
    a   = int(255 * af)
    # 🎨 Animation d'entrée/sortie : le bloc de texte "monte" doucement en
    # place pendant le fade-in et "redescend" légèrement pendant le fade-out,
    # au lieu d'un simple fondu statique. Effet subtil (≤18px) pour rester
    # élégant plutôt que voyant.
    dy_anim = int((1 - _ease_inout(af)) * 18)

    # ── Layout ───────────────────────────────────────────────────────────────
    words_ar  = verse["ar"].split()
    lines_ar  = _wrap_words(words_ar, f["ar"], 920)
    fh        = _line_h(f["ar"]) + 6
    ar_est_h  = len(lines_ar) * (fh + 32) + 10
    en_lines  = verse["en"].split("\n")
    en_h      = len(en_lines) * 68
    block_h   = ar_est_h + 30 + 56 + 24 + en_h
    ar_top    = H // 2 - block_h // 2 + 20 + dy_anim
    mid       = H // 2 + dy_anim

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

    # ── 4. Verset arabe — affiché en entier, statique ────────────────────────
    ar_h = draw_arabic_text(
        d, verse["ar"], f["ar"],
        cx=W//2, y_start=ar_top, max_w=920, alpha=a, line_gap=32
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

    # ── 7. Traduction anglaise (fondu légèrement retardé sur l'arabe) ────────
    en_af = max(0., min(1., (af - 0.12) / 0.88))
    a_en  = int(255 * _ease_inout(en_af))
    en_y  = ref_y + 56
    for i, line in enumerate(en_lines):
        lw = f["en"].getbbox(line)[2] - f["en"].getbbox(line)[0]
        lx = W//2 - lw//2
        ly = en_y + i * 68
        # Ombre riche
        for dx, dy in _SHADOW_OFFSETS:
            d.text((lx+dx, ly+dy), line, font=f["en"], fill=(0, 0, 0, min(255, int(a_en*0.55))))
        d.text((lx, ly), line, font=f["en"], fill=(*_EN_COLOR, a_en))

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

def dl_audio(verse, reciter, retries=3):
    """
    Télécharge l'audio d'un verset. Essaie plusieurs miroirs, avec plusieurs
    tentatives par miroir (timeouts/erreurs réseau transitoires inclus).
    🔧 FIX zéro-décalage : on ne laisse plus jamais passer un échec silencieux
    suivi d'une poursuite de la génération — voir _ensure_audio() plus bas qui
    lève une exception explicite si tous les miroirs échouent, pour éviter
    qu'un verset se retrouve avec des frames vidéo mais sans audio
    (ce qui désynchronise tout ce qui suit dans la vidéo).
    """
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
        f"https://verses.quran.com/{qid}/{s}{aa}.mp3",
    ]
    last_err = None
    for url in urls:
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=25) as r:
                    data = r.read()
                if len(data) > 3000:
                    cache.write_bytes(data)
                    print(f"   Audio {cache.name} ({len(data)//1024} KB)")
                    return cache
                last_err = f"réponse trop petite ({len(data)} octets)"
            except Exception as e:
                last_err = str(e)
                time.sleep(0.8 * (attempt + 1))
                continue
    print(f"   ⚠ Audio INDISPONIBLE pour {verse.get('ref', f'{s}:{a}')} — dernière erreur: {last_err}")
    return None

def get_audio_dur(path):
    try:
        r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)], capture_output=True, text=True, timeout=10)
        v = float(r.stdout.strip())
        return v if v > 0 else 4.5
    except:
        return 4.5

def _screen_char_weights(sub_parts):
    """
    Pour une ayah affichée sur plusieurs écrans (ex. Ayat Al-Kursi a→h), répartit
    la durée audio totale entre les écrans proportionnellement à la longueur du
    texte de chacun — un écran avec deux fois plus de mots reste affiché deux
    fois plus longtemps. Beaucoup plus simple et 100% robuste qu'un alignement
    mot-à-mot (segments CDN / Whisper) : aucun appel réseau supplémentaire,
    aucun risque d'alignement raté, un résultat toujours cohérent.
    """
    def char_count(text):
        return max(1, sum(1 for c in text if unicodedata.category(c).startswith("L")))
    return [char_count(v["ar"]) for v in sub_parts]

def select_verses(passage, reciter):
    """v8 : TOUS les versets du passage, affichage verset entier (pas de karaoké
    mot-à-mot). Les sous-parties d'un même verset (même surah+ayah) partagent
    UN seul audio.

    Pour une ayah découpée en plusieurs écrans (ex. Ayat Al-Kursi a→h), la
    durée audio totale de l'ayah est répartie entre ses écrans au prorata de
    la longueur du texte de chacun (_screen_char_weights) — pas besoin de
    timings mot-à-mot précis puisqu'on n'affiche plus le surlignage, juste le
    verset entier pendant sa fenêtre. Beaucoup plus simple et 100% fiable :
    aucun appel réseau supplémentaire pour des segments, aucun risque
    d'alignement raté qui aurait pu faire "sauter" un écran.
    """
    sel, audios, aud_durs, frame_counts = [], [], [], []

    # Regrouper les sous-parties consécutives par ayah réelle (surah, ayah)
    # Ex: Ayat Al-Kursi a→h ont toutes surah=2, ayah=255 → 1 seul audio
    ayah_groups = {}   # (surah, ayah, qid) → liste des sous-parties (dans l'ordre du passage)
    for verse in passage["verses"]:
        key = (verse["surah"], verse["ayah"], reciter["qid"])
        ayah_groups.setdefault(key, []).append(verse)

    ayah_audio_cache    = {}  # (s,a,qid) → (audio_path, ad, weights, total_weight)
    ayah_weight_before  = {}  # (s,a,qid) → somme des poids déjà consommés par les sous-parties précédentes
    ayah_subpart_idx    = {}  # (s,a,qid) → index de la prochaine sous-partie dans ayah_groups[key]
    ayah_frames_emitted = {}  # (s,a,qid) → nb de frames déjà émises (arrondi cumulatif)

    for verse in passage["verses"]:
        key = (verse["surah"], verse["ayah"], reciter["qid"])
        ref = verse.get("ref") or f"{verse['surah']}:{verse['ayah']}"

        if key not in ayah_audio_cache:
            # Première sous-partie de cette ayah : télécharger l'audio
            audio = dl_audio(verse, reciter)
            # 🔧 FIX zéro-décalage / passage complet : si l'audio est introuvable,
            # on ABANDONNE ce passage avec ce récitateur plutôt que de générer
            # des frames vidéo pour un verset sans son (ce qui faisait "sauter"
            # le verset à l'écoute et décalait tous les versets suivants).
            if not audio:
                raise AudioMissingError(
                    f"Audio introuvable pour {ref} avec le récitateur "
                    f"{reciter.get('name', '?')} — passage abandonné pour garantir 0 décalage."
                )
            ad      = get_audio_dur(audio) if audio else 4.5
            weights = _screen_char_weights(ayah_groups[key])
            ayah_audio_cache[key]   = (audio, ad, weights, sum(weights))
            ayah_weight_before[key] = 0
            ayah_subpart_idx[key]   = 0
            print(f"      {verse['surah']}:{verse['ayah']} ({round(ad,1)}s) [audio téléchargé — {len(weights)} écran(s)]")
        else:
            print(f"      {verse['ref']} [même audio {verse['surah']}:{verse['ayah']}]")

        audio, ad, weights, total_weight = ayah_audio_cache[key]
        idx  = ayah_subpart_idx[key]
        w    = weights[idx]
        is_last_subpart = (idx == len(weights) - 1)

        # ── Fenêtre temporelle de cette sous-partie dans l'audio complet ──────
        w_before     = ayah_weight_before[key]
        window_start = ad * (w_before / total_weight) if total_weight > 0 else 0.0
        window_end   = ad if is_last_subpart else ad * ((w_before + w) / total_weight)
        window_start = max(0.0, min(window_start, ad))
        window_end   = max(window_start + 0.05, min(window_end, ad))
        window_dur   = window_end - window_start

        ayah_weight_before[key] = w_before + w
        ayah_subpart_idx[key]   = idx + 1

        # 🔧 Zéro dérive : le nombre de frames de CHAQUE écran est calculé par
        # arrondi CUMULATIF (façon Bresenham) sur la durée réelle de l'audio
        # complet de l'ayah, pas par troncature indépendante de chaque fenêtre —
        # garantit que les écrans d'une même ayah s'emboîtent exactement
        # (zéro trou, zéro recouvrement de frames).
        total_frames_full_ayah = int(round(ad * FPS))
        cum_before = ayah_frames_emitted.get(key, 0)
        if is_last_subpart:
            cum_after = total_frames_full_ayah  # garantit la somme exacte, pas d'arrondi résiduel
        else:
            cum_after = int(round(window_end / ad * total_frames_full_ayah)) if ad > 0 else cum_before
            cum_after = max(cum_after, cum_before + 1)
        n_audio_frames = max(1, cum_after - cum_before)
        ayah_frames_emitted[key] = cum_after

        sel.append(verse)
        audios.append(audio)
        aud_durs.append(window_dur)
        frame_counts.append(n_audio_frames)

    # Audio mixé : dédoublonner les fichiers audio (même ayah = même fichier complet)
    seen_audio = []
    seen_keys  = set()
    for verse in sel:
        key = (verse["surah"], verse["ayah"], reciter["qid"])
        if key not in seen_keys:
            audio, ad, _, _ = ayah_audio_cache[key]
            seen_audio.append((audio, ad))
            seen_keys.add(key)

    unique_audios = [a for a, _ in seen_audio]
    unique_durs   = [d for _, d in seen_audio]

    total_dur = sum(unique_durs) + BREATH * max(0, len(unique_audios) - 1)
    audio_dur = sum(unique_durs)
    print(f"   Total : {len(sel)} écrans — {len(unique_audios)} ayat audio — {audio_dur:.1f}s audio — {total_dur:.1f}s vidéo")
    return sel, audios, aud_durs, total_dur, audio_dur, unique_audios, unique_durs, frame_counts

def mix_audio(audio_list, dur_list, total_dur):
    """
    Concatène les fichiers audio avec un court silence BREATH entre chaque verset.
    Cela préserve le silence naturel entre les ayat, sans jamais couper la récitation.

    IMPORTANT : audio_list contient déjà les audios DÉDOUBLONNÉS (un seul par ayah).
    On insère donc un silence entre chaque ayah — ce qui correspond exactement
    aux transitions breath visuelles entre ayat différentes.
    """
    # 🔧 FIX "verset sauté" / vidéo muette : auparavant, tout audio manquant
    # ici était silencieusement filtré (`valid = [... if a and Path(a).exists()]`),
    # alors que les frames vidéo de CE verset avaient déjà été rendues avec le
    # nombre de frames prévu. Résultat possible : piste audio plus courte que
    # la piste vidéo → tous les versets suivants désynchronisés (karaoké qui
    # "saute"), ou pire, si TOUS les audios manquaient, la fonction renvoyait
    # None et generate() encodait quand même une vidéo... sans aucun son, et
    # la déclarait "✅ OK". On échoue maintenant bruyamment (exception) pour
    # que le run global retente avec un autre récitateur/passage plutôt que
    # de livrer une vidéo cassée.
    missing = [a for a in audio_list if not a or not Path(a).exists()]
    if missing:
        raise AudioMissingError(
            f"mix_audio: {len(missing)} fichier(s) audio manquant(s) au moment du mixage "
            f"alors qu'ils étaient attendus (incohérence cache) — passage abandonné pour "
            f"éviter une vidéo désynchronisée ou muette."
        )
    valid = list(zip(audio_list, dur_list))
    if not valid:
        raise AudioMissingError("mix_audio: aucun audio à mixer.")
    # Générer un fichier silence .aac de BREATH secondes
    silence_path = OUT_DIR / "cache" / "silence_breath.aac"
    if not silence_path.exists():
        # 🔧 FIX : durée du silence = BREATH_DUR (verrouillée sur breath_frames vidéo),
        # pas BREATH brut — garantit zéro dérive audio/vidéo sur les transitions.
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"anullsrc=r=44100:cl=stereo",
            "-t", str(BREATH_DUR), "-c:a", "aac", "-b:a", "192k", str(silence_path)
        ], capture_output=True)
    inputs, concat_parts, idx = [], [], 0
    for vi, (audio, _) in enumerate(valid):
        inputs += ["-i", str(audio)]
        concat_parts.append(f"[{idx}:a]")
        idx += 1
        # Silence UNIQUEMENT entre deux ayat successives (pas après la dernière)
        if vi < len(valid) - 1 and silence_path.exists():
            inputs += ["-i", str(silence_path)]
            concat_parts.append(f"[{idx}:a]")
            idx += 1
    n   = len(concat_parts)
    flt = "".join(concat_parts) + f"concat=n={n}:v=0:a=1[aout]"
    out = OUT_DIR / "cache" / "audio_mixed.aac"
    r = subprocess.run(
        ["ffmpeg", "-y"] + inputs + ["-filter_complex", flt, "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", str(out)],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"Mix audio erreur: {r.stderr[-300:]}")
        return None
    return out

def encode(frames_dir, audio_path, total_dur, out_path):
    cmd = ["ffmpeg","-y","-framerate",str(FPS),"-start_number","0","-i",str(frames_dir/"frame_%06d.jpg")]
    if audio_path and Path(audio_path).exists():
        cmd += ["-i",str(audio_path),"-c:v","libx264","-preset","fast","-crf","18","-c:a","aac","-b:a","192k","-t",str(total_dur),"-shortest"]
    else:
        cmd += ["-c:v","libx264","-preset","fast","-crf","18","-t",str(total_dur)]
    cmd += ["-pix_fmt","yuv420p","-movflags","+faststart",str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"ffmpeg erreur: {r.stderr[-400:]}")
        return False
    return True

def _select_passage_and_reciter(passage):
    """Essaie tous les récitateurs sur CE passage. Retourne soit le tuple complet
    de select_verses() + le récitateur retenu, soit None si aucun récitateur
    ne fournit un audio complet pour ce passage."""
    shuffled = RECITERS.copy()
    RNG.shuffle(shuffled)

    print("Passage: " + passage["title"])

    for cand in shuffled:
        try:
            print("→ Tentative avec " + cand["name"] + " " + cand["flag"])
            result = select_verses(passage, cand)
            verses = result[0]
            if not verses:
                continue
            return result + (cand,)
        except AudioMissingError as e:
            print(f"   ⚠ {e}")
            continue
        except Exception as e:
            # 🔧 Filet de sécurité : toute erreur réseau imprévue (timeout SSL,
            # connexion réinitialisée, DNS, etc.) ne doit JAMAIS faire planter
            # tout le process — on l'enregistre comme un échec de CE récitateur
            # sur CE passage et on passe au suivant, comme pour un audio manquant.
            print(f"   ⚠ Erreur inattendue avec {cand['name']} ({type(e).__name__}: {e}) — récitateur écarté pour ce passage")
            continue
    print(f"   ❌ Aucun récitateur n'a pu fournir l'audio complet pour « {passage['title']} »")
    return None

# 🔧 FIX "1 vidéo garantie par jour" : si le passage tiré au hasard échoue avec
# TOUS les récitateurs (audio manquant ou karaoké imprécis partout), on ne
# renonce plus — on essaie le passage suivant, et ainsi de suite, jusqu'à en
# trouver un qui marche parfaitement. On parcourt les 200 passages dans un
# ordre mélangé (donc pas toujours le même ordre de repli), et si même ÇA
# échoue (tous les passages × tous les récitateurs), on reboucle depuis le
# début après une courte pause — utile si l'échec vient d'un souci réseau
# transitoire qui se résorbe en quelques secondes/minutes.
# Pas de petite limite arbitraire (genre 10 essais) : ça tourne jusqu'au
# succès. Une seule soupape de sécurité — MAX_GENERATE_ATTEMPTS — existe pour
# éviter qu'un run en boucle infinie ne tourne éternellement si la machine
# n'a PLUS DU TOUT accès réseau (sinon ça boucle pour rien indéfiniment) ;
# elle est réglée très haut par défaut, donc sans incidence en usage normal.
MAX_GENERATE_ATTEMPTS = int(os.getenv("MAX_GENERATE_ATTEMPTS", "100000"))
RETRY_PAUSE_S         = float(os.getenv("RETRY_PAUSE_S", "5"))

def generate(passage_idx=None):
    if passage_idx is not None:
        # Appel ciblé sur un passage précis (ex: tests manuels) : on essaie
        # uniquement celui-là, comportement inchangé par rapport à avant.
        passage = PASSAGES[passage_idx % len(PASSAGES)]
        picked = _select_passage_and_reciter(passage)
        if picked is None:
            return None
        verses, audios, aud_durs, total_dur, audio_dur, unique_audios, unique_durs, frame_counts, reciter = picked
        order = list(range(len(PASSAGES)))
        attempt = 0
        picked = None
        passage = None
        while picked is None:
            RNG.shuffle(order)
            for idx in order:
                attempt += 1
                if attempt > MAX_GENERATE_ATTEMPTS:
                    print(f"❌ Limite de sécurité atteinte ({MAX_GENERATE_ATTEMPTS} tentatives) — abandon. "
                          f"Vérifie la connexion réseau / la disponibilité des CDN audio.")
                    return None
                passage = PASSAGES[idx]
                try:
                    picked = _select_passage_and_reciter(passage)
                except Exception as e:
                    # Même logique : une erreur imprévue sur CE passage ne doit
                    # jamais arrêter la boucle globale — on note et on continue.
                    print(f"   ⚠ Erreur inattendue sur « {passage['title']} » ({type(e).__name__}: {e}) — passage suivant")
                    picked = None
                if picked is not None:
                    break
            if picked is None:
                print(f"   🔁 Aucun des {len(PASSAGES)} passages n'a abouti à ce tour — "
                      f"nouvelle passe dans {RETRY_PAUSE_S:.0f}s (tentative cumulée: {attempt})...")
                time.sleep(RETRY_PAUSE_S)
        verses, audios, aud_durs, total_dur, audio_dur, unique_audios, unique_durs, frame_counts, reciter = picked

    n = len(verses)
    if n == 0:
        print("❌ Aucun verset disponible")
        return None
    p      = make_params(n)
    scenes = [get_scene(i, p) for i in range(n)]
    fd = OUT_DIR / "frames"
    for f in fd.glob("*.jpg"):
        f.unlink()
    xf           = p["xf"]
    gi           = 0
    # v7 : frames audio + frames breath (silence visuel) entre versets
    # 🔧 FIX : BREATH_FRAMES (constante globale) au lieu de int(BREATH*FPS) recalculé ici —
    # garantit que ce nombre est identique à celui utilisé pour générer le silence audio
    # dans mix_audio(), donc zéro dérive entre les flux audio et vidéo.
    breath_frames = BREATH_FRAMES
    # n_breaths = nombre de transitions réelles entre ayat DIFFÉRENTES dans la séquence de versets
    # C'est aussi le nombre de silences audio insérés par mix_audio (len(unique_audios) - 1)
    # Les deux DOIVENT être identiques pour éviter tout désalignement audio/vidéo.
    n_breaths = len(unique_audios) - 1  # ← aligné sur mix_audio
    total_frames  = sum(frame_counts) + breath_frames * n_breaths
    total_dur     = total_frames / FPS   # 🔧 durée vidéo recalculée EXACTEMENT depuis le nombre de frames réel (plus de dérive cumulative entre durée déclarée et frames produites)
    print(f"Rendu {total_frames} frames ({total_dur:.1f}s) — {n_breaths} transitions breath...")
    for vi in range(n):
        verse   = verses[vi]
        aud_dur_v = aud_durs[vi]
        sc_img, _ = scenes[vi]
        kb      = p["kb"][vi]
        n_audio_frames = frame_counts[vi]
        # Frames pendant la récitation (son actif)
        fade_in  = max(1, int(FPS * 0.55))
        fade_out = max(1, int(FPS * 0.45))
        next_sc  = scenes[vi+1][0] if vi < n-1 else None
        next_kb  = p["kb"][vi+1]   if vi < n-1 else None
        n_words  = len(verse["ar"].split())
        print("Verset " + str(vi+1) + "/" + str(n) + " — " + verse["ref"] + " — " + str(n_words) + " mots")
        # ── Frames audio du verset ──────────────────────────────────────────
        # TRANSITION PROPRE (fix bug glitch) :
        # - Pendant l'audio : image STABLE (ken-burns), texte visible
        # - Fade-out texte sur les dernières fade_out frames (image toujours stable)
        # - Pendant BREATH : image crossfade A→B, texte INVISIBLE (alpha=0)
        # - Au verset suivant : fade-in texte sur les premières fade_in frames
        for fi in range(n_audio_frames):
            t_seg = fi / max(1, n_audio_frames)
            # Image stable pendant tout le verset (pas de crossfade pendant l'audio)
            frame = ken_burns(sc_img, t_seg, **kb)
            # Alpha texte : fade-in en début, fade-out en fin
            if fi < fade_in:
                ta = fi / fade_in
            elif fi > n_audio_frames - fade_out:
                ta = (n_audio_frames - fi) / max(1, fade_out)
            else:
                ta = 1.0
            frame = render_frame(frame, verse, reciter, passage["title"], max(0., ta), vi+1, n)
            frame.save(str(fd / f"frame_{gi:06d}.jpg"), "JPEG", quality=92)
            gi += 1
        # ── Frames BREATH : crossfade IMAGE seulement, texte invisible ────────
        # Uniquement entre ayat DIFFÉRENTES (pas entre sous-parties du même verset)
        next_is_new_ayah = (vi < n - 1 and
            (verses[vi+1]["surah"] != verse["surah"] or
             verses[vi+1]["ayah"]  != verse["ayah"]))
        if vi < n - 1 and next_is_new_ayah:
            for bi in range(breath_frames):
                t_b = bi / max(1, breath_frames - 1)
                # Crossfade progressif image A → image B (easing smooth)
                t_ease = _ease_inout(t_b)
                frame_a = ken_burns(sc_img, 1.0, **kb)
                frame_b = ken_burns(next_sc, 0., **next_kb)
                frame   = Image.blend(frame_a, frame_b, t_ease)
                # Texte INVISIBLE pendant le crossfade (alpha=0) → plus de glitch
                frame = render_frame(frame, verse, reciter, passage["title"], 0.0, vi+1, n)
                frame.save(str(fd / f"frame_{gi:06d}.jpg"), "JPEG", quality=92)
                gi += 1
        print(f"  Verset {vi+1} OK")
    print(f"{gi} frames rendues")
    audio_track = mix_audio(unique_audios, unique_durs, audio_dur)
    if not audio_track or not Path(audio_track).exists():
        # 🔧 FIX vidéo muette : ne jamais encoder sans piste audio valide.
        raise AudioMissingError("Piste audio mixée introuvable après mix_audio() — abandon plutôt que vidéo muette.")
    today = datetime.date.today().strftime("%Y%m%d")
    out   = OUT_DIR / f"quran_{today}_s{RUN_SEED%99999:05d}.mp4"
    print(f"Encodage...")
    ok = encode(fd, audio_track, total_dur, out)
    for f in fd.glob("*.jpg"):
        f.unlink()
    if ok and out.exists():
        mb = out.stat().st_size / 1024 / 1024
        print(f"✅ OK: {out.name} ({mb:.1f} MB — {total_dur:.1f}s — {n} versets)")
        # 🔧 Métadonnées pour daily_upload.py : le thème du passage (déjà en
        # anglais dans PASSAGES, ex. "Patience and Hope") sert de titre au short.
        # Écrit en .json à côté de la vidéo (même nom de base) ET dans un
        # fichier "last_meta.json" générique pour un accès simple sans avoir
        # à connaître le nom exact du fichier vidéo généré.
        ref_first = verses[0]["ref"]
        ref_last  = verses[-1]["ref"]
        meta = {
            "title": passage["title"],            # ex: "Patience and Hope"
            "video_path": str(out),
            "surah_range": f"{ref_first} - {ref_last}",
            "reciter": reciter["name"],
            "n_verses": n,
            "duration_s": round(total_dur, 1),
            "generated_at": datetime.datetime.now().isoformat(),
        }
        try:
            (out.with_suffix(".json")).write_text(json.dumps(meta, ensure_ascii=False, indent=2))
            (OUT_DIR / "last_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"   ⚠ Écriture des métadonnées échouée (non bloquant) : {e}")
        return out
    else:
        print("❌ Erreur encodage")
        return None

# ══════════════════════════════════════════════════════════════════════════
# Tout est prêt — la génération démarre ci-dessous (bloc Drive)
# ══════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════
# POINT D'ENTRÉE — appelé par daily_upload.py
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    import datetime, glob
    print(f'🎲 Seed : {RUN_SEED} — {len(PASSAGES)} passages — {len(RECITERS)} récitateurs')

    # 🔧 Dernier filet de sécurité : même après avoir choisi un passage et un
    # récitateur, le rendu des frames ou l'encodage ffmpeg peuvent échouer sur
    # un incident réseau/disque transitoire (ex: timeout SSL pendant un
    # téléchargement d'image de fond). Plutôt que de planter tout le run avec
    # exit code 1, on relance generate() depuis zéro (nouveau passage tiré)
    # jusqu'à obtenir une vidéo, avec la même soupape MAX_GENERATE_ATTEMPTS.
    video = None
    top_attempt = 0
    while video is None:
        top_attempt += 1
        if top_attempt > MAX_GENERATE_ATTEMPTS:
            print(f"❌ Limite de sécurité atteinte ({MAX_GENERATE_ATTEMPTS} tentatives globales) — abandon.")
            video = None
            break
        try:
            video = generate()
        except Exception as e:
            print(f"   ⚠ Erreur inattendue pendant la génération ({type(e).__name__}: {e}) — nouvelle tentative dans {RETRY_PAUSE_S:.0f}s...")
            video = None
        if video is None:
            time.sleep(RETRY_PAUSE_S)

    if video and Path(video).exists():
        src_path = str(video)
        yt = src_path.replace('.mp4', '_youtube.mp4')
        subprocess.run([
            'ffmpeg', '-y', '-i', src_path,
            '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.0',
            '-preset', 'fast', '-crf', '18', '-vf', 'scale=1080:1920',
            '-r', '30', '-c:a', 'aac', '-b:a', '192k', '-ar', '44100',
            '-movflags', '+faststart', '-pix_fmt', 'yuv420p', yt
        ])
        print(f'✅ Vidéo YouTube prête : {yt}')
        sys.exit(0)
    else:
        print('❌ Génération échouée')
        sys.exit(1)
