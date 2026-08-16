"""
Script lancé automatiquement chaque jour à 18h par GitHub Actions.
Il génère la vidéo Quran du jour et l'upload sur YouTube.
"""

import sys, os, subprocess, glob, datetime, json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from uploader import authenticate, upload_short


def generer_video():
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

    # 🔧 Métadonnées du passage (thème anglais, récitateur, etc.) écrites par
    # quran_generate.py dans quran_out/last_meta.json. On les lit ici pour
    # pouvoir utiliser le thème comme titre du short, au lieu d'un titre
    # générique avec juste la date.
    meta = {}
    meta_path = Path("quran_out/last_meta.json")
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception as e:
            print(f"   ⚠ Lecture de last_meta.json échouée ({e}) — titre générique utilisé en repli")
    else:
        print("   ⚠ quran_out/last_meta.json introuvable — titre générique utilisé en repli")

    return videos[0], meta


# ═══════════════════════════════════════════════════════════════════════════
# 💬 Commentaire épinglé — appel à s'abonner
# ═══════════════════════════════════════════════════════════════════════════
# ⚠️ LIMITE CONNUE DE L'API : YouTube Data API v3 n'expose AUCUN endpoint pour
# épingler un commentaire (ni "pinComment", ni un flag sur commentThreads.
# insert/comments.update). C'est une action réservée à l'interface YouTube
# Studio, jamais rendue publique côté API — ce n'est pas une lacune de ce
# script, juste une limite de Google. On ne peut donc PAS automatiser
# l'épinglage lui-même. Par contre, on PEUT poster automatiquement le
# commentaire (via commentThreads.insert) pour qu'il ne reste plus qu'à
# l'épingler d'un tap dans l'app YouTube (30 secondes/jour), au lieu de devoir
# aussi le rédiger et le copier-coller à la main.
def post_comment(youtube, video_id, text):
    """
    Poste `text` en commentaire de haut niveau sur la vidéo `video_id`.
    Ne bloque jamais l'upload en cas d'échec (commentaires désactivés sur la
    chaîne/vidéo, quota API épuisé, etc.) — best-effort, comme le reste du
    pipeline.
    """
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": text}
                    }
                }
            }
        ).execute()
        print(f"   💬 Commentaire posté (à épingler manuellement dans YouTube Studio/app — l'API ne permet pas l'épinglage) : {text}")
        return True
    except Exception as e:
        print(f"   ⚠ Échec du post du commentaire (non bloquant) : {e}")
        return False


def main():
    today = datetime.date.today().strftime("%d/%m/%Y")
    print(f"🗓️  Lancement de l'upload du {today} à 18h Paris...")

    video_path, meta = generer_video()

    youtube = authenticate(
        credentials_path="config/client_secrets.json",
        token_path="config/token.pickle",
    )

    # 🔧 Titre = thème du passage en anglais (ex: "Patience and Hope"),
    # déjà fourni en anglais par PASSAGES dans quran_generate.py.
    # Repli sur l'ancien titre générique si la métadonnée est absente
    # (ne doit jamais bloquer l'upload).
    theme = meta.get("title")
    if theme:
        title = f"{theme} 🕌 #Shorts"
    else:
        title = f"Quran Daily Reel — {today} 🕌 #Shorts"

    surah_range = meta.get("surah_range", "")
    reciter     = meta.get("reciter", "")
    extra_desc  = f"Sourate : {surah_range}\nRécitateur : {reciter}\n\n" if surah_range else ""
    description = (
        f"{extra_desc}"
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

    # 💬 Poste le commentaire suggéré par quran_generate.py (question +
    # appel à s'abonner, en anglais — voir suggested_pinned_comment dans
    # last_meta.json). Best-effort : ne fait jamais échouer le run si ça
    # rate, la vidéo est déjà en ligne à ce stade.
    pinned_text = meta.get("suggested_pinned_comment")
    video_id = result.get("id")
    if not video_id and result.get("url"):
        # repli si upload_short ne renvoie pas 'id' directement
        video_id = result["url"].rstrip("/").split("/")[-1]
    if pinned_text and video_id:
        post_comment(youtube, video_id, pinned_text)
    elif pinned_text and not video_id:
        print("   ⚠ Impossible de déterminer l'ID vidéo — commentaire non posté (à faire manuellement).")


if __name__ == "__main__":
    main()
