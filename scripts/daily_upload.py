"""
Script lancé automatiquement chaque jour à 18h par GitHub Actions.
Il génère la vidéo Quran du jour et l'upload sur YouTube.
"""

import sys, os, subprocess, glob, datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from uploader import authenticate, upload_short


def generer_video() -> str:
    env = os.environ.copy()
    env["WHISPER_MODEL"] = "small"
    env["IG_HANDLE"] = "@quranreminders14"

    result = subprocess.run(
        [sys.executable, "scripts/quran_generate.py"],
        env=env
    )

    if result.returncode != 0:
        raise RuntimeError("❌ Erreur lors de la génération de la vidéo")

    videos = sorted(glob.glob("quran_out/*_youtube.mp4"), key=os.path.getmtime, reverse=True)
    if not videos:
        videos = sorted(glob.glob("quran_out/*.mp4"), key=os.path.getmtime, reverse=True)
    if not videos:
        raise FileNotFoundError("❌ Aucune vidéo trouvée dans quran_out/")

    print(f"✅ Vidéo trouvée : {videos[0]}")
    return videos[0]


def main():
    today = datetime.date.today().strftime("%d/%m/%Y")
    print(f"🗓️  Lancement de l'upload du {today} à 18h Paris...")

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
