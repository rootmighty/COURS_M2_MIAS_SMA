"""
02_chat_function_calling.py
---------------------------
Le chat de l'étape 02, réécrit avec le function calling natif.

Différences avec le protocole "fait maison" :
    - les outils sont décrits par des schémas JSON (paramètre `tools=`) ;
    - la demande d'outil arrive dans un champ dédié : message.tool_calls ;
    - le résultat est renvoyé avec le rôle "tool" et l'identifiant de la demande ;
    - le modèle peut demander plusieurs outils dans une même réponse.

          patient ──> LLM ──> message.tool_calls ──> notre code exécute les fonctions
                       ^                                        │
                       └──── messages {"role": "tool", ...} ────┘

Lancement :
    python 03_FUNCTION_CALLING/02_chat_function_calling.py

Scénario à tester :
    Vous : Bonjour, il reste de la place demain matin ?
    Vous : Je prends le premier créneau, je m'appelle Mme Dubois.
    Vous : Quels créneaux avez-vous lundi et mardi prochains ?
    Vous : Réservez-moi le créneau de ... lundi
    Vous : annulez tous mes rendez-vous.

EXERCICES :
    1. Ajoutez l'outil "annuler_rdv(date, heure, nom)" : fonction, schéma, catalogue.
       Comparez avec l'étape 02 : qu'est-ce qui a changé dans le travail à faire ?
    2. Demandez les créneaux de deux jours différents. Combien de tool_calls reçoit-on ?
    3. Demandez directement : "Réservez-moi le premier créneau libre demain, je suis M. Leroy."
       Que se passe-t-il ? Pourquoi ?
"""

import json
import os
from datetime import date

from dotenv import load_dotenv
from openai import OpenAI

from outils_cabinet import OUTILS
from schemas_outils import SCHEMAS_OUTILS

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

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

# Le system prompt ne contient plus que le rôle et les règles :
# la description des outils est transmise séparément via `tools=`.
SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.
Horaires : du lundi au vendredi, 9h-12h et 14h-18h.
Tu vouvoies le patient, ton ton est chaleureux et concis.
Tu ne donnes jamais de conseil médical.
N'invente jamais une disponibilité : vérifie toujours avec l'outil chercher_creneaux.
Ne réserve qu'après accord explicite du patient et quand tu connais son nom."""


# --- Fonctions utilitaires ---------------------------------------------------
def appeler_llm(messages):
    """Envoie l'historique et la liste des outils, renvoie le message du modèle."""
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=SCHEMAS_OUTILS,
        tool_choice="auto",
        max_tokens=1024,
        temperature=0,
        reasoning_effort=REASONING_EFFORT,
    )
    # On renvoie l'objet message complet (contenu texte ET éventuels tool_calls)
    return completion.choices[0].message


def executer_outil(nom, arguments_json):
    """Exécute l'outil demandé à partir de son nom et de ses arguments (chaîne JSON).

    Renvoie un dictionnaire de résultat, ou un dictionnaire d'erreur.
    """
    if nom not in OUTILS:
        return {"erreur": f"Outil inconnu : '{nom}'."}

    # Les arguments arrivent sous forme de texte JSON : on les décode
    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return {"erreur": f"Arguments non lisibles : {arguments_json}"}

    try:
        return OUTILS[nom](**arguments)
    except TypeError as e:  # arguments manquants, en trop, ou mal nommés
        return {"erreur": f"Arguments invalides pour {nom} : {e}"}


# --- Programme principal : le chat -------------------------------------------
def main():
    print("Doc'Assist (function calling) — tapez 'exit' pour quitter.\n")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

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

        # 1er appel : le modèle répond OU demande un ou plusieurs outils
        message = appeler_llm(messages)

        if message.tool_calls:
            # On ajoute à l'historique le message du modèle AVEC ses tool_calls.
            # model_dump() convertit chaque tool_call (objet du SDK) en dictionnaire.
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [tc.model_dump() for tc in message.tool_calls],
            })

            # Exécution de chaque outil demandé (il peut y en avoir plusieurs)
            for tool_call in message.tool_calls:
                nom = tool_call.function.name
                print(f"   🔧 {nom}({tool_call.function.arguments})")
                resultat = executer_outil(nom, tool_call.function.arguments)
                print(f"   📋 {resultat}")

                # Résultat renvoyé avec le rôle "tool".
                # tool_call_id relie ce résultat à la demande correspondante.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(resultat, ensure_ascii=False),
                })

            # 2e appel : le modèle rédige sa réponse à partir des résultats
            message = appeler_llm(messages)

        # Un seul tour d'outils est traité par question :
        # si le modèle en demande d'autres, ils ne sont pas exécutés.
        if message.tool_calls:
            noms = [tc.function.name for tc in message.tool_calls]
            print(f"   ⚠️  Nouvelle demande d'outil non traitée : {noms}")

        reponse = message.content or "(pas de réponse texte)"
        messages.append({"role": "assistant", "content": reponse})
        print(f"Doc'Assist : {reponse}\n")


if __name__ == "__main__":
    main()
