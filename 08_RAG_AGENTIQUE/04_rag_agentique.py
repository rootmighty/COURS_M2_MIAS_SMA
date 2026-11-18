"""
04_rag_agentique.py
-------------------
Le RAG agentique : la recherche dans les documents devient un OUTIL de l'agent.

C'est l'agent qui décide :
    - s'il doit chercher (pas pour "Bonjour" ni pour un créneau) ;
    - quoi chercher (il reformule la question en requête) ;
    - combien de fois (plusieurs recherches si la question a plusieurs parties) ;
    - comment combiner les documents avec les autres outils (agenda).

    question ──> agent ──┬──> rechercher_documents ──> FAISS
                         └──> outils de l'agenda

Prérequis : avoir lancé 02_indexer_documents.py

Lancement :
    python 08_RAG_AGENTIQUE/04_rag_agentique.py

Questions à tester :
    Vous : Bonjour !
    Vous : Je ne suis pas venu depuis deux ans, je peux faire une téléconsultation ?
    Vous : Combien coûte une consultation, et il vous reste de la place demain matin ?
    Vous : Je ne pourrai pas venir à mon rendez-vous de demain, je risque quelque chose ?

EXERCICES :
    1. Pour chaque question, l'agent a-t-il cherché dans les documents ? Avec quelle requête ?
    2. Comparez avec 03 : nombre de recherches, tokens, qualité des réponses.
    3. Les documents sont des données lues par un outil : quel risque vu à l'étape précédente ?
"""

from datetime import date

from agent import CRITERE_ARRET, executer_agent
from outils_cabinet import OUTILS
from rag import rechercher
from schemas_outils import SCHEMAS_OUTILS

MAX_ETAPES = 6


# --- L'outil de recherche documentaire ------------------------------------------------
def rechercher_documents(requete, nombre_resultats=3):
    """Cherche les passages des documents du cabinet les plus proches de la requête."""
    resultats = rechercher(requete, k=nombre_resultats)
    return {
        "resultats": [
            {"source": f"{r['source']} — {r['section']}", "extrait": r["texte"], "score": r["score"]}
            for r in resultats
        ]
    }


SCHEMA_RECHERCHE = {
    "type": "function",
    "function": {
        "name": "rechercher_documents",
        "description": (
            "Recherche dans les documents du cabinet : horaires, accès, tarifs, remboursements, "
            "téléconsultation, visites à domicile, absences du médecin, urgences, "
            "données personnelles, règles d'annulation et de retard. "
            "La recherche est sémantique : formule une requête courte et précise."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "requete": {"type": "string", "description": "Ce que tu cherches, en une phrase courte."},
                "nombre_resultats": {"type": "integer", "description": "Nombre de passages (1 à 5).",
                                     "minimum": 1, "maximum": 5},
            },
            "required": ["requete"],
        },
    },
}

# Outils de l'agenda + outil de recherche documentaire
SCHEMAS = SCHEMAS_OUTILS + [SCHEMA_RECHERCHE]
FONCTIONS = {**OUTILS, "rechercher_documents": rechercher_documents}

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.
Tu vouvoies le patient, ton ton est chaleureux et concis.
Tu ne donnes jamais de conseil médical.

Pour toute question sur le fonctionnement du cabinet (tarifs, règles, téléconsultation...),
utilise l'outil rechercher_documents et réponds uniquement à partir des passages trouvés,
en citant la source entre crochets. Si les documents ne contiennent pas la réponse, dis-le.
Pour les disponibilités et les rendez-vous, utilise les outils de l'agenda.
Ne réserve qu'après accord explicite du patient et quand tu connais son nom.
{CRITERE_ARRET}"""


def main():
    print("Doc'Assist (RAG agentique) — tapez 'exit' pour quitter.\n")
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
        reponse, tokens = executer_agent(messages, SCHEMAS, FONCTIONS, max_etapes=MAX_ETAPES)
        print(f"Doc'Assist : {reponse}")
        print(f"   📊 {tokens} tokens envoyés au dernier appel\n")


if __name__ == "__main__":
    main()
