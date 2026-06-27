"""
Extraction du code de génération du notebook quran_reel_v7-5.
Ce script est appelé par daily_upload.py chaque jour.
Il génère la vidéo dans quran_out/ puis encode la version YouTube.
"""

import subprocess, sys, importlib, shutil, os, math
import datetime, json, random, time, hashlib, unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import urllib.request

# ══════════════════════════════════════════════════════════
# CONFIG (identique à ton notebook)
# ══════════════════════════════════════════════════════════
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "small")
_whisper_model = None
_WHISPER_OK    = False

W, H      = 1080, 1920
FPS       = 24
MAX_DUR   = None
BREATH    = 0.40
ACCOUNT   = os.getenv("IG_HANDLE", "@quranreminders14")
OUT_DIR   = Path("quran_out")
for d in [OUT_DIR, OUT_DIR / "frames", OUT_DIR / "cache"]:
    d.mkdir(exist_ok=True)

def make_seed():
    raw = f"{time.time_ns()}_{os.urandom(16).hex()}_{os.getpid()}"
    return int(hashlib.sha256(raw.encode()).hexdigest(), 16) % (2 ** 31)

RUN_SEED = make_seed()
RNG      = random.Random(RUN_SEED)

# ══════════════════════════════════════════════════════════
# TOUT LE RESTE DU CODE DE TON NOTEBOOK EST ICI
# (PASSAGES, RECITERS, fonctions generate(), etc.)
# Colle le contenu de ton notebook ici entre ces lignes
# ══════════════════════════════════════════════════════════

# [TON CODE ICI — voir instructions ci-dessous]

# ══════════════════════════════════════════════════════════
# LANCEMENT + ENCODAGE YOUTUBE
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f'🎲 Seed : {RUN_SEED}')
    video = generate()  # passage et récitateur 100% aléatoires

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
