"""
02_outils_manuels.py
--------------------
Donner des outils au LLM... à la main.

Le modèle ne peut pas exécuter de code. Mais il peut DEMANDER qu'on le fasse.
On invente donc un protocole simple, décrit dans le system prompt :

    Si tu as besoin d'un outil, réponds UNIQUEMENT :
    {"outil": "nom_de_l_outil", "arguments": {...}}

Notre programme :
    1. envoie la question au modèle ;
    2. regarde si la réponse est une demande d'outil (un JSON avec "outil") ;
    3. si oui, exécute la fonction Python et renvoie le résultat au modèle ;
    4. le modèle rédige alors sa réponse finale au patient.

          patient ──> LLM ──> {"outil": ...} ──> notre code exécute la fonction
                       ^                                     │
                       └──────── [RESULTAT OUTIL] ───────────┘

Lancement :
    python 02_TOOLS_MANUELS/02_outils_manuels.py

Scénario à tester :
    Vous : Bonjour, il reste de la place demain matin ?
    Vous : Je prends le premier créneau, je m'appelle Mme Dubois.
    Vous : Et le jour d'après ?

EXERCICES :
    1. Ajoutez un outil "annuler_rdv(date, heure, nom)" dans outils_cabinet.py.
       Que faut-il modifier ici pour que le modèle puisse l'utiliser ?
    2. Demandez un créneau un samedi. Comment l'erreur de l'outil est-elle gérée ?
    3. Quelles sont les faiblesses de ce protocole "fait maison" ?
"""

import json
import os
from datetime import date

from dotenv import load_dotenv
from openai import OpenAI

# OUTILS : le catalogue {nom de l'outil -> fonction Python} défini dans outils_cabinet.py
from outils_cabinet import OUTILS

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

# Date du jour (avec le nom du jour) pour interpréter "demain", "jeudi"...
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
aujourd_hui = date.today()

# --- Le system prompt ---------------------------------------------------------
# Le prompt décrit les outils disponibles et le format JSON pour les appeler.
# Note : dans une f-string, les accolades du JSON doivent être doublées {{ }}
# pour ne pas être confondues avec des variables Python.
SYSTEM_PROMPT = f"""Tu es Doc'Assist, l'assistant de secrétariat du cabinet du Dr Martin.
Aujourd'hui, nous sommes le {JOURS[aujourd_hui.weekday()]} {aujourd_hui.isoformat()}.
Horaires : du lundi au vendredi, 9h-12h et 14h-18h.
Tu vouvoies le patient, ton ton est chaleureux et concis.
Tu ne donnes jamais de conseil médical.

Tu as accès à ces OUTILS :

1. chercher_creneaux(date)
   Liste les créneaux libres d'une journée. date au format AAAA-MM-JJ.

2. reserver_creneau(date, heure, nom)
   Réserve un créneau. heure au format HH:MM (ex. "09:30"), nom = nom du patient.
   
3. annuler_rdv(date, heure, nom)
   Annuler un rendez-vous. date au format AAAA-MM-JJ, heure au format HH:MM, nom = nom du patient.

RÈGLES D'UTILISATION DES OUTILS :
- Pour utiliser un outil, réponds UNIQUEMENT avec ce JSON, sans aucun autre texte :
  {{"outil": "nom_de_l_outil", "arguments": {{"param": "valeur"}}}}
- Tu recevras ensuite le résultat dans un message commençant par [RESULTAT OUTIL].
- N'invente JAMAIS une disponibilité : vérifie toujours avec chercher_creneaux.
- Ne réserve qu'après accord explicite du patient et quand tu connais son nom.
- Si tu n'as pas besoin d'outil, réponds normalement au patient."""


# --- Fonctions utilitaires ---------------------------------------------------
def appeler_llm(messages):
    """Envoie l'historique au modèle et renvoie sa réponse (texte)."""
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=1024,
        temperature=0,   # 0 : réponses les plus stables possibles
        reasoning_effort=REASONING_EFFORT,
    )
    # content peut être None (cf. étape 00) : on le remplace par une chaîne vide
    return (completion.choices[0].message.content or "").strip()


def detecter_appel_outil(texte):
    """Analyse la réponse du modèle : est-ce une demande d'outil ?

    Renvoie (nom_outil, arguments) si c'est le cas, sinon None.
    """
    texte = texte.strip()

    # Certains modèles entourent le JSON de balises markdown : ```json ... ```
    # On retire les ` aux extrémités, puis le mot "json" s'il reste au début.
    if texte.startswith("```"):
        texte = texte.strip("`").removeprefix("json").strip()

    # On essaie de lire le texte comme du JSON
    try:
        demande = json.loads(texte)
    except json.JSONDecodeError:
        return None  # ce n'est pas du JSON : c'est une réponse normale au patient

    # C'est du JSON, mais est-ce bien une demande d'outil ? (il faut la clé "outil")
    if isinstance(demande, dict) and "outil" in demande:
        return demande["outil"], demande.get("arguments", {})
    return None


def executer_outil(nom, arguments):
    """Exécute l'outil demandé par le modèle.

    Si l'outil n'existe pas ou si les arguments sont incorrects,
    renvoie un dictionnaire d'erreur au lieu de planter.
    """
    # 1. L'outil existe-t-il dans notre catalogue ?
    if nom not in OUTILS:
        return {"erreur": f"Outil inconnu : '{nom}'. Outils disponibles : {list(OUTILS)}"}

    # 2. On appelle la fonction. **arguments "déplie" le dictionnaire :
    #    {"date": "2026-11-17"} devient chercher_creneaux(date="2026-11-17")
    try:
        return OUTILS[nom](**arguments)
    except TypeError as e:  # arguments manquants, en trop, ou mal nommés
        return {"erreur": f"Arguments invalides pour {nom} : {e}"}


# --- Programme principal : le chat -------------------------------------------
def main():
    print("Doc'Assist (outils manuels) — tapez 'exit' pour quitter.\n")

    # L'historique commence par le system prompt, renvoyé à chaque appel
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        # Lecture de la question du patient
        try:
            question = input("Vous : ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl+D ou Ctrl+C
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue  # ignore les entrées vides

        messages.append({"role": "user", "content": question})

        # 1er appel : le modèle répond OU demande un outil
        reponse = appeler_llm(messages)

        # Le modèle demande-t-il un outil ?
        appel = detecter_appel_outil(reponse)
        if appel:
            nom, arguments = appel
            print(f"   🔧 Le modèle demande : {nom}({arguments})")

            # Exécution de la fonction Python correspondante
            resultat = executer_outil(nom, arguments)
            print(f"   📋 Résultat : {resultat}")

            # On ajoute à l'historique :
            #   - la demande d'outil du modèle (pour qu'il se souvienne de l'avoir faite)
            #   - le résultat, envoyé comme un message "user" avec le préfixe [RESULTAT OUTIL]
            messages.append({"role": "assistant", "content": reponse})
            messages.append({
                "role": "user",
                "content": f"[RESULTAT OUTIL] {json.dumps(resultat, ensure_ascii=False)}",
            })

            # 2e appel : le modèle rédige sa réponse en tenant compte du résultat
            reponse = appeler_llm(messages)

        # Un seul outil est exécuté par question :
        # si le modèle en demande un autre, il n'est pas traité.
        if detecter_appel_outil(reponse):
            print("   ⚠️  Le modèle voulait encore un outil : limite d'un outil par tour.")

        # On enregistre la réponse finale dans l'historique et on l'affiche
        messages.append({"role": "assistant", "content": reponse})
        print(f"Doc'Assist : {reponse}\n")


if __name__ == "__main__":
    main()
