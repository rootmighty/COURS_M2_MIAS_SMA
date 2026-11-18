"""
03_chat_streaming.py
--------------------
Petit chat en ligne de commande avec un modèle de l'API NVIDIA.

- La réponse s'affiche en streaming (morceau par morceau).
- L'historique est conservé pour que le modèle "se souvienne" de la conversation.
- Les erreurs temporaires (429 quota, 5xx serveur, réseau) sont réessayées.

Configuration : fichier .env à la racine du projet
    NVIDIA_API_KEY=nvapi-...      (obligatoire)
    NVIDIA_MODEL=...              (optionnel)

Lancement :
    source .venv/bin/activate
    python 00_LLM_CALL/03_chat_streaming.py

EXERCICE :
    1. Présentez-vous ("Je m'appelle ..."), puis demandez "Comment je m'appelle ?".
    2. Passez MEMOIRE = False et refaites exactement le même échange.
    Que se passe-t-il ? Qu'en concluez-vous sur la "mémoire" d'un LLM ?
"""

import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---------------------------------------------------------
API_KEY = os.getenv("NVIDIA_API_KEY")
MODEL = os.getenv("NVIDIA_MODEL", "mistralai/mistral-large-4-1t-a52b")
REASONING_EFFORT = os.getenv("NVIDIA_REASONING_EFFORT", "low")  # low | medium | high
INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

MEMOIRE = True  # [EXERCICE] passez à False et refaites le test

MAX_RETRIES = 3
RETRY_STATUS = {429, 500, 502, 503, 504}  # erreurs temporaires qui valent un réessai

# Codes couleur du terminal (pour afficher le raisonnement en gris)
GREY, RESET = "\033[90m", "\033[0m"


def post_with_retry(headers, payload):
    """Envoie la requête et réessaie en cas d'erreur temporaire.

    Attente croissante entre les essais (backoff exponentiel) : 2s, 4s, 8s.
    Si le serveur indique combien de temps attendre (en-tête Retry-After),
    on respecte sa demande.
    """
    response = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                INVOKE_URL, headers=headers, json=payload, stream=True, timeout=300
            )
            if response.status_code not in RETRY_STATUS:
                return response  # succès, ou erreur définitive (401, 404...)
            reason = f"HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:  # réseau coupé, timeout...
            response = None
            reason = f"erreur réseau ({type(e).__name__})"

        if attempt < MAX_RETRIES:
            wait = 2 ** (attempt + 1)
            if response is not None and response.headers.get("Retry-After", "").isdigit():
                wait = int(response.headers["Retry-After"])
            print(f"\n[{reason} — nouvel essai dans {wait}s...]", flush=True)
            time.sleep(wait)

    return response


def ask(messages):
    """Envoie l'historique au modèle et affiche la réponse en streaming.

    `messages` est la liste des échanges au format OpenAI :
    [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]

    Retourne le texte complet de la réponse, ou None en cas d'erreur.
    """
    # "text/event-stream" : on veut la réponse morceau par morceau (format SSE)
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "text/event-stream"}
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 4096,   # longueur maximale de la réponse
        "stream": True,       # réponse envoyée au fil de l'eau
        "temperature": 0.5,   # créativité : 0 = déterministe, plus haut = plus varié
        "top_p": 1,
        "reasoning_effort": REASONING_EFFORT,  # réflexion courte = réponses plus rapides
    }

    response = post_with_retry(headers, payload)

    if response is None:
        print("Impossible de joindre l'API après plusieurs essais.")
        return None
    # 401 = clé invalide, 404 = modèle inconnu, 429 = quota toujours dépassé...
    if not response.ok:
        print(f"Erreur HTTP {response.status_code} : {response.text}")
        return None

    answer = ""
    in_reasoning = False

    # Le flux SSE est une suite de lignes. Seules celles qui commencent
    # par "data: " contiennent la réponse ; les autres (": ping",
    # "event: ...") sont des commentaires ou métadonnées qu'on ignore.
    for line in response.iter_lines():
        if not line:
            continue  # lignes vides = séparateurs entre événements
        line = line.decode("utf-8")
        if not line.startswith("data: "):
            continue
        data = line.removeprefix("data: ")
        if data == "[DONE]":
            break  # le serveur signale la fin de la réponse

        choices = json.loads(data).get("choices")
        if not choices:
            continue  # certains événements (ex. statistiques d'usage) n'ont pas de contenu
        delta = choices[0].get("delta", {})

        # Modèles "thinking" : le raisonnement arrive à part, avant la réponse.
        # On l'affiche en gris mais on ne le garde pas dans l'historique.
        reasoning = delta.get("reasoning_content") or ""
        if reasoning:
            if not in_reasoning:
                print(f"{GREY}[raisonnement] ", end="")
                in_reasoning = True
            print(reasoning, end="", flush=True)

        chunk = delta.get("content") or ""
        if chunk:
            if in_reasoning:
                print(f"{RESET}\n", end="")
                in_reasoning = False
            answer += chunk
            print(chunk, end="", flush=True)  # affichage immédiat

    print(RESET if in_reasoning else "")
    return answer


def main():
    if not API_KEY or API_KEY.startswith("nvapi-xxx"):
        sys.exit("NVIDIA_API_KEY manquante : copiez .env.example en .env et renseignez votre clé.")

    print(f"Chat avec {MODEL} — tapez 'exit' pour quitter.\n")
    messages = []  # historique, renvoyé EN ENTIER à chaque question

    while True:
        try:
            question = input("Vous : ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl+D ou Ctrl+C
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        messages.append({"role": "user", "content": question})
        print("IA : ", end="", flush=True)
        # Avec mémoire : on envoie tout l'historique.
        # Sans mémoire : on n'envoie que la question actuelle.
        answer = ask(messages if MEMOIRE else [messages[-1]])
        if answer is None:
            messages.pop()  # on retire la question pour garder un historique cohérent
        else:
            messages.append({"role": "assistant", "content": answer})
        print()


if __name__ == "__main__":
    main()