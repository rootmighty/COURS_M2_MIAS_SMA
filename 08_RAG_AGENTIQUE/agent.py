"""
agent.py
--------
La boucle agent : le modèle est appelé tant qu'il demande des outils,
jusqu'à ce qu'il produise une réponse texte.

Fonctionnalités :
    - limite d'étapes, avec une réponse finale forcée (sans outils) quand elle est atteinte ;
    - taille du contexte envoyé au modèle (en tokens), renvoyée avec la réponse ;
    - contrôle optionnel avant chaque outil (paramètre garde_outil), qui peut refuser l'appel.

Ce fichier n'est pas lancé directement : il est importé par les autres scripts du dossier.
"""

import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# --- Configuration ---------------------------------------------------------
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
    max_retries=3,
    timeout=60,
)
MODEL = os.getenv("NVIDIA_MODEL", "mistralai/mistral-large-4-1t-a52b")
REASONING_EFFORT = os.getenv("NVIDIA_REASONING_EFFORT", "low")

# Règle à ajouter dans les system prompts pour éviter les boucles d'exploration
CRITERE_ARRET = ("Si tu ne trouves pas ce que tu cherches après 2 ou 3 essais, "
                 "arrête de chercher et réponds avec les informations déjà obtenues.")

# Message ajouté (temporairement) pour le dernier appel quand la limite est atteinte
MESSAGE_LIMITE = ("[SYSTÈME] Nombre maximum d'étapes atteint. Réponds maintenant au patient "
                  "avec les informations déjà obtenues, sans utiliser d'outil.")


def appeler_llm(messages, schemas=None, tool_choice="auto"):
    """Appelle le modèle et renvoie la réponse complète de l'API (message + usage)."""
    parametres = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0,
        "reasoning_effort": REASONING_EFFORT,
    }
    # Les outils ne sont envoyés que s'il y en a
    if schemas:
        parametres["tools"] = schemas
        parametres["tool_choice"] = tool_choice
    return client.chat.completions.create(**parametres)


def tokens_contexte(completion):
    """Nombre de tokens envoyés au modèle lors de cet appel (0 si non fourni par l'API)."""
    return completion.usage.prompt_tokens if completion.usage else 0


def executer_outil(fonctions, nom, arguments_json, garde_outil=None):
    """Exécute l'outil demandé.

    fonctions   : dictionnaire {nom de l'outil -> fonction Python}
    garde_outil : fonction (nom, arguments) -> None si l'appel est autorisé,
                  ou un dictionnaire {"erreur": ...} si l'appel est refusé.
    """
    if nom not in fonctions:
        return {"erreur": f"Outil inconnu : '{nom}'."}
    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return {"erreur": f"Arguments non lisibles : {arguments_json}"}

    # Contrôle avant exécution : en cas de refus, l'outil n'est pas exécuté
    if garde_outil:
        refus = garde_outil(nom, arguments)
        if refus:
            return refus

    try:
        return fonctions[nom](**arguments)
    except TypeError as e:
        return {"erreur": f"Arguments invalides pour {nom} : {e}"}


def executer_agent(messages, schemas, fonctions, max_etapes=6, verbeux=True, garde_outil=None):
    """Fait tourner l'agent jusqu'à obtenir une réponse texte.

    messages    : historique (modifié sur place)
    schemas     : description des outils au format de l'API
    fonctions   : dictionnaire {nom de l'outil -> fonction Python}
    garde_outil : contrôle optionnel appelé avant chaque outil (voir executer_outil)

    Renvoie (réponse finale, tokens du contexte lors du dernier appel).
    """
    tokens = 0
    for etape in range(1, max_etapes + 1):
        if verbeux:
            print(f"   ── Étape {etape} ──")
        completion = appeler_llm(messages, schemas)
        tokens = tokens_contexte(completion)
        message = completion.choices[0].message

        # Pas de demande d'outil : réponse finale
        if not message.tool_calls:
            reponse = message.content or "(pas de réponse texte)"
            messages.append({"role": "assistant", "content": reponse})
            return reponse, tokens

        # Exécution des outils demandés et ajout des résultats à l'historique
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [tc.model_dump() for tc in message.tool_calls],
        })
        for tool_call in message.tool_calls:
            nom = tool_call.function.name
            if verbeux:
                print(f"   🔧 {nom}({tool_call.function.arguments})")
            resultat = executer_outil(fonctions, nom, tool_call.function.arguments, garde_outil)
            if verbeux:
                print(f"   📋 {resultat}")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(resultat, ensure_ascii=False),
            })

    # --- Limite atteinte : réponse finale forcée ---
    # Dernier appel avec tool_choice="none" : le modèle doit répondre en texte.
    # MESSAGE_LIMITE est ajouté à une copie de l'historique, pas à l'historique lui-même.
    if verbeux:
        print(f"   ⚠️  Limite de {max_etapes} étapes atteinte : demande d'une réponse finale.")
    try:
        completion = appeler_llm(messages + [{"role": "user", "content": MESSAGE_LIMITE}],
                                 schemas, tool_choice="none")
        tokens = tokens_contexte(completion)
        reponse = completion.choices[0].message.content or ""
    except Exception:
        reponse = ""
    if not reponse:
        reponse = "Désolé, je n'ai pas réussi à traiter votre demande. Pouvez-vous la reformuler ?"
    messages.append({"role": "assistant", "content": reponse})
    return reponse, tokens
