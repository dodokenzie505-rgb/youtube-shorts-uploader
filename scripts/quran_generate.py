"""
Script de génération de vidéos Quran Daily Reel — Version Propre & Fluide.
- Zéro coupure audio (enchaînement naturel des versets sans silence artificiel)
- Suppression du karaoké mot-à-mot (plus léger, 100% fiable)
- Polices coraniques élégantes et lisibles
- Transitions douces synchronisées avec la récitation
"""

import subprocess, sys, os, math, datetime, json, random, time, hashlib, unicodedata, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import urllib.request

# ═══════════════════════════════════════════════════════════════════════════
# 0. VÉRIFICATION ET INSTALLATION DES DÉPENDANCES
# ═══════════════════════════════════════════════════════════════════════════
def _ensure_installed():
    if not shutil.which("ffmpeg"):
        subprocess.run(["sudo", "apt-get", "install", "-y", "-q", "ffmpeg"], check=True)
    
    # Installation de polices coraniques élégantes (Amiri & Scheherazade)
    for pkg in ["fonts-hosny-amiri", "fonts-sil-scheherazade"]:
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y", "-q", pkg], check=True, timeout=60)
        except Exception:
            pass # Repli silencieux sur les polices disponibles
    try:
        import PIL
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"], check=True)

_ensure_installed()

print("\n🚀 Démarrage de la génération (Mode Fluide & Épuré)...\n")

W, H      = 1080, 1920
FPS       = 24
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
    pass

# ═══════════════════════════════════════════════════════════════════════════
# 1. BASE DE DONNÉES DES PASSAGES (Échantillon curaté + API)
# ═══════════════════════════════════════════════════════════════════════════
CURATED_PASSAGES = [
    {"title": "Al-Fatiha — The Opening", "verses": [
        {"ar": "بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيمِ",   "en": "In the name of Allah, the Most Gracious, the Most Merciful.",  "ref": "1:1",  "surah": 1,  "ayah": 1},
        {"ar": "الْحَمْدُ لِلّٰهِ رَبِّ الْعَالَمِينَ",    "en": "All praise is due to Allah, Lord of all the worlds.",            "ref": "1:2",  "surah": 1,  "ayah": 2},
        {"ar": "الرَّحْمٰنِ الرَّحِيمِ",                   "en": "The Most Gracious, the Most Merciful.",                         "ref": "1:3",  "surah": 1,  "ayah": 3},
        {"ar": "مَالِكِ يَوْمِ الدِّينِ",                  "en": "Master of the Day of Judgment.",                                 "ref": "1:4",  "surah": 1,  "ayah": 4},
        {"ar": "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ", "en": "It is You we worship and You we ask for help.",                "ref": "1:5",  "surah": 1,  "ayah": 5},
        {"ar": "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ",       "en": "Guide us to the straight path.",                                 "ref": "1:6",  "surah": 1,  "ayah": 6},
        {"ar": "صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ", "en": "The path of those You have blessed, not those who have earned anger nor those who are astray.", "ref": "1:7", "surah": 1, "ayah": 7},
    ]},
    {"title": "Patience and Hope", "verses": [
        {"ar": "أَلَمْ نَشْرَحْ لَكَ صَدْرَكَ",             "en": "Did We not expand for you your chest?",                         "ref": "94:1", "surah": 94, "ayah": 1},
        {"ar": "وَوَضَعْنَا عَنكَ وِزْرَكَ",               "en": "And removed from you your burden?",                              "ref": "94:2", "surah": 94, "ayah": 2},
        {"ar": "الَّذِي أَنقَضَ ظَهْرَكَ",                 "en": "Which had weighed heavily upon your back?",                      "ref": "94:3", "surah": 94, "ayah": 3},
        {"ar": "وَرَفَعْنَا لَكَ ذِكْرَكَ",                "en": "And raised high your repute?",                                    "ref": "94:4", "surah": 94, "ayah": 4},
        {"ar": "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا",           "en": "For indeed, with hardship will be ease.",                        "ref": "94:5", "surah": 94, "ayah": 5},
        {"ar": "إِنَّ مَعَ الْعُسْرِ يُسْرًا",             "en": "Indeed, with hardship will be ease.",                            "ref": "94:6", "surah": 94, "ayah": 6},
    ]},
    {"title": "Trust in Allah", "verses": [
        {"ar": "وَمَن يَتَّقِ اللّٰهَ يَجْعَل لَّهُ مَخْرَجًا", "en": "And whoever fears Allah, He will make for him a way out.", "ref": "65:2", "surah": 65, "ayah": 2},
        {"ar": "وَيَرْزُقْهُ مِنْ حَيْثُ لَا يَحْتَسِبُ",       "en": "And will provide for him from where he does not expect.",  "ref": "65:3", "surah": 65, "ayah": 3},
        {"ar": "وَمَن يَتَوَكَّلْ عَلَى اللّٰهِ فَهُوَ حَسْبُهُ", "en": "Whoever relies upon Allah — He is sufficient for him.", "ref": "65:3b","surah": 65, "ayah": 3},
    ]},
    {"title": "Ayat Al-Kursi — The Throne Verse", "verses": [
        {"ar": "اللّٰهُ لَا إِلٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ", "en": "Allah — there is no deity except Him, the Ever-Living, the Sustainer.", "ref": "2:255a", "surah": 2, "ayah": 255},
        {"ar": "لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ",       "en": "Neither drowsiness overtakes Him nor sleep.",                     "ref": "2:255b", "surah": 2, "ayah": 255},
        {"ar": "لَّهُ مَا فِي السَّمٰوَاتِ وَمَا فِي الْأَرْضِ", "en": "To Him belongs whatever is in the heavens and earth.",       "ref": "2:255c", "surah": 2, "ayah": 255},
        {"ar": "مَن ذَا الَّذِي يَشْفَعُ عِندَهُ إِلَّا بِإِذْنِهِ", "en": "Who is it that can intercede with Him except by His permission?", "ref": "2:255d", "surah": 2, "ayah": 255},
    ]}
]

