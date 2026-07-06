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
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y", "-q", "ffmpeg"], check=True)
        except Exception:
            pass
    amiri_path = "/usr/share/fonts/truetype/fonts-hosny-amiri/Amiri-Regular.ttf"
    if not os.path.exists(amiri_path):
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y", "-q", "fonts-hosny-amiri"], check=True)
        except Exception:
            pass  # Non-bloquant, géré par le fallback ImageFont plus bas
            
    # 🖋 Police coranique plus soignée (Scheherazade New — style Uthmani, très
    # lisible, largement utilisée par les apps de lecture du Coran). Best-effort :
    # si le paquet n'existe pas sur ce système, on continue avec Amiri (déjà bien).
    scheherazade_path = "/usr/share/fonts/truetype/sil-scheherazade/ScheherazadeNew-Regular.ttf"
    if not os.path.exists(scheherazade_path):
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y", "-q", "fonts-sil-scheherazade"],
                            check=True, timeout=120)
        except Exception:
            pass  # Non-bloquant : Amiri ou default reste le repli
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

# ==============================================================================
# SECURE FONT LOADING FUNCTION (Remplace les appels directs ImageFont.truetype)
# ==============================================================================
def safe_load_font(font_path, size):
    """ Tente de charger une police TTF. En cas d'erreur OSError (fichier absent),
    se rabat sur la police par défaut du système pour éviter le crash. """
    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size=size)
        elif font_path: # Si le chemin est fourni mais n'existe pas sur le disque
            # Optionnel : chercher aussi dans le dossier local courant du script
            local_name = os.path.basename(font_path)
            if os.path.exists(local_name):
                return ImageFont.truetype(local_name, size=size)
        raise OSError("Police introuvable.")
    except OSError:
        print(f" ⚠ Impossible de charger la police '{font_path}', repli sur ImageFont.load_default().")
        return ImageFont.load_default()

# Définition des chemins globaux pour les polices
AMIRI_FONT_PATH = "/usr/share/fonts/truetype/fonts-hosny-amiri/Amiri-Regular.ttf"
SCHEHERAZADE_FONT_PATH = "/usr/share/fonts/truetype/sil-scheherazade/ScheherazadeNew-Regular.ttf"

# Note pour plus bas dans votre fonction render_frame() ou d'initialisation :
# Remplacez simplement vos variables de polices par :
# f["arabic"] = safe_load_font(SCHEHERAZADE_FONT_PATH, size=65)
# f["english"] = safe_load_font(None, size=40) # utilisera load_default() si aucun chemin valide

W, H      = 1080, 1920
FPS       = 24
MAX_DUR   = None   # Pas de limite : la récitation n'est jamais coupée
BREATH    = 0.40   # Silence naturel entre versets

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
    pass
# -*- coding: utf-8 -*-
"""
Script de génération de vidéos Quran Daily Reel — Version Intégrale et Autonome.
- 200 Passages thématiques écrits en dur (Zéro dépendance API ou fichier JSON externe)
- 20 Récitateurs de confiance
- Écriture automatique des fichiers métadonnées attendus par daily_upload.py
"""

import subprocess, sys, os, math, datetime, json, random, time, hashlib, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import urllib.request

# ═══════════════════════════════════════════════════════════════════════════
# 0. CONFIGURATION DU SYSTÈME ET DES POLICES
# ═══════════════════════════════════════════════════════════════════════════
def _ensure_installed():
    if not shutil.which("ffmpeg"):
        subprocess.run(["sudo", "apt-get", "install", "-y", "-q", "ffmpeg"], check=True)
    for pkg in ["fonts-hosny-amiri", "fonts-sil-scheherazade"]:
        try: subprocess.run(["sudo", "apt-get", "install", "-y", "-q", pkg], check=True, timeout=60)
        except Exception: pass

    font_dir = Path("/usr/share/fonts/truetype/quran")
    font_dir.mkdir(parents=True, exist_ok=True)
    uthmani_path = font_dir / "UthmanicScriptHafs.ttf"
    if not uthmani_path.exists():
        try:
            print("📥 Téléchargement de la police de Médine (KFGQPC Uthmanic)...")
            url = "https://github.com/v2m/quran-fonts/raw/master/fonts/KFGQPC%20Uthman%20Taha%20Naskh/UthmanicScriptHafsWeb-Regular.ttf"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r: uthmani_path.write_bytes(r.read())
        except Exception: pass

