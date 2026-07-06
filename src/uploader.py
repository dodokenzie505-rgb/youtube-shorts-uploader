"""
YouTube Shorts Uploader
Utilise l'API YouTube Data v3 pour uploader automatiquement des Shorts.
"""

import os
import json
import time
import pickle
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


# Scopes nécessaires pour uploader des vidéos
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]

TOKEN_PATH = Path("config/token.pickle")
CREDENTIALS_PATH = Path("config/client_secrets.json")


def authenticate(credentials_path: str = None, token_path: str = None) -> object:
    """
    Authentifie l'utilisateur via OAuth2.
    Compatible Google Colab (le flow 'oob' est mort, on utilise
    la méthode 'copier l'URL de redirection' à la place).

    Args:
        credentials_path: Chemin vers client_secrets.json
        token_path: Chemin vers le token sauvegardé

    Returns:
        Service YouTube authentifié
    """
    from urllib.parse import urlparse, parse_qs

    creds_path = Path(credentials_path or CREDENTIALS_PATH)
    tok_path = Path(token_path or TOKEN_PATH)
    tok_path.parent.mkdir(parents=True, exist_ok=True)

    creds = None

    # Charger le token existant
    if tok_path.exists():
        with open(tok_path, "rb") as f:
            creds = pickle.load(f)

    # Rafraîchir ou re-authentifier si nécessaire
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                raise FileNotFoundError(
                    f"❌ Fichier client_secrets.json introuvable : {creds_path}\n"
                    "👉 Télécharge-le depuis Google Cloud Console > APIs > Credentials"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            # 'localhost' est autorisé automatiquement pour un client OAuth
            # de type "Desktop app", même si la page ne charge pas vraiment.
            flow.redirect_uri = "http://localhost"

            auth_url, _ = flow.authorization_url(prompt="consent")
            print("\n👉 Clique sur ce lien, connecte-toi et autorise l'app :\n")
            print(auth_url)
            print(
                "\n📋 Ton navigateur va afficher une erreur "
                "'Impossible d'accéder à ce site' — c'est normal.\n"
                "   Copie l'URL COMPLÈTE dans la barre d'adresse "
                "(elle contient '?code=...') et colle-la ci-dessous :"
            )
            redirected_url = input("URL collée : ").strip()

            # Extraire le paramètre 'code' de l'URL collée
            parsed = urlparse(redirected_url)
            code = parse_qs(parsed.query).get("code")
            if not code:
                raise ValueError(
                    "❌ Impossible de trouver 'code=' dans l'URL collée. "
                    "Vérifie que tu as bien copié l'URL complète après autorisation."
                )
            code = code[0]

            flow.fetch_token(code=code)
            creds = flow.credentials

        # Sauvegarder le token pour les prochaines fois
        with open(tok_path, "wb") as f:
            pickle.dump(creds, f)
        print("✅ Token sauvegardé.")

    youtube = build("youtube", "v3", credentials=creds)
    print("✅ Authentification réussie.")
    return youtube


def upload_short(
    youtube,
    video_path: str,
    title: str,
    description: str = "",
    tags: list = None,
    category_id: str = "22",       # 22 = People & Blogs
    privacy: str = "public",        # public | private | unlisted
    thumbnail_path: str = None,
    made_for_kids: bool = False,
    retry: int = 3,
) -> dict:
    """
    Upload une vidéo en tant que YouTube Short.

    Args:
        youtube: Service YouTube authentifié
        video_path: Chemin vers le fichier vidéo (.mp4)
        title: Titre de la vidéo (max 100 caractères)
        description: Description (les #Shorts y sont ajoutés auto)
        tags: Liste de tags
        category_id: ID catégorie YouTube (défaut: People & Blogs)
        privacy: Visibilité (public / private / unlisted)
        thumbnail_path: Chemin vers une miniature personnalisée (optionnel)
        made_for_kids: True si contenu pour enfants
        retry: Nombre de tentatives en cas d'erreur réseau

    Returns:
        dict avec les infos de la vidéo uploadée (id, url, title...)
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"❌ Vidéo introuvable : {video_path}")

    # Ajouter #Shorts à la description pour forcer le format Short
    if "#Shorts" not in description and "#shorts" not in description:
        description = f"{description}\n\n#Shorts #Short".strip()

    body = {
        "snippet": {
            "title": title[:100],           # YouTube limite à 100 chars
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
            "defaultLanguage": "fr",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,             # Upload resumable = robuste sur Colab
        chunksize=1024 * 1024 * 5  # Chunks de 5MB
    )

    print(f"📤 Upload en cours : {video_path.name}")
    print(f"   Titre     : {title}")
    print(f"   Visibilité: {privacy}")

    for attempt in range(1, retry + 1):
        try:
            request = youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    print(f"   ⏳ Progression : {pct}%", end="\r")

            video_id = response["id"]
            url = f"https://www.youtube.com/shorts/{video_id}"
            print(f"\n✅ Vidéo uploadée avec succès !")
            print(f"   🔗 {url}")

            result = {
                "id": video_id,
                "url": url,
                "title": response["snippet"]["title"],
                "privacy": privacy,
            }

            # Upload miniature personnalisée si fournie
            if thumbnail_path and Path(thumbnail_path).exists():
                _upload_thumbnail(youtube, video_id, thumbnail_path)

            return result

        except HttpError as e:
            print(f"\n⚠️  Tentative {attempt}/{retry} échouée : {e}")
            if attempt < retry:
                wait = 2 ** attempt
                print(f"   Nouvel essai dans {wait}s...")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError("❌ Échec de l'upload après plusieurs tentatives.")


def _upload_thumbnail(youtube, video_id: str, thumbnail_path: str):
    """Upload une miniature pour une vidéo."""
    media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
    youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
    print(f"🖼️  Miniature uploadée.")


def batch_upload(
    youtube,
    videos: list,
    delay_seconds: int = 30,
    log_path: str = "config/upload_log.json",
) -> list:
    """
    Upload une liste de vidéos avec délai entre chaque.

    Args:
        youtube: Service YouTube authentifié
        videos: Liste de dicts {video_path, title, description, tags, privacy, thumbnail_path}
        delay_seconds: Délai entre chaque upload (évite les bans)
        log_path: Fichier JSON pour sauvegarder les résultats

    Returns:
        Liste des résultats d'upload
    """
    results = []
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    for i, video_info in enumerate(videos, 1):
        print(f"\n{'='*50}")
        print(f"📹 Vidéo {i}/{len(videos)}")
        try:
            result = upload_short(youtube, **video_info)
            result["status"] = "success"
            results.append(result)
        except Exception as e:
            print(f"❌ Erreur : {e}")
            results.append({
                "video_path": video_info.get("video_path"),
                "status": "failed",
                "error": str(e),
            })

        # Sauvegarder le log après chaque upload
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # Délai entre uploads (sauf pour le dernier)
        if i < len(videos):
            print(f"\n⏳ Pause de {delay_seconds}s avant le prochain upload...")
            time.sleep(delay_seconds)

    print(f"\n{'='*50}")
    print(f"✅ Batch terminé : {sum(1 for r in results if r['status']=='success')}/{len(videos)} réussis")
    print(f"📝 Log sauvegardé : {log_path}")
    return results
