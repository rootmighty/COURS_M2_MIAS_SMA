"""
01_memoire_courte.py
--------------------
La mémoire courte : gérer l'historique de la conversation.

Depuis l'étape 00, on renvoie TOUT l'historique au modèle à chaque appel.
Le nombre de tokens envoyés augmente donc à chaque échange (affiché après chaque réponse).
Trois stratégies sont proposées (variable STRATEGIE) :

    "complete" : tout l'historique est conservé (comme jusqu'ici)
    "fenetre"  : seuls les N derniers échanges sont conservés, les plus anciens sont oubliés
    "resume"   : les échanges anciens sont résumés par le LLM, les N derniers sont conservés

Lancement :
    python 06_MEMOIRE/01_memoire_courte.py

Scénario à tester (avec chacune des trois stratégies) :
    Vous : Bonjour, je suis Mme Dubois.
    Vous : Il vous reste de la place demain matin ?
    Vous : Et jeudi après-midi ?
    Vous : Je prends le premier créneau de jeudi.
    Vous : Rappelez-moi mon nom et ce qu'on a fait ?

EXERCICES :
    1. Relevez le nombre de tokens après chaque échange, pour chaque stratégie.
    2. Avec "fenetre", que répond l'agent à la dernière question ? Pourquoi ?
    3. Avec "resume", affichez le résumé (AFFICHER_RESUME = True). Qu'a-t-il gardé ? Perdu ?
    4. Mettez MAX_ETAPES = 1 et demandez de réserver un créneau. Que se passe-t-il à la limite ?
"""

from datetime import date

from agent import CRITERE_ARRET, appeler_llm, executer_agent
from outils_cabinet import OUTILS
from schemas_outils import SCHEMAS_OUTILS

# --- Configuration -----------------------------------------------------------
STRATEGIE = "complete"     # "complete" | "fenetre" | "resume"
TOURS_GARDES = 2           # nombre d'échanges récents conservés ("fenetre" et "resume")
AFFICHER_RESUME = True     # affiche le résumé à chaque mise à jour
MAX_ETAPES = 6

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.
Horaires : du lundi au vendredi, 9h-12h et 14h-18h.
Tu vouvoies le patient, ton ton est chaleureux et concis.
Tu ne donnes jamais de conseil médical.
N'invente jamais une disponibilité ni un rendez-vous : vérifie toujours avec les outils.
Ne réserve qu'après accord explicite du patient et quand tu connais son nom.
{CRITERE_ARRET}"""


# --- Découpage de l'historique en échanges ---------------------------------------
def debut_des_tours(messages):
    """Renvoie les positions des messages "user" : chacun ouvre un nouvel échange.

    On coupe toujours l'historique au début d'un échange, pour ne jamais séparer
    une demande d'outil (assistant + tool_calls) de ses résultats (messages "tool"),
    ce que l'API refuserait.
    """
    return [i for i, m in enumerate(messages) if m["role"] == "user"]


# --- Stratégie "fenetre" -------------------------------------------------------
def appliquer_fenetre(messages):
    """Garde le system prompt et les TOURS_GARDES derniers échanges."""
    debuts = debut_des_tours(messages)
    if len(debuts) <= TOURS_GARDES:
        return messages
    coupe = debuts[-TOURS_GARDES]
    return [messages[0]] + messages[coupe:]


# --- Stratégie "resume" --------------------------------------------------------
resume_actuel = ""   # résumé des échanges déjà retirés de l'historique


def transcrire(messages):
    """Transforme une liste de messages en texte lisible pour le LLM qui résume."""
    lignes = []
    for m in messages:
        if m["role"] == "user":
            lignes.append(f"Patient : {m['content']}")
        elif m["role"] == "assistant" and m.get("content"):
            lignes.append(f"Assistant : {m['content']}")
        elif m["role"] == "tool":
            lignes.append(f"[Résultat d'outil] {m['content']}")
    return "\n".join(lignes)


def appliquer_resume(messages):
    """Résume les anciens échanges et garde les TOURS_GARDES derniers tels quels."""
    global resume_actuel
    debuts = debut_des_tours(messages)
    if len(debuts) <= TOURS_GARDES:
        return messages

    coupe = debuts[-TOURS_GARDES]
    anciens = messages[1:coupe]   # tout sauf le system prompt et les échanges récents

    # Le nouveau résumé intègre l'ancien résumé et les échanges retirés
    consigne = ("Résume en quelques lignes les informations importantes de cette conversation "
                "entre un patient et le secrétariat d'un cabinet médical : nom du patient, "
                "rendez-vous pris ou annulés (dates et heures), demandes en cours.\n\n"
                f"Résumé précédent : {resume_actuel or '(aucun)'}\n\n"
                f"Nouveaux échanges :\n{transcrire(anciens)}")
    completion = appeler_llm([{"role": "user", "content": consigne}])
    resume_actuel = completion.choices[0].message.content or resume_actuel

    if AFFICHER_RESUME:
        print(f"   📝 Résumé mis à jour : {resume_actuel}")

    # Le résumé est intégré au system prompt (un seul message "system" en tête)
    systeme = {"role": "system",
               "content": f"{SYSTEM_PROMPT}\n\nRésumé de la conversation précédente :\n{resume_actuel}"}
    return [systeme] + messages[coupe:]


# --- Programme principal : le chat -------------------------------------------
def main():
    print(f"Doc'Assist — mémoire courte : stratégie '{STRATEGIE}'. Tapez 'exit' pour quitter.\n")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            question = input("Vous : ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        messages.append({"role": "user", "content": question})

        # Réduction de l'historique avant l'appel, selon la stratégie choisie
        # (messages[:] = ... remplace le contenu de la liste existante)
        if STRATEGIE == "fenetre":
            messages[:] = appliquer_fenetre(messages)
        elif STRATEGIE == "resume":
            messages[:] = appliquer_resume(messages)

        reponse, tokens = executer_agent(messages, SCHEMAS_OUTILS, OUTILS, max_etapes=MAX_ETAPES)
        print(f"Doc'Assist : {reponse}")
        print(f"   📊 Contexte envoyé : {tokens} tokens — {len(messages)} messages en mémoire\n")


if __name__ == "__main__":
    main()