# (L'extension automatique via l'API Quran.com est conservée pour avoir 200+ thèmes)
TARGET_PASSAGE_CNT = 200
PASSAGES_CACHE_FILE = OUT_DIR / "cache" / "passages_api.json"

def _fetch_api_passages():
    if PASSAGES_CACHE_FILE.exists():
        try:
            return json.loads(PASSAGES_CACHE_FILE.read_text()).get("passages", [])
        except:
            pass
    try:
        url = "https://api.quran.com/api/v4/chapters?language=en"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            chapters = json.loads(r.read()).get("chapters", [])
        extra = []
        for ch in chapters[:25]: # Échantillon rapide
            cid = ch["id"]
            if cid in [1, 94, 65]: continue
            v_url = f"https://api.quran.com/api/v4/verses/by_chapter/{cid}?language=en&fields=text_uthmani&translations=131&per_page=6"
            v_req = urllib.request.Request(v_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(v_req, timeout=10) as vr:
                v_data = json.loads(vr.read()).get("verses", [])
            if not v_data: continue
            verses_out = []
            for v in v_data:
                ar = v.get("text_uthmani", "").strip()
                en = v.get("translations", [{}])[0].get("text", "").replace("<sup ", "").strip()
                if ar and en:
                    verses_out.append({"ar": ar, "en": en, "ref": f"{cid}:{v['verse_number']}", "surah": cid, "ayah": v['verse_number']})
            if verses_out:
                extra.append({"title": f"{ch['translated_name']['name']} — Surah {cid}", "verses": verses_out})
        PASSAGES_CACHE_FILE.write_text(json.dumps({"passages": extra}, ensure_ascii=False))
        return extra
    except Exception:
        return []

PASSAGES = CURATED_PASSAGES + _fetch_api_passages()
print(f"   📚 {len(PASSAGES)} passages disponibles au total.")

# ═══════════════════════════════════════════════════════════════════════════
# 2. RÉCITATEURS & PHOTOS DE FOND
# ═══════════════════════════════════════════════════════════════════════════
RECITERS = [
    {"name": "Mishary Rashid Alafasy",       "qid": 1,   "ev": "Alafasy_128kbps",              "flag": "🇰🇼"},
    {"name": "Abdul Rahman Al-Sudais",       "qid": 2,   "ev": "AbdulSamad_128kbps",           "flag": "🇸🇦"},
    {"name": "Saad Al-Ghamdi",               "qid": 3,   "ev": "Saad_Al-Ghamdi_128kbps",       "flag": "🇸🇦"},
    {"name": "Maher Al-Muaiqly",             "qid": 10,  "ev": "MaherAlMuaiqly128kbps",        "flag": "🇸🇦"},
    {"name": "Hani Ar-Rifai",                "qid": 5,   "ev": "Hani_Rifai_128kbps",           "flag": "🇸🇦"},
    {"name": "Nasser Al-Qatami",             "qid": 43,  "ev": "Nasser_Alqatami_128kbps",      "flag": "🇸🇦"},
    {"name": "Yasser Al-Dosari",             "qid": 135, "ev": "Yasser_Ad-Dussary_128kbps",    "flag": "🇸🇦"},
    {"name": "Abdul Basit Abdul Samad",      "qid": 16,  "ev": "Abdul_Basit_Murattal_192kbps", "flag": "🇪🇬"},
    {"name": "Mahmoud Khalil Al-Husary",     "qid": 17,  "ev": "Husary_128kbps",               "flag": "🇪🇬"},
]

PHOTOS = [
    ("https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?w=1080&h=1920&fit=crop&crop=center", "sunset_orange"),
    ("https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1080&h=1920&fit=crop&crop=center", "golden_mountain"),
    ("https://images.unsplash.com/photo-1518021964703-4b2030f03085?w=1080&h=1920&fit=crop&crop=center", "sunset_clouds"),
    ("https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1080&h=1920&fit=crop&crop=center", "snowy_peaks"),
    ("https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1080&h=1920&fit=crop&crop=center", "milky_way"),
    ("https://images.unsplash.com/photo-1448375240586-882707db888b?w=1080&h=1920&fit=crop&crop=center", "forest_green"),
    ("https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=1080&h=1920&fit=crop&crop=center", "sahara_dunes"),
    ("https://images.unsplash.com/photo-1505118380757-91f5f5632de0?w=1080&h=1920&fit=crop&crop=center", "turquoise_sea"),
    ("https://images.unsplash.com/photo-1534088568595-a066f410bcda?w=1080&h=1920&fit=crop&crop=center", "dramatic_sky"),
    ("https://images.unsplash.com/photo-1508739773434-c26b3d09e071?w=1080&h=1920&fit=crop&crop=center", "aurora_borealis"),
]

# ═══════════════════════════════════════════════════════════════════════════
# 3. TYPOGRAPHIE ET RENDU TEXTE PROPRE
# ═══════════════════════════════════════════════════════════════════════════
def _load_font(paths, size):
    for p in paths:
        try: return ImageFont.truetype(p, size)
        except: pass
    return ImageFont.load_default()

_FONTS_CACHE = None
def fonts():
    global _FONTS_CACHE
    if _FONTS_CACHE is None:
        AR = [
            "/usr/share/fonts/truetype/sil-scheherazade/ScheherazadeNew-Bold.ttf",
            "/usr/share/fonts/truetype/sil-scheherazade/ScheherazadeNew-Regular.ttf",
            "/usr/share/fonts/truetype/fonts-hosny-amiri/Amiri-Regular.ttf",
            "/usr/share/fonts/opentype/fonts-hosny-amiri/Amiri-Regular.ttf",
        ]
        IT = ["/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"]
        RG = ["/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"]
        _FONTS_CACHE = {
            "ar":    _load_font(AR, 92),   # Arabe bien dimensionné et soigné
            "en":    _load_font(IT, 52),   # Anglais en italique élégant
            "ref":   _load_font(RG, 40),   # Référence discrète
            "small": _load_font(RG, 30),   # Crédits
            "title": _load_font(IT, 44),   # Titre du thème
        }
    return _FONTS_CACHE

WORD_GAP = 18
def _word_w(font, word): return font.getbbox(word)[2] - font.getbbox(word)[0]
def _line_h(font): return font.getbbox("ابجد")[3] - font.getbbox("ابجد")[1]

def _wrap_words(words, font, max_w):
    lines, cur, cur_w = [], [], 0
    for i, w in enumerate(words):
        ww = _word_w(font, w)
        if cur and cur_w + WORD_GAP + ww > max_w:
            lines.append(cur); cur, cur_w = [(i, w, ww)], ww
        else:
            cur.append((i, w, ww))
            cur_w = (cur_w + WORD_GAP + ww) if len(cur) > 1 else ww
    if cur: lines.append(cur)
    return lines

def _ease_inout(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def draw_arabic_text_clean(draw, text, font, cx, y_start, max_w, alpha, line_gap=32):
    """
    Affiche le verset arabe avec une élégance absolue :
    - Surlignage karaoké SUPPRIMÉ pour un visuel solennel et pur.
    - Teinte blanc chaud dorée (#FFFAEB) et ombrage doux.
    """
    words = text.split()
    if not words: return 0
    lines = _wrap_words(words, font, max_w)
    fh = _line_h(font) + 8
    y, total_h = y_start, 0
    
    for line in lines:
        line_w = sum(_word_w(font, w) for _, w, _ in line) + WORD_GAP * (len(line) - 1)
        x = cx + line_w // 2
        for _, w, ww in line:
            x -= ww
            # Ombre portée douce pour une parfaite lisibilité
            for dx, dy in [(-2,-2), (2,-2), (-2,2), (2,2), (0,3), (1,3)]:
                draw.text((x + dx, y + dy), w, font=font, fill=(0, 0, 0, int(alpha * 0.65)))
            # Texte principal en blanc chaud
            draw.text((x, y), w, font=font, fill=(255, 250, 235, alpha))
            x -= WORD_GAP
        y += fh + line_gap
        total_h += fh + line_gap
    return total_h

# ═══════════════════════════════════════════════════════════════════════════
# 4. GESTION DU FOND VISUEL (KEN BURNS & CINÉMATIQUE)
# ═══════════════════════════════════════════════════════════════════════════
def dl_image(url, path):
    if path.exists(): return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r: path.write_bytes(r.read())
        return True
    except Exception: return False

def cinematic(img, p):
    img = ImageEnhance.Contrast(img).enhance(p["contrast"])
    img = ImageEnhance.Color(img).enhance(p["color_sat"])
    img = ImageEnhance.Brightness(img).enhance(p["brightness"])
    # Vignette douce autour de l'image
    vign = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vign)
    cx, cy, mr = W // 2, H // 2, int(math.sqrt((W//2)**2 + (H//2)**2))
    vs = int(p["vign"])
    for r in range(mr, 0, -8):
        a = int(vs * (r / mr) ** 1.7)
        vd.ellipse([cx-r, cy-r, cx+r, cy+r], fill=max(0, a))
    result = Image.composite(Image.new("RGB", (W, H), 0), img, vign)
    return ImageEnhance.Brightness(result).enhance(1.10)

def get_scene(idx, p):
    real = p["photo_indices"][idx % len(p["photo_indices"])]
    url, _ = PHOTOS[real]
    cache = OUT_DIR / "cache" / f"photo_{real:03d}.jpg"
    if dl_image(url, cache):
        try: return cinematic(Image.open(str(cache)).convert("RGB").resize((W, H), Image.LANCZOS), p)
        except: pass
    img = Image.new("RGB", (W, H), (20, 15, 35))
    return cinematic(img, p)

def ken_burns(img, t, zoom_end=1.06, pan_x=0., pan_y=0.):
    w, h = img.size
    zoom = 1. + (zoom_end - 1.) * t
    nw, nh = int(w / zoom), int(h / zoom)
    cx = int(w // 2 + pan_x * w * (1 - t))
    cy = int(h // 2 + pan_y * h * (1 - t))
    l, t2 = max(0, cx - nw // 2), max(0, cy - nh // 2)
    return img.crop((l, t2, min(w, l+nw), min(h, t2+nh))).resize((w, h), Image.LANCZOS)

def make_params(n):
    kb = []
    for _ in range(n):
        dx, dy = RNG.choice([(1,0),(-1,0),(0,1),(0,-1)])
        kb.append({"zoom_end": RNG.uniform(1.04, 1.08), "pan_x": dx*RNG.uniform(0.01, 0.02), "pan_y": dy*RNG.uniform(0.01, 0.02)})
    return {
        "photo_indices": RNG.sample(range(len(PHOTOS)), k=min(n, len(PHOTOS))),
        "contrast": RNG.uniform(1.08, 1.15), "color_sat": RNG.uniform(1.15, 1.30),
        "brightness": RNG.uniform(0.95, 1.05), "vign": RNG.uniform(70, 95), "kb": kb,
    }

# ═══════════════════════════════════════════════════════════════════════════
# 5. RENDU D'UNE FRAME (AVEC ANIMATION DOUCE D'ENTRÉE/SORTIE)
# ═══════════════════════════════════════════════════════════════════════════
def render_frame(base_img, verse, reciter, title, alpha_frac, verse_num, total_verses):
    img = base_img.copy().convert("RGBA")
    ov  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d   = ImageDraw.Draw(ov, "RGBA")
    f   = fonts()
    
    af = max(0., min(1., alpha_frac))
    a  = int(255 * af)
    # Légère translation verticale (14px) pendant le fondu pour un effet fluide
    dy_anim = int((1.0 - _ease_inout(af)) * 14)

    # Fond dégradé sombre au centre pour faire ressortir le texte
    mid = H // 2 + dy_anim
    for yi in range(mid - 450, mid + 450):
        dist = abs(yi - mid) / 451.0
        sa = int(195 * max(0., 1.0 - dist ** 1.5))
        d.line([(0, yi), (W, yi)], fill=(5, 5, 15, sa))

    # Ligne et titre en haut
    band_y = mid - 400
    d.text((W//2 - _word_w(f["title"], title)//2, band_y), title, font=f["title"], fill=(255, 220, 100, int(a*0.95)))

    # Verset Arabe
    ar_h = draw_arabic_text_clean(d, verse["ar"], f["ar"], cx=W//2, y_start=mid - 250, max_w=920, alpha=a)

    # Séparateur ornemental doré
    sep_y = mid - 250 + ar_h + 20
    d.polygon([(W//2, sep_y - 6), (W//2 + 6, sep_y), (W//2, sep_y + 6), (W//2 - 6, sep_y)], fill=(255, 215, 80, a))
    
    # Référence et Traduction Anglaise
    ref_clean = verse["ref"].rstrip('abcdef')
    d.text((W//2 - _word_w(f["ref"], ref_clean)//2, sep_y + 15), ref_clean, font=f["ref"], fill=(255, 215, 80, int(a*0.9)))

    en_y = sep_y + 65
    for i, line in enumerate(verse["en"].split("\n")):
        lw = _word_w(f["en"], line)
        for dx, dy in [(-1,-1), (1,-1), (-1,1), (1,1), (0,2)]:
            d.text((W//2 - lw//2 + dx, en_y + i*60 + dy), line, font=f["en"], fill=(0, 0, 0, int(a*0.7)))
        d.text((W//2 - lw//2, en_y + i*60), line, font=f["en"], fill=(240, 245, 255, a))

    # Pagination et Récitateur en bas
    dot_y = int(H * 0.885)
    start_x = W//2 - (total_verses * 24) // 2
    for i in range(total_verses):
        xd = start_x + i * 24
        if i == verse_num - 1: d.ellipse([xd-7, dot_y-7, xd+7, dot_y+7], fill=(255, 215, 80, int(a*0.95)))
        else: d.ellipse([xd-3, dot_y-3, xd+3, dot_y+3], fill=(150, 150, 170, int(a*0.4)))

    rec_txt = f"{reciter['flag']}  {reciter['name']}"
    d.text((W//2 - _word_w(f["small"], rec_txt)//2, int(H * 0.920)), rec_txt, font=f["small"], fill=(212, 175, 55, int(a*0.85)))
    d.text((W//2 - _word_w(f["small"], ACCOUNT)//2, int(H * 0.950)), ACCOUNT, font=f["small"], fill=(255, 255, 255, int(a*0.75)))

    return Image.alpha_composite(img, ov).convert("RGB")

# ═══════════════════════════════════════════════════════════════════════════
# 6. GESTION AUDIO (SANS COUPURE ARTIFICIELLE)
# ═══════════════════════════════════════════════════════════════════════════
def dl_audio(verse, reciter):
    s, a, qid, ev = verse["surah"], str(verse["ayah"]).zfill(3), reciter["qid"], reciter["ev"]
    cache = OUT_DIR / "cache" / f"audio_{s}_{a}_{qid}.mp3"
    if cache.exists(): return cache
    urls = [
        f"https://cdn.islamic.network/quran/audio/128/{qid}/{s}{a}.mp3",
        f"https://everyayah.com/data/{ev}/{str(verse['surah']).zfill(3)}{a}.mp3",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r: data = r.read()
            if len(data) > 2000:
                cache.write_bytes(data)
                return cache
        except Exception: continue
    return None

def get_audio_dur(path):
    try:
        r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)], capture_output=True, text=True, timeout=5)
        return max(1.0, float(r.stdout.strip()))
    except: return 4.5

def select_verses(passage, reciter):
    sel, audios, aud_durs, frame_counts = [], [], [], []
    for verse in passage["verses"]:
        audio = dl_audio(verse, reciter)
        if not audio: raise AudioMissingError(f"Audio manquant pour {verse['ref']}")
        ad = get_audio_dur(audio)
        sel.append(verse)
        audios.append(audio)
        aud_durs.append(ad)
        # Nombre de frames synchronisé sur la durée audio réelle
        frame_counts.append(int(round(ad * FPS)))
    return sel, audios, aud_durs, sum(aud_durs), frame_counts

def mix_audio_clean(audio_list):
    """
    Concatène proprement les audios des versets SANS insérer de silence numérique.
    Le rythme de lecture est 100% fidèle et ne coupe jamais la voix.
    """
    inputs, concat_parts = [], []
    for idx, audio in enumerate(audio_list):
        inputs += ["-i", str(audio)]
        concat_parts.append(f"[{idx}:a]")
    
    flt = "".join(concat_parts) + f"concat=n={len(audio_list)}:v=0:a=1[aout]"
    out = OUT_DIR / "cache" / "audio_mixed.aac"
    r = subprocess.run(["ffmpeg", "-y"] + inputs + ["-filter_complex", flt, "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", str(out)], capture_output=True, text=True)
    if r.returncode != 0: return None
    return out

# ═══════════════════════════════════════════════════════════════════════════
# 7. BOUCLE DE GÉNÉRATION ET ENCODAGE
# ═══════════════════════════════════════════════════════════════════════════
def generate():
    order = list(range(len(PASSAGES)))
    RNG.shuffle(order)
    picked = None
    
    for idx in order:
        passage = PASSAGES[idx]
        shuffled_rec = RECITERS.copy(); RNG.shuffle(shuffled_rec)
        for cand in shuffled_rec:
            try:
                print(f"Tentative : « {passage['title']} » par {cand['name']}")
                verses, audios, aud_durs, total_dur, frame_counts = select_verses(passage, cand)
                picked = (passage, cand, verses, audios, aud_durs, total_dur, frame_counts)
                break
            except AudioMissingError: continue
        if picked: break

    if not picked: return None
    passage, reciter, verses, audios, aud_durs, total_dur, frame_counts = picked

    n = len(verses)
    p = make_params(n)
    scenes = [get_scene(i, p) for i in range(n)]
    fd = OUT_DIR / "frames"
    for f in fd.glob("*.jpg"): f.unlink()
    
    gi = 0
    print(f"🎨 Rendu visuel en cours ({sum(frame_counts)} frames - {total_dur:.1f}s)...")
    
    for vi in range(n):
        verse = verses[vi]
        sc_img = scenes[vi]
        kb = p["kb"][vi]
        n_frames = frame_counts[vi]
        
        # Transitions : Fondu d'entrée sur 0.5s et fondu de sortie sur 0.4s
        fade_in  = max(1, int(FPS * 0.50))
        fade_out = max(1, int(FPS * 0.40))
        next_sc  = scenes[vi+1] if vi < n-1 else None
        next_kb  = p["kb"][vi+1] if vi < n-1 else None

        for fi in range(n_frames):
            t_seg = fi / max(1, n_frames)
            
            # Fondu enchaîné de l'image de fond en toute fin de verset
            if next_sc is not None and fi >= (n_frames - fade_out):
                cross_t = _ease_inout((fi - (n_frames - fade_out)) / float(fade_out))
                frame_cur  = ken_burns(sc_img, t_seg, **kb)
                frame_next = ken_burns(next_sc, 0.0, **next_kb)
                frame = Image.blend(frame_cur, frame_next, cross_t)
            else:
                frame = ken_burns(sc_img, t_seg, **kb)

            # Opacité douce du texte
            if fi < fade_in: ta = _ease_inout(fi / float(fade_in))
            elif fi > n_frames - fade_out: ta = _ease_inout((n_frames - fi) / float(fade_out))
            else: ta = 1.0

            frame = render_frame(frame, verse, reciter, passage["title"], ta, vi+1, n)
            frame.save(str(fd / f"frame_{gi:06d}.jpg"), "JPEG", quality=92)
            gi += 1

    audio_track = mix_audio_clean(audios)
    if not audio_track: return None

    today = datetime.date.today().strftime("%Y%m%d")
    out = OUT_DIR / f"quran_{today}_s{RUN_SEED%99999:05d}.mp4"
    print("🎬 Encodage final de la vidéo...")
    
    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-start_number", "0", "-i", str(fd/"frame_%06d.jpg"),
           "-i", str(audio_track), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
           "-c:a", "aac", "-b:a", "192k", "-t", str(total_dur), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    
    if subprocess.run(cmd, capture_output=True).returncode == 0 and out.exists():
        print(f"✅ Vidéo générée avec succès : {out.name} ({out.stat().st_size / 1024 / 1024:.1f} MB)")
        for f in fd.glob("*.jpg"): f.unlink()
        return out
    return None

if __name__ == "__main__":
    video = generate()
    if video: sys.exit(0)
    else: sys.exit(1)
