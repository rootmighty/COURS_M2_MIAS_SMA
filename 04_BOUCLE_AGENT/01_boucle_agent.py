"""
01_boucle_agent.py
------------------
La boucle agent : laisser le modèle enchaîner les outils jusqu'à finir sa tâche.

À l'étape 03, un seul tour d'outils était exécuté par question.
Ici, on répète tant que le modèle demande des outils :

    ┌──> LLM ──> tool_calls ? ── non ──> réponse finale au patient
    │               │
    │              oui
    │               │
    └── résultats <── exécution des outils

Une limite (MAX_ETAPES) empêche l'agent de tourner indéfiniment.

C'est le cœur de tout agent : un LLM + des outils + une boucle.

Lancement :
    python 04_BOUCLE_AGENT/01_boucle_agent.py

Scénario à tester :
    Vous : Réservez-moi le premier créneau libre demain, je suis M. Leroy.
    Vous : Finalement, décalez-le au dernier créneau de l'après-midi.
    Vous : Quels sont mes rendez-vous ?

EXERCICES :
    1. Mettez MAX_ETAPES = 1. Que retrouve-t-on ?
    2. Demandez : "Annulez tous les rendez-vous de M. Leroy". Combien d'étapes ?
    3. Demandez : "Trouvez-moi un créneau libre un jour où il y a au moins 5 créneaux
       le matin". Observez le nombre d'étapes. Quel risque pour le coût et le temps ?
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

# Nombre maximum d'appels au modèle pour une seule question
MAX_ETAPES = 6

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.
Horaires : du lundi au vendredi, 9h-12h et 14h-18h.
Tu vouvoies le patient, ton ton est chaleureux et concis.
Tu ne donnes jamais de conseil médical.
N'invente jamais une disponibilité ni un rendez-vous : vérifie toujours avec les outils.
Tu peux enchaîner plusieurs outils pour mener une demande jusqu'au bout.
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
    return completion.choices[0].message


def executer_outil(nom, arguments_json):
    """Exécute l'outil demandé à partir de son nom et de ses arguments (chaîne JSON)."""
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


# --- La boucle agent ---------------------------------------------------------
def executer_agent(messages):
    """Fait tourner l'agent jusqu'à obtenir une réponse texte (ou atteindre la limite).

    `messages` est modifié sur place : tous les échanges y sont ajoutés.
    Renvoie la réponse finale destinée au patient.
    """
    for etape in range(1, MAX_ETAPES + 1):
        print(f"   ── Étape {etape} ──")
        message = appeler_llm(messages)

        # Pas de demande d'outil : le modèle a terminé, on sort de la boucle
        if not message.tool_calls:
            reponse = message.content or "(pas de réponse texte)"
            messages.append({"role": "assistant", "content": reponse})
            return reponse

        # Sinon : on enregistre la demande, on exécute chaque outil
        # et on ajoute les résultats à l'historique
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [tc.model_dump() for tc in message.tool_calls],
        })
        for tool_call in message.tool_calls:
            nom = tool_call.function.name
            print(f"   🔧 {nom}({tool_call.function.arguments})")
            resultat = executer_outil(nom, tool_call.function.arguments)
            print(f"   📋 {resultat}")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(resultat, ensure_ascii=False),
            })
        # ... puis on repart pour un nouveau tour de boucle avec les résultats

    # Limite atteinte sans réponse finale
    reponse = "Désolé, je n'ai pas réussi à traiter votre demande. Pouvez-vous la reformuler ?"
    print(f"   ⚠️  Limite de {MAX_ETAPES} étapes atteinte.")
    messages.append({"role": "assistant", "content": reponse})
    return reponse


# --- Programme principal : le chat -------------------------------------------
def main():
    print(f"Doc'Assist (agent, {MAX_ETAPES} étapes max) — tapez 'exit' pour quitter.\n")
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
        reponse = executer_agent(messages)
        print(f"Doc'Assist : {reponse}\n")


if __name__ == "__main__":
    main()
