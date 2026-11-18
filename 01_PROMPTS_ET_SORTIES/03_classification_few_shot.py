"""
03_classification_few_shot.py
-----------------------------
Classer les messages entrants avec quelques exemples (few-shot).

Avant de traiter un message, Doc'Assist doit savoir DE QUOI il s'agit :
prise de rendez-vous, annulation, question pratique ou urgence médicale.
C'est un "routeur" : plus tard, chaque catégorie sera confiée à un agent différent.

Le few-shot consiste à montrer au modèle quelques exemples de questions
déjà classées, sous forme de faux échanges user/assistant, avant la vraie question.

Lancement :
    python 01_PROMPTS_ET_SORTIES/03_classification_few_shot.py

EXERCICES :
    1. Mettez USE_EXEMPLES = False (zero-shot). Les résultats changent-ils ?
    2. Ajoutez une catégorie "RESULTATS_ANALYSES". Que faut-il modifier ?
    3. Trouvez un message que le modèle classe mal, puis ajoutez un exemple pour le corriger.
"""

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

# True = few-shot (avec exemples), False = zero-shot (consigne seule)
USE_EXEMPLES = True

# Liste fermée des catégories possibles : le modèle doit choisir parmi elles
CATEGORIES = ["PRISE_RDV", "ANNULATION", "QUESTION_PRATIQUE", "URGENCE_MEDICALE", "AUTRE"]

# Consigne de classification, avec une règle de priorité pour l'urgence
SYSTEM_PROMPT = f"""Tu classes les messages reçus par le secrétariat d'un cabinet médical.
Réponds UNIQUEMENT par une de ces catégories, sans aucun autre mot :
{", ".join(CATEGORIES)}

URGENCE_MEDICALE est prioritaire : dès qu'un message décrit un signe grave
(douleur thoracique, difficulté à respirer, malaise...), choisis-la."""

# --- Les exemples few-shot ----------------------------------------------------
# Chaque tuple = (message du patient, catégorie attendue).
# Ils sont envoyés au modèle comme des échanges user / assistant, avant le vrai message.
EXEMPLES = [
    ("Je voudrais un rendez-vous jeudi si possible", "PRISE_RDV"),
    ("Je ne pourrai pas venir demain à 10h, désolé", "ANNULATION"),
    ("Vous prenez la carte Vitale ?", "QUESTION_PRATIQUE"),
    ("Mon père a du mal à respirer et il est tout pâle", "URGENCE_MEDICALE"),
    ("Vous pouvez me conseiller un bon restaurant ?", "AUTRE"),
]

# Messages à classer
MESSAGES_A_CLASSER = [
    "Bonjour, est-ce qu'il reste de la place lundi matin ?",
    "Il y a un parking près du cabinet ?",
    "Finalement je ne viendrai pas à mon rdv de vendredi",
    "J'ai une douleur qui serre dans la poitrine et je transpire beaucoup",
    "Je voulais annuler mais en fait je peux décaler à mardi ?",
    "Quel temps fait-il à Lille ?",
]


def classer(message):
    """Renvoie la catégorie du message, ou 'INCONNU' si la réponse est hors liste."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Few-shot : on insère les exemples sous forme de paires question / réponse
    if USE_EXEMPLES:
        for exemple, categorie in EXEMPLES:
            messages.append({"role": "user", "content": exemple})
            messages.append({"role": "assistant", "content": categorie})

    # Puis le vrai message à classer, en dernier
    messages.append({"role": "user", "content": message})

    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=512,
        temperature=0,   # 0 : réponses les plus stables possibles
        reasoning_effort=REASONING_EFFORT,
    )
    # On normalise la réponse : espaces retirés, majuscules
    reponse = (completion.choices[0].message.content or "").strip().upper()

    # Si la réponse ne fait pas partie des catégories, elle est marquée INCONNU.
    # !r affiche la chaîne entre guillemets (pratique pour voir les espaces, etc.)
    return reponse if reponse in CATEGORIES else f"INCONNU ({reponse!r})"


# --- Programme principal -------------------------------------------------------
print(f"Mode : {'few-shot' if USE_EXEMPLES else 'zero-shot'}\n")
for message in MESSAGES_A_CLASSER:
    # :<20 aligne la catégorie à gauche sur 20 caractères (affichage en colonnes)
    print(f"{classer(message):<20} <- {message}")