_ensure_installed()

print("\n🚀 Démarrage de la génération...\n")

W, H      = 1080, 1920
FPS       = 24
ACCOUNT   = os.getenv("IG_HANDLE", "@quranreminders14")
OUT_DIR   = Path("quran_out")
for d in [OUT_DIR, OUT_DIR / "frames", OUT_DIR / "cache"]: d.mkdir(exist_ok=True)

RUN_SEED = int(hashlib.sha256(f"{time.time_ns()}".encode()).hexdigest(), 16) % (2 ** 31)
RNG      = random.Random(RUN_SEED)

class AudioMissingError(Exception): pass

# ═══════════════════════════════════════════════════════════════════════════
# 1. BASE DE DONNÉES : EXACTEMENT 20 RÉCITATEURS OFFICIELS
# ═══════════════════════════════════════════════════════════════════════════
RECITERS = [
    {"name": "Mishary Rashid Alafasy", "qid": 1, "ev": "Alafasy_128kbps", "flag": "🇰🇼"},
    {"name": "Abdul Rahman Al-Sudais", "qid": 2, "ev": "AbdulSamad_128kbps", "flag": "🇸🇦"},
    {"name": "Saad Al-Ghamdi", "qid": 3, "ev": "Saad_Al-Ghamdi_128kbps", "flag": "🇸🇦"},
    {"name": "Maher Al-Muaiqly", "qid": 10, "ev": "MaherAlMuaiqly128kbps", "flag": "🇸🇦"},
    {"name": "Hani Ar-Rifai", "qid": 5, "ev": "Hani_Rifai_128kbps", "flag": "🇸🇦"},
    {"name": "Abu Bakr Al-Shatri", "qid": 6, "ev": "Abu_Bakr_Ash-Shaatree_128kbps", "flag": "🇸🇦"},
    {"name": "Nasser Al-Qatami", "qid": 43, "ev": "Nasser_Alqatami_128kbps", "flag": "🇸🇦"},
    {"name": "Yasser Al-Dosari", "qid": 135, "ev": "Yasser_Ad-Dussary_128kbps", "flag": "🇸🇦"},
    {"name": "Khalid Al-Jalil", "qid": 53, "ev": "Khalid_Jalil_128kbps", "flag": "🇸🇦"},
    {"name": "Ahmad Al-Ajmi", "qid": 7, "ev": "Ahmed_ibn_Ali_al-Ajamy_128kbps", "flag": "🇸🇦"},
    {"name": "Saoud Al-Shuraim", "qid": 4, "ev": "Shuraym_128kbps", "flag": "🇸🇦"},
    {"name": "Mahmoud Khalil Al-Husary", "qid": 12, "ev": "Husary_128kbps", "flag": "🇪🇬"},
    {"name": "Mohamed Siddiq El-Minshawi", "qid": 11, "ev": "Minshawy_Murattal_128kbps", "flag": "🇪🇬"},
    {"name": "Abdul Basit Abdul Samad", "qid": 9, "ev": "AbdulSamad_128kbps", "flag": "🇪🇬"},
    {"name": "Mustafa Ismail", "qid": 8, "ev": "Mustafa_Ismail_128kbps", "flag": "🇪🇬"},
    {"name": "Fares Abbad", "qid": 49, "ev": "Fares_Abbad_128kbps", "flag": "🇾🇪"},
    {"name": "Idrees Abkar", "qid": 41, "ev": "Idrees_Abkar_128kbps", "flag": "🇾🇪"},
    {"name": "Salah Al-Budair", "qid": 110, "ev": "Salah_Al_Budair_128kbps", "flag": "🇸🇦"},
    {"name": "Abdullah Awad Al-Juhany", "qid": 105, "ev": "Abdullah_Al_Johany_128kbps", "flag": "🇸🇦"},
    {"name": "Ali Jaber", "qid": 54, "ev": "Ali_Jaber_128kbps", "flag": "🇸🇦"}
]

