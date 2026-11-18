"""
02_memoire_longue.py
--------------------
La mémoire longue : se souvenir d'un patient d'une conversation à l'autre.

L'historique (mémoire courte) disparaît quand le programme s'arrête.
Ici, l'agent dispose de deux outils supplémentaires pour lire et écrire
dans un fichier persistant (memoire_patients.json) :
    - consulter_memoire        : au début de la conversation, dès qu'il connaît le nom
    - enregistrer_information  : quand le patient exprime une préférence durable

C'est l'agent qui décide quoi retenir : la mémoire est elle-même un outil.

Lancement :
    python 06_MEMOIRE/02_memoire_longue.py

Scénario en deux sessions :
    Session 1 :
        Vous : Bonjour, je suis Mme Dubois. Je préfère toujours venir le matin, avant 10h.
        Vous : Il vous reste de la place jeudi ?
        Vous : exit
    Session 2 (relancez le script) :
        Vous : Bonjour, c'est Mme Dubois, je voudrais un rendez-vous la semaine prochaine.

EXERCICES :
    1. Ouvrez memoire_patients.json après la session 1. Qu'a retenu l'agent ?
    2. Dites : "Je suis diabétique, je préfère le matin à jeun." Que retient l'agent ?
       Pourquoi est-ce un problème (RGPD, données de santé) ? HDS ? 
    3. Ajoutez un outil oublier_patient(nom) : le droit à l'effacement du RGPD.
    4. Plutôt que de laisser l'agent appeler consulter_memoire, chargez la mémoire
       dans le system prompt dès que le nom est connu. Avantages ? Inconvénients ?
"""

from datetime import date

from agent import CRITERE_ARRET, executer_agent
from memoire_patients import OUTILS_MEMOIRE, SCHEMAS_MEMOIRE
from outils_cabinet import OUTILS
from schemas_outils import SCHEMAS_OUTILS

MAX_ETAPES = 6

# Outils de l'agenda + outils de mémoire
SCHEMAS = SCHEMAS_OUTILS + SCHEMAS_MEMOIRE
FONCTIONS = {**OUTILS, **OUTILS_MEMOIRE}

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.
Horaires : du lundi au vendredi, 9h-12h et 14h-18h.
Tu vouvoies le patient, ton ton est chaleureux et concis.
Tu ne donnes jamais de conseil médical.
N'invente jamais une disponibilité ni un rendez-vous : vérifie toujours avec les outils.
Ne réserve qu'après accord explicite du patient et quand tu connais son nom.
{CRITERE_ARRET}

MÉMOIRE :
- Dès que tu connais le nom du patient, consulte sa mémoire avec consulter_memoire
  et tiens compte de ses préférences dans tes propositions.
- Quand le patient exprime une préférence durable (horaires, médecin, moyen de contact),
  enregistre-la avec enregistrer_information.
- N'enregistre JAMAIS d'information médicale (maladie, symptôme, traitement)."""


def main():
    print("Doc'Assist — mémoire longue. Tapez 'exit' pour quitter.\n")
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
        print(f"   📊 Contexte envoyé : {tokens} tokens\n")

    # À la fin du programme, l'historique (mémoire courte) est perdu.
    # Seul le fichier memoire_patients.json (mémoire longue) est conservé.
    print("Fin de la session : l'historique est effacé, la mémoire longue est conservée.")


if __name__ == "__main__":
    main()
