"""
Script lancé automatiquement chaque jour à 18h par GitHub Actions.
Il génère la vidéo Quran du jour et l'upload sur YouTube.
"""

import sys, os, subprocess, shutil, glob, datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from uploader import authenticate, upload_short


# ─────────────────────────────────────────────────────────────
# ÉTAPE 1 : Installer les dépendances système (GitHub Actions)
# ─────────────────────────────────────────────────────────────
def install_deps():
    print("📦 Installation des dépendances système...")
    subprocess.run(["apt-get", "install", "-y", "-q", "ffmpeg", "fonts-hosny-amiri"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
        "Pillow", "openai-whisper"], check=True)
    print("✅ Dépendances OK")


# ─────────────────────────────────────────────────────────────
# ÉTAPE 2 : Exécuter ton code de génération Quran
# ─────────────────────────────────────────────────────────────
def generer_video() -> str:
    """
    Exécute le notebook Quran converti en script et retourne
    le chemin de la vidéo générée.
    """
    # Lancer le script de génération (extrait de ton notebook)
    env = os.environ.copy()
    env["WHISPER_MODEL"] = "small"
    env["IG_HANDLE"] = "@quranreminders14"

    result = subprocess.run(
        [sys.executable, "scripts/quran_generate.py"],
        env=env,
        capture_output=False
    )

    if result.returncode != 0:
        raise RuntimeError("❌ Erreur lors de la génération de la vidéo")

    # Trouver la vidéo YouTube générée (suffixe _youtube.mp4)
    videos = sorted(glob.glob("quran_out/*_youtube.mp4"), key=os.path.getmtime, reverse=True)
    if not videos:
        # Fallback : prendre le mp4 le plus récent
        videos = sorted(glob.glob("quran_out/*.mp4"), key=os.path.getmtime, reverse=True)
    if not videos:
        raise FileNotFoundError("❌ Aucune vidéo trouvée dans quran_out/")

    print(f"✅ Vidéo trouvée : {videos[0]}")
    return videos[0]


# ─────────────────────────────────────────────────────────────
# ÉTAPE 3 : Upload sur YouTube
# ─────────────────────────────────────────────────────────────
def main():
    today = datetime.date.today().strftime("%d/%m/%Y")
    print(f"🗓️  Lancement de l'upload du {today} à 18h Paris...")

    install_deps()
    video_path = generer_video()

    youtube = authenticate(
        credentials_path="config/client_secrets.json",
        token_path="config/token.pickle",
    )

    title = f"Quran Daily Reel — {today} 🕌 #Shorts"
    description = (
        f"Récitation du Coran du {today}.\n"
        "Écoute, médite et partage ❤️\n\n"
        "#Shorts #Quran #Coran #Islam #QuranRecitation #QuranReminders"
    )
    tags = ["quran", "coran", "islam", "shorts", "récitation", "daily", "reminder"]

    result = upload_short(
        youtube=youtube,
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        privacy="public",
    )

    print(f"\n🎉 Vidéo en ligne : {result['url']}")


if __name__ == "__main__":
    main()