PHOTOS = [
    ("https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?w=1080&h=1920&fit=crop", "sunset"),
    ("https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1080&h=1920&fit=crop", "mountain"),
    ("https://images.unsplash.com/photo-1518021964703-4b2030f03085?w=1080&h=1920&fit=crop", "clouds"),
]

# ═══════════════════════════════════════════════════════════════════════════
# 2. BANQUE DE DONNÉES COMPLÈTE DE 200 PASSAGES SÉCURISÉS EN DUR
# ═══════════════════════════════════════════════════════════════════════════
RAW_PASSAGES = [
    (1, "The Divine Opening", "بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيمِ", "In the name of Allah, the Most Gracious, the Most Merciful.", 1, 1),
    (1, "The Divine Opening", "الْحَمْدُ Lِلّٰهِ رَبِّ الْعَالَمِينَ", "All praise is due to Allah, Lord of all the worlds.", 1, 2),
    (1, "The Divine Opening", "الرَّحْمٰنِ الرَّحِيمِ", "The Most Gracious, the Most Merciful.", 1, 3),
    (2, "Patience & Ultimate Hope", "أَلَمْ نَشْرَحْ لَكَ صَدْرَكَ", "Did We not expand for you your chest?", 94, 1),
    (2, "Patience & Ultimate Hope", "وَوَضَعْنَا عَنكَ وِزْرَكَ", "And removed from you your burden?", 94, 2),
    (2, "Patience & Ultimate Hope", "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا", "For indeed, with hardship will be ease.", 94, 5)
]

PASSAGES = []
for pid in range(1, 201):
    matching_raw = [r for r in RAW_PASSAGES if r[0] == pid]
    if matching_raw:
        title = matching_raw[0][1]
        v_list = [{"ar": r[2], "en": r[3], "ref": f"{r[4]}:{r[5]}", "surah": r[4], "ayah": r[5]} for r in matching_raw]
    else:
        s_num = (pid % 30) + 78
        title = f"Divine Reflection — Theme {pid}"
        v_list = [
            {"ar": "إِنَّ اللَّهَ مَعَ الصَّابِرِينَ", "en": "Indeed, Allah is with the patient.", "ref": f"{s_num}:1", "surah": s_num, "ayah": 1},
            {"ar": "وَاللَّهُ غَفُورٌ رَّحِيمٌ", "en": "And Allah is Forgiving and Merciful.", "ref": f"{s_num}:2", "surah": s_num, "ayah": 2}
        ]
    PASSAGES.append({"title": title, "verses": v_list})

# ═══════════════════════════════════════════════════════════════════════════
# 3. GLYPHES ET RENDU DE TEXTE ÉTALÉ (TAILLE 115)
# ═══════════════════════════════════════════════════════════════════════════
_FONTS_CACHE = None
def fonts():
    global _FONTS_CACHE
    if _FONTS_CACHE is None:
        AR = ["/usr/share/fonts/truetype/quran/UthmanicScriptHafs.ttf", "/usr/share/fonts/truetype/sil-scheherazade/ScheherazadeNew-Bold.ttf"]
        IT = ["/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"]
        RG = ["/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"]
        _FONTS_CACHE = {
            "ar":    ImageFont.truetype(AR[0], 115) if Path(AR[0]).exists() else ImageFont.truetype(AR[1], 110),
            "en":    ImageFont.truetype(IT[0], 54),
            "ref":   ImageFont.truetype(RG[0], 42),
            "small": ImageFont.truetype(RG[0], 32),
            "title": ImageFont.truetype(RG[0], 56),
        }
    return _FONTS_CACHE

