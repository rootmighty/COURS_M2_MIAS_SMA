"""
02_react_explicite.py
---------------------
Le schéma ReAct (Reasoning + Acting) : Pensée -> Action -> Observation.

On confie à l'agent une tâche qui demande plusieurs étapes dépendantes :
déplacer le rendez-vous d'une patiente. L'agent doit, sans aide :
    1. retrouver le rendez-vous existant      (lister_rdv)
    2. chercher les créneaux libres            (chercher_creneaux)
    3. réserver le nouveau créneau             (reserver_creneau) (en premier sinon si on annule avant de réserver, on perd les deux rendez-vous si erreur de réservation)
    4. annuler l'ancien                        (annuler_rdv)

On demande au modèle d'écrire sa réflexion avant chaque action,
et on affiche la trace complète : Pensée / Action / Observation.

Lancement :
    python 04_BOUCLE_AGENT/02_react_explicite.py

EXERCICES :
    1. Dans quel ordre l'agent a-t-il réservé et annulé ? Quel ordre est le plus sûr, et pourquoi ?
    2. Changez la demande : "décalez-le au premier créneau libre de la semaine prochaine".
       L'agent s'en sort-il ? En combien d'étapes ?
    3. Supprimez l'outil lister_rdv de SCHEMAS_OUTILS. Comment l'agent réagit-il ?
"""

import json
import os
from datetime import date, timedelta

from dotenv import load_dotenv
from openai import OpenAI

from outils_cabinet import OUTILS, chercher_creneaux, reinitialiser_agenda, reserver_creneau
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
MAX_ETAPES = 8

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

# Consigne ReAct : écrire une courte pensée avant chaque action
SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.
Horaires : du lundi au vendredi, 9h-12h et 14h-18h.

Tu traites la demande du patient de façon autonome, en enchaînant les outils nécessaires.
La demande du patient vaut accord pour les réservations et annulations qu'elle implique.
Avant CHAQUE appel d'outil, écris dans ton message une phrase qui commence par
"Pensée :" et qui explique ce que tu vas faire et pourquoi.
Quand la tâche est terminée, rédige un court message de confirmation au patient."""


# --- Préparation : un rendez-vous existant pour Mme Dubois -------------------
reinitialiser_agenda()

# Prochain jour ouvré
jour = aujourd_hui + timedelta(days=1)
while jour.weekday() >= 5:
    jour += timedelta(days=1)

# Réservation du premier créneau libre du matin de ce jour
libres = chercher_creneaux(jour.isoformat())["creneaux_libres"]
heure_initiale = next(h for h in libres if h < "12:00")
reserver_creneau(jour.isoformat(), heure_initiale, "Mme Dubois")

DEMANDE = ("Bonjour, c'est Mme Dubois. Je ne pourrai pas venir à mon rendez-vous du matin. "
           "décalez-le au premier créneau libre de la semaine prochaine")


# --- Fonctions utilitaires ---------------------------------------------------
def appeler_llm(messages):
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=SCHEMAS_OUTILS,
        tool_choice="auto",
        max_tokens=1024,
        temperature=0,
        reasoning_effort=REASONING_EFFORT,
    )
    return completion.choices[0].message


def executer_outil(nom, arguments_json):
    if nom not in OUTILS:
        return {"erreur": f"Outil inconnu : '{nom}'."}
    try:
        arguments = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return {"erreur": f"Arguments non lisibles : {arguments_json}"}
    try:
        return OUTILS[nom](**arguments)
    except TypeError as e:
        return {"erreur": f"Arguments invalides pour {nom} : {e}"}


def extraire_pensee(message):
    """Renvoie la réflexion du modèle : le texte du message,
    ou à défaut son raisonnement interne (modèles "thinking")."""
    if message.content:
        return message.content.strip()
    # Champ non standard renvoyé par certains modèles : lu s'il existe
    raisonnement = getattr(message, "reasoning_content", None) or ""
    if raisonnement:
        return "(raisonnement interne) " + raisonnement.strip()[:300]
    return "(aucune pensée exprimée)"


# --- La boucle ReAct ---------------------------------------------------------
print(f"Rendez-vous initial : Mme Dubois, le {jour.isoformat()} à {heure_initiale}\n")
print(f"PATIENTE : {DEMANDE}\n")

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": DEMANDE},
]

for etape in range(1, MAX_ETAPES + 1):
    print(f"══════ Étape {etape} ══════")
    message = appeler_llm(messages)

    # Fin de la tâche : réponse texte sans demande d'outil
    if not message.tool_calls:
        print(f"✅ Réponse finale : {message.content}")
        break

    print(f"💭 {extraire_pensee(message)}")

    messages.append({
        "role": "assistant",
        "content": message.content,
        "tool_calls": [tc.model_dump() for tc in message.tool_calls],
    })
    for tool_call in message.tool_calls:
        print(f"🔧 Action      : {tool_call.function.name}({tool_call.function.arguments})")
        resultat = executer_outil(tool_call.function.name, tool_call.function.arguments)
        print(f"👀 Observation : {resultat}")
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(resultat, ensure_ascii=False),
        })
    print()
else:
    # Exécuté seulement si la boucle n'a pas été interrompue par "break"
    print(f"⚠️  Limite de {MAX_ETAPES} étapes atteinte sans réponse finale.")

# --- Vérification dans l'agenda réel -----------------------------------------
print("\nAgenda réel de Mme Dubois :", OUTILS["lister_rdv"]("Mme Dubois"))
