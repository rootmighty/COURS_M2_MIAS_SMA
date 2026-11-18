"""
01_le_probleme.py
-----------------
Pourquoi a-t-on besoin d'outils ?

On demande à Doc'Assist s'il reste un créneau demain. Le modèle n'a AUCUN
accès à l'agenda : au mieux il l'avoue, au pire il invente une réponse
crédible (hallucination). Dans les deux cas, il ne peut pas réserver.

Lancement :
    python 02_TOOLS_MANUELS/01_le_probleme.py

Relancez plusieurs fois : la réponse change-t-elle ? Est-elle vraie ?
Comparez avec l'agenda réel affiché à la fin.
"""

import os
from datetime import date, timedelta

from dotenv import load_dotenv
from openai import OpenAI

# Outil utilisé uniquement pour afficher l'agenda réel à la fin
from outils_cabinet import chercher_creneaux

# Charge les variables du fichier .env (clé API, modèle...)
load_dotenv()

# --- Configuration ---------------------------------------------------------
# Client OpenAI pointé vers l'API NVIDIA (compatible OpenAI, cf. étape 00)
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
    max_retries=3,   # réessais automatiques en cas de 429 / erreur serveur
    timeout=60,
)
MODEL = os.getenv("NVIDIA_MODEL", "mistralai/mistral-large-4-1t-a52b")
REASONING_EFFORT = os.getenv("NVIDIA_REASONING_EFFORT", "low")

# Prochain jour ouvré (on saute le week-end, où le cabinet est fermé)
demain = date.today() + timedelta(days=1)
while demain.weekday() >= 5:
    demain += timedelta(days=1)

# System prompt : rôle et date du jour, sans information sur les créneaux
SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {date.today().isoformat()}.
Tu aides les patients à prendre rendez-vous. Ton ton est chaleureux et concis."""

# {demain:%d/%m} : formatage de la date en "JJ/MM" directement dans la f-string
question = f"Bonjour, est-ce qu'il vous reste un créneau le {demain:%d/%m} ? Et à quelle heure ?"

# --- Appel au modèle ---------------------------------------------------------
completion = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ],
    max_tokens=1024,
    temperature=0.7,   # réponses plus variées d'un lancement à l'autre
    reasoning_effort=REASONING_EFFORT,
)

# --- Comparaison : ce que dit le modèle vs la réalité ---------------------
print(f"PATIENT  : {question}")
print(f"DOC'ASSIST : {completion.choices[0].message.content}\n")
print(f"AGENDA RÉEL : {chercher_creneaux(demain.isoformat())}")