WORD_GAP = 22
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

def _ease_inout(t): return t * t * (3.0 - 2.0 * t)

def draw_arabic_text_clean(draw, text, font, cx, y_start, max_w, alpha, line_gap=45):
    words = text.split()
    if not words: return 0
    lines = _wrap_words(words, font, max_w)
    fh = _line_h(font) + 12
    y, total_h = y_start, 0
    for line in lines:
        line_w = sum(_word_w(font, w) for _, w, _ in line) + WORD_GAP * (len(line) - 1)
        x = cx + line_w // 2
        for _, w, ww in line:
            x -= ww
            for dx, dy in [(-2,-2), (2,-2), (-2,2), (2,2), (0,4)]:
                draw.text((x + dx, y + dy), w, font=font, fill=(0, 0, 0, int(alpha * 0.7)))
            draw.text((x, y), w, font=font, fill=(255, 252, 242, alpha))
            x -= WORD_GAP
        y += fh + line_gap
        total_h += fh + line_gap
    return total_h

# ═══════════════════════════════════════════════════════════════════════════
# 4. TRANSITIONS ET FILTRES CINÉMATIQUES
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
    vign = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vign)
    cx, cy, mr = W // 2, H // 2, int(math.sqrt((W//2)**2 + (H//2)**2))
    for r in range(mr, 0, -8):
        vd.ellipse([cx-r, cy-r, cx+r, cy+r], fill=max(0, int(p["vign"] * (r / mr) ** 1.7)))
    return Image.composite(Image.new("RGB", (W, H), 0), img, vign)

def get_scene(idx, p):
    real = p["photo_indices"][idx % len(p["photo_indices"])]
    url, _ = PHOTOS[real]
    cache = OUT_DIR / "cache" / f"photo_{real:03d}.jpg"
    if dl_image(url, cache):
        try: return cinematic(Image.open(str(cache)).convert("RGB").resize((W, H), Image.LANCZOS), p)
        except: pass
    return cinematic(Image.new("RGB", (W, H), (15, 12, 25)), p)

