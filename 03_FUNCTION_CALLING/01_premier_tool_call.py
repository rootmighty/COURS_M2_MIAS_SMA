"""
01_premier_tool_call.py
-----------------------
Le function calling natif : observer ce que renvoie l'API.

On envoie deux questions avec la liste des outils (paramètre `tools=`) :
    1. une question qui nécessite l'agenda   -> le modèle renvoie un "tool_call"
    2. une question qui n'en a pas besoin    -> le modèle répond normalement

Aucun outil n'est exécuté dans ce script : on regarde seulement la DEMANDE du modèle.

Lancement :
    python 03_FUNCTION_CALLING/01_premier_tool_call.py

EXERCICES :
    1. Ajoutez tool_choice="required" dans l'appel. Que se passe-t-il pour la question 2 ?
    2. Essayez tool_choice="none". Et pour la question 1 ?
    3. Retirez la description de l'outil chercher_creneaux dans schemas_outils.py.
       Le modèle l'utilise-t-il encore correctement ?
"""

import json
import os
from datetime import date, timedelta

from dotenv import load_dotenv
from openai import OpenAI

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

# Prochain jour ouvré
demain = date.today() + timedelta(days=1)
while demain.weekday() >= 5:
    demain += timedelta(days=1)

# Le system prompt ne décrit plus les outils : ils sont passés via `tools=`
SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {date.today().isoformat()}.
Horaires : du lundi au vendredi, 9h-12h et 14h-18h."""

QUESTIONS = [
    f"Est-ce qu'il vous reste un créneau le {demain:%d/%m} ?",
    "Quels sont vos horaires d'ouverture ?",
]


for question in QUESTIONS:
    print("=" * 70)
    print(f"PATIENT : {question}\n")

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        tools=SCHEMAS_OUTILS,   # liste des outils disponibles
        tool_choice="auto",     # "auto" : le modèle décide s'il utilise un outil
        max_tokens=1024,
        temperature=0,
        reasoning_effort=REASONING_EFFORT,
    )
    choice = completion.choices[0]
    message = choice.message

    # finish_reason vaut "tool_calls" quand le modèle demande un outil
    print(f"finish_reason : {choice.finish_reason}")

    if message.tool_calls:
        # Réponse brute : liste des demandes d'outils
        print("tool_calls (brut) :")
        print(json.dumps([tc.model_dump() for tc in message.tool_calls], indent=2, ensure_ascii=False))

        for tool_call in message.tool_calls:
            # Les arguments arrivent sous forme de chaîne JSON : il faut les décoder
            arguments = json.loads(tool_call.function.arguments)
            print(f"\n-> Outil demandé : {tool_call.function.name}")
            print(f"-> Arguments     : {arguments}")
            print(f"-> Identifiant   : {tool_call.id}")
    else:
        # Pas de demande d'outil : réponse texte classique
        print(f"Réponse : {message.content}")
    print()