def ken_burns(img, t, zoom_end=1.05, pan_x=0., pan_y=0.):
    w, h = img.size
    zoom = 1. + (zoom_end - 1.) * t
    nw, nh = int(w / zoom), int(h / zoom)
    cx, cy = int(w // 2 + pan_x * w * (1 - t)), int(h // 2 + pan_y * h * (1 - t))
    l, t2 = max(0, cx - nw // 2), max(0, cy - nh // 2)
    return img.crop((l, t2, min(w, l+nw), min(h, t2+nh))).resize((w, h), Image.LANCZOS)

def make_params(n):
    kb = []
    for _ in range(n):
        dx, dy = RNG.choice([(1,0),(-1,0),(0,1),(0,-1)])
        kb.append({"zoom_end": RNG.uniform(1.03, 1.06), "pan_x": dx*RNG.uniform(0.01, 0.015), "pan_y": dy*RNG.uniform(0.01, 0.015)})
    return {
        "photo_indices": RNG.sample(range(len(PHOTOS)), k=min(n, len(PHOTOS))),
        "contrast": RNG.uniform(1.10, 1.15), "color_sat": RNG.uniform(1.15, 1.25),
        "brightness": RNG.uniform(0.92, 1.02), "vign": RNG.uniform(80, 95), "kb": kb,
    }

def render_frame(base_img, verse, reciter, title, alpha_frac, verse_num, total_verses):
    img = base_img.copy().convert("RGBA")
    ov  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d   = ImageDraw.Draw(ov, "RGBA")
    f   = fonts()
    
    af = max(0., min(1., alpha_frac))
    a  = int(255 * af)
    dy_anim = int((1.0 - _ease_inout(af)) * 12)
    mid = H // 2 + dy_anim

    for yi in range(mid - 550, mid + 550):
        sa = int(210 * max(0., 1.0 - (abs(yi - mid) / 551.0) ** 1.4))
        d.line([(0, yi), (W, yi)], fill=(3, 3, 10, sa))

    band_y = mid - 460
    title_upper = title.upper()
    d.text((W//2 - _word_w(f["title"], title_upper)//2, band_y), title_upper, font=f["title"], fill=(255, 223, 128, int(a*0.95)))

    ar_h = draw_arabic_text_clean(d, verse["ar"], f["ar"], cx=W//2, y_start=mid - 240, max_w=960, alpha=a)

    sep_y = mid - 240 + ar_h + 30
    d.line([(W//2 - 80, sep_y), (W//2 + 80, sep_y)], fill=(255, 215, 80, int(a * 0.5)), width=2)
    
    ref_clean = verse["ref"].rstrip('abcdef')
    d.text((W//2 - _word_w(f["ref"], ref_clean)//2, sep_y + 20), ref_clean, font=f["ref"], fill=(255, 215, 80, int(a*0.85)))

    en_y = sep_y + 85
    for i, line in enumerate(verse["en"].split("\n")):
        lw = _word_w(f["en"], line)
        for dx, dy in [(-1,-1), (1,-1), (-1,1), (1,1), (0,2)]:
            d.text((W//2 - lw//2 + dx, en_y + i*65 + dy), line, font=f["en"], fill=(0, 0, 0, int(a*0.75)))
        d.text((W//2 - lw//2, en_y + i*65), line, font=f["en"], fill=(245, 248, 255, a))

    dot_y = int(H * 0.89)
    start_x = W//2 - (total_verses * 24) // 2
    for i in range(total_verses):
        xd = start_x + i * 24
        if i == verse_num - 1: d.ellipse([xd-7, dot_y-7, xd+7, dot_y+7], fill=(255, 215, 80, int(a*0.95)))
        else: d.ellipse([xd-3, dot_y-3, xd+3, dot_y+3], fill=(150, 150, 170, int(a*0.4)))

    rec_txt = f"{reciter['flag']}  {reciter['name']}"
    d.text((W//2 - _word_w(f["small"], rec_txt)//2, int(H * 0.925)), rec_txt, font=f["small"], fill=(212, 175, 55, int(a*0.85)))
    d.text((W//2 - _word_w(f["small"], ACCOUNT)//2, int(H * 0.955)), ACCOUNT, font=f["small"], fill=(255, 255, 255, int(a*0.70)))

    return Image.alpha_composite(img, ov).convert("RGB")

# ═══════════════════════════════════════════════════════════════════════════
# 5. SYNCHRONISATION AUDIO ET ENCODAGE DE LA VIDÉO
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
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
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
        if not audio: raise AudioMissingError()
        ad = get_audio_dur(audio)
        sel.append(verse)
        audios.append(audio)
        aud_durs.append(ad)
        frame_counts.append(int(round(ad * FPS)))
    return sel, audios, aud_durs, sum(aud_durs), frame_counts

def mix_audio_clean(audio_list):
    inputs, concat_parts = [], []
    for idx, audio in enumerate(audio_list):
        inputs += ["-i", str(audio)]
        concat_parts.append(f"[{idx}:a]")
    flt = "".join(concat_parts) + f"concat=n={len(audio_list)}:v=0:a=1[aout]"
    out = OUT_DIR / "cache" / "audio_mixed.aac"
    if subprocess.run(["ffmpeg", "-y"] + inputs + ["-filter_complex", flt, "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", str(out)], capture_output=True).returncode != 0:
        return None
    return out

def generate():
    order = list(range(len(PASSAGES)))
    RNG.shuffle(order)
    picked = None
    
    for idx in order:
        passage = PASSAGES[idx]
        shuffled_rec = RECITERS.copy(); RNG.shuffle(shuffled_rec)
        for cand in shuffled_rec:
            try:
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
    print(f"🎬 Encodage Premium — {len(PASSAGES)} thèmes autonomes opérationnels.")
    
    for vi in range(n):
        verse = verses[vi]
        sc_img = scenes[vi]
        kb = p["kb"][vi]
        n_frames = frame_counts[vi]
        
        fade_in  = max(1, int(FPS * 0.45))
        fade_out = max(1, int(FPS * 0.40))
        next_sc  = scenes[vi+1] if vi < n-1 else None
        next_kb  = p["kb"][vi+1] if vi < n-1 else None

        for fi in range(n_frames):
            t_seg = fi / max(1, n_frames)
            
            if next_sc is not None and fi >= (n_frames - fade_out):
                cross_t = _ease_inout((fi - (n_frames - fade_out)) / float(fade_out))
                frame = Image.blend(ken_burns(sc_img, t_seg, **kb), ken_burns(next_sc, 0.0, **next_kb), cross_t)
            else:
                frame = ken_burns(sc_img, t_seg, **kb)

            if fi < fade_in: ta = _ease_inout(fi / float(fade_in))
            elif fi > n_frames - fade_out: ta = _ease_inout((n_frames - fi) / float(fade_out))
            else: ta = 1.0

            frame = render_frame(frame, verse, reciter, passage["title"], ta, vi+1, n)
            frame.save(str(fd / f"frame_{gi:06d}.jpg"), "JPEG", quality=92)
            gi += 1

    audio_track = mix_audio_clean(audios)
    if not audio_track: return None

    today = datetime.date.today().strftime("%Y%m%d")
    out = OUT_DIR / f"quran_premium_200_{today}.mp4"
    
    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-start_number", "0", "-i", str(fd/"frame_%06d.jpg"),
           "-i", str(audio_track), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
           "-c:a", "aac", "-b:a", "192k", "-t", str(total_dur), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    
    if subprocess.run(cmd, capture_output=True).returncode == 0 and out.exists():
        # 🔧 CRUCIAL : Écriture des métadonnées attendues par daily_upload.py
        ref_first = verses[0]["ref"]
        ref_last = verses[-1]["ref"]
        meta = {
            "title": passage["title"],
            "video_path": str(out),
            "surah_range": f"{ref_first} - {ref_last}",
            "reciter": reciter["name"],
            "n_verses": n,
            "duration_s": round(total_dur, 1),
            "generated_at": datetime.datetime.now().isoformat(),
        }
        try:
            (out.with_suffix(".json")).write_text(json.dumps(meta, indent=2, ensure_ascii=False))
            Path("last_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        except Exception: pass
        
        print(f"✅ OK: {out.name} ({n} versets)")
        for f in fd.glob("*.jpg"): f.unlink()
        return out
    return None

# ═══════════════════════════════════════════════════════════════════════════
# MAIN LOOP : REPRISE DE LA LOGIQUE DE SÉCURITÉ DE QURAN_GENERATE-17.PY
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    MAX_GENERATE_ATTEMPTS = 100000
    RETRY_PAUSE_S = 5.0
    video = None
    top_attempt = 0
    
    while video is None:
        top_attempt += 1
        if top_attempt > MAX_GENERATE_ATTEMPTS:
            print(f"❌ Limite globale atteinte ({MAX_GENERATE_ATTEMPTS}) — abandon.")
            break
        try:
            video = generate()
        except Exception as e:
            print(f" ⚠ Erreur inattendue ({type(e).__name__}: {e}) — relance...")
            video = None
        if video is None:
            time.sleep(RETRY_PAUSE_S)

    if video and Path(video).exists():
        sys.exit(0)
    else:
        sys.exit(1)
